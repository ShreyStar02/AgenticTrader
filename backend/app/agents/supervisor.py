"""Supervisor agent: orchestrates the autonomous trading loop.

Flow per run:
  1. Assess market regime (RegimeAgent).
  2. Manage existing positions: mark-to-market, apply exit rules (RiskManager).
  3. Scan the risk-profile universe -> StrategyAgent signals.
  4. Rank candidates, gate each through RiskManager, and paper-buy the best fits.
  5. Persist signals, alerts, and a run summary for full explainability.
"""
from __future__ import annotations

import datetime as dt
import json

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.risk_profiles import get_risk_params
from app.models import AgentRun, Order, Signal, Trade
from app.agents import regime_agent, risk_manager, analyst_agent
from app.agents.strategy_agent import evaluate_symbol, evaluate_symbol_intraday
from app.core.universe import SECTOR_HINT
from app.services import alerts, market_data, portfolio, settings_store, wallet, watchlist

log = get_logger("agent.supervisor")

# Cap how many profile-universe symbols we deeply analyze per run. Set to 75 so
# the entire aggressive universe (NIFTY 50 + ~22 midcaps) is scanned every cycle.
# User-watchlisted symbols are added ON TOP of this cap (see below), so they never
# displace a universe name.
MAX_SCAN = 75

# In risk-off regimes, re-check only the strongest swing candidates with intraday
# (5m) data. Kept small so the extra network calls stay bounded.
INTRADAY_SCAN = 10

# Shorts are force-covered when this many (or fewer) minutes remain in the
# session, i.e. always >=30 min before the 15:30 IST close. We refuse to OPEN a
# new short inside a slightly wider window so there is time to cover cleanly.
SHORT_FORCE_COVER_MIN = 35
SHORT_NO_NEW_MIN = 45


def _intraday_trades_today(db: Session) -> int:
    """Count intraday entries already taken today (across cycles) for the daily cap."""
    start = dt.datetime.now(dt.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (
        db.query(Order)
        .filter(
            Order.side == "BUY",
            Order.created_at >= start,
            Order.reason.like("[INTRADAY]%"),
        )
        .count()
    )


def _short_trades_today(db: Session) -> int:
    """Count short entries opened today (across cycles) for the daily short cap."""
    start = dt.datetime.now(dt.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (
        db.query(Order)
        .filter(
            Order.side == "SHORT",
            Order.created_at >= start,
        )
        .count()
    )


def run_cycle(db: Session, force: bool = False) -> dict:
    """Execute one full autonomous cycle. Returns a summary dict."""
    if not settings_store.is_autonomous(db) and not force:
        return {"skipped": True, "reason": "autonomous disabled"}

    run = AgentRun(status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    profile = settings_store.get_risk_profile(db)
    rp = get_risk_params(profile)

    regime = regime_agent.assess_regime()
    run.regime = regime.label

    actions = 0
    action_log: list[str] = []
    signals_saved: list[Signal] = []

    universe = market_data.get_universe(profile)
    if not rp.allow_midcap:
        from app.core.universe import NIFTY_NEXT_EXTRA

        midset = set(NIFTY_NEXT_EXTRA)
        universe = [u for u in universe if u["symbol"] not in midset]

    # Always include user-watchlisted symbols (even outside the profile universe).
    wl = watchlist.get_watchlist(db)
    wl_extra = 0
    if wl:
        present = {u["symbol"] for u in universe}
        extra = [
            {"symbol": s, "sector": SECTOR_HINT.get(s)}
            for s in wl if s not in present
        ]
        wl_extra = len(extra)
        # Prepend so watchlist symbols are never dropped by the MAX_SCAN cap.
        universe = extra + universe

    # ---- 1) Manage existing positions first (exits) ----
    # Minutes left in the session drives the mandatory same-day cover of shorts.
    mtc = market_data.minutes_to_close()
    force_cover = (mtc is None) or (mtc <= SHORT_FORCE_COVER_MIN)
    held = {p.symbol for p in portfolio.list_positions(db)}
    price_map: dict[str, float] = {}

    for pos in portfolio.list_positions(db):
        sig = evaluate_symbol(pos.symbol, None, regime.bias, with_news=False)
        last = sig.last_price if sig else (pos.last_price or pos.avg_price)
        score = sig.score if sig else 0.0
        price_map[pos.symbol] = last
        if pos.qty < 0:
            # Short position: cover on stop/target/reversal, or force-cover when we
            # are within the mandatory same-day window (>=30 min before close).
            isig = evaluate_symbol_intraday(pos.symbol, None, regime.bias)
            iscore = isig.score if isig else score
            if isig is not None:
                last = isig.last_price
                price_map[pos.symbol] = last
            decision = risk_manager.evaluate_cover(
                last, pos.avg_price, pos.stop_loss, pos.take_profit, iscore,
                force=force_cover,
            )
            if decision.should_cover:
                res = portfolio.cover(
                    db, pos.symbol, abs(pos.qty), last,
                    reason=f"[COVER] {decision.reason}",
                )
                if res.ok:
                    actions += 1
                    action_log.append(
                        f"COVERED {abs(pos.qty)} {pos.symbol} ({decision.reason})"
                    )
            continue

        decision = risk_manager.evaluate_exit(
            last, pos.avg_price, pos.stop_loss, pos.take_profit, score
        )
        if decision.should_sell:
            res = portfolio.sell(db, pos.symbol, pos.qty, last, reason=decision.reason)
            if res.ok:
                actions += 1
                action_log.append(f"SOLD {pos.qty} {pos.symbol} ({decision.reason})")

    # ---- 2) Scan universe for new opportunities ----
    # Cap applies to the profile universe; watchlist extras (prepended) are added
    # on top so the full NIFTY 50 plus every watchlist symbol is always scanned.
    candidates = [u for u in universe if u["symbol"] not in held][: MAX_SCAN + wl_extra]
    scored: list = []
    for u in candidates:
        sig = evaluate_symbol(u["symbol"], u.get("sector"), regime.bias, with_news=True)
        if sig is None:
            continue
        price_map[sig.symbol] = sig.last_price
        action = "BUY" if sig.score >= rp.min_score_to_buy else (
            "SELL" if sig.score <= -0.4 else "HOLD"
        )
        sig.action = action
        scored.append(sig)
        signals_saved.append(
            Signal(
                run_id=run.id, symbol=sig.symbol, score=sig.score,
                technical_score=sig.technical_score, sentiment_score=sig.sentiment_score,
                trend=sig.trend, action=action, rationale=sig.rationale,
                details_json=json.dumps(sig.details, default=str),
            )
        )

    db.add_all(signals_saved)
    db.commit()

    # ---- 3) Execute buys on the best candidates, gated by risk ----
    scored.sort(key=lambda s: s.score, reverse=True)
    summary = portfolio.portfolio_summary(db, price_map)
    equity = summary["equity"]
    trades_today = db.query(Trade).filter(
        Trade.created_at >= dt.datetime.now(dt.timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    ).count()

    if not regime.risk_on:
        alerts.push_alert(
            db, f"Risk-off regime: {regime.label}", message=regime.detail,
            level="warning", category="risk",
        )

    if regime.risk_on:
        # ---- 3a) Normal swing entries on the best candidates, gated by risk ----
        for sig in scored:
            cash = wallet.get_balance(db) - portfolio.short_notional(db)
            open_positions = len(portfolio.list_positions(db))
            decision = risk_manager.evaluate_buy(
                db, sig.symbol, sig.last_price, sig.score, rp,
                equity=equity, cash=cash, open_positions=open_positions,
                trades_today=trades_today,
            )
            if decision.approved:
                res = portfolio.buy(
                    db, sig.symbol, decision.qty, sig.last_price,
                    reason=f"{sig.rationale} | {decision.reason}",
                    stop_loss=decision.stop_loss, take_profit=decision.take_profit,
                )
                if res.ok:
                    actions += 1
                    trades_today += 1
                    action_log.append(f"BOUGHT {decision.qty} {sig.symbol} @ ₹{sig.last_price:.2f}")
    elif rp.intraday_enabled:
        # ---- 3b) Risk-off: skip slow swing entries, but allow a few highly
        # selective intraday (5m) momentum trades with tight stops. This keeps the
        # agent active in a bearish/volatile tape without taking overnight/trend
        # risk -- the strict gate (high score bar, no daily downtrends, small size)
        # keeps it from being random.
        intraday_trades_today = _intraday_trades_today(db)
        for sig in scored[:INTRADAY_SCAN]:
            isig = evaluate_symbol_intraday(
                sig.symbol, sig.details.get("sector"), regime.bias
            )
            if isig is None:
                continue
            price_map[isig.symbol] = isig.last_price
            cash = wallet.get_balance(db) - portfolio.short_notional(db)
            open_positions = len(portfolio.list_positions(db))
            decision = risk_manager.evaluate_buy_intraday(
                db, isig.symbol, isig.last_price, isig.score, sig.technical_score, rp,
                equity=equity, cash=cash, open_positions=open_positions,
                intraday_trades_today=intraday_trades_today,
            )
            if decision.approved:
                res = portfolio.buy(
                    db, isig.symbol, decision.qty, isig.last_price,
                    reason=f"[INTRADAY] {isig.rationale} | {decision.reason}",
                    stop_loss=decision.stop_loss, take_profit=decision.take_profit,
                )
                if res.ok:
                    actions += 1
                    intraday_trades_today += 1
                    action_log.append(
                        f"INTRADAY BOUGHT {decision.qty} {isig.symbol} @ ₹{isig.last_price:.2f}"
                    )

        # ---- 3c) Risk-off: selective intraday SHORTS (sell-then-buy). Only the
        # weakest names with confirmed downside momentum, small size, tight stop.
        # Every short is force-covered >=30 min before the close (handled in the
        # exit loop), so there is never overnight short risk. We also refuse to
        # open shorts too close to that cover window.
        if rp.short_enabled and mtc is not None and mtc > SHORT_NO_NEW_MIN:
            short_trades_today = _short_trades_today(db)
            shorts_ranked = sorted(scored, key=lambda s: s.score)
            for sig in shorts_ranked[:INTRADAY_SCAN]:
                if sig.score > -0.05:
                    break  # ranked ascending: nothing left negative enough to short
                isig = evaluate_symbol_intraday(
                    sig.symbol, sig.details.get("sector"), regime.bias
                )
                if isig is None:
                    continue
                price_map[isig.symbol] = isig.last_price
                cash = wallet.get_balance(db) - portfolio.short_notional(db)
                open_positions = len(portfolio.list_positions(db))
                decision = risk_manager.evaluate_short(
                    db, isig.symbol, isig.last_price, isig.score, sig.technical_score, rp,
                    equity=equity, available_cash=cash, open_positions=open_positions,
                    short_trades_today=short_trades_today, minutes_to_close=mtc,
                    no_new_minutes=SHORT_NO_NEW_MIN,
                )
                if decision.approved:
                    res = portfolio.short_sell(
                        db, isig.symbol, decision.qty, isig.last_price,
                        reason=f"[SHORT] {isig.rationale} | {decision.reason}",
                        stop_loss=decision.stop_loss, take_profit=decision.take_profit,
                    )
                    if res.ok:
                        actions += 1
                        short_trades_today += 1
                        action_log.append(
                            f"SHORTED {decision.qty} {isig.symbol} @ ₹{isig.last_price:.2f}"
                        )

    portfolio.mark_to_market(db, price_map)

    # LLM analyst briefing (explainability only; never affects decisions).
    top = [
        {"symbol": s.symbol, "score": s.score, "trend": s.trend, "action": s.action}
        for s in scored[:6]
    ]
    briefing = analyst_agent.market_briefing(
        regime.label, regime.detail, top, action_log
    )

    final = portfolio.portfolio_summary(db, price_map)
    run.finished_at = dt.datetime.now(dt.timezone.utc)
    run.candidates_scanned = len(candidates)
    run.actions_taken = actions
    run.status = "done"
    run.briefing = briefing
    run.summary = (
        f"Regime {regime.label} ({regime.detail}). Scanned {len(candidates)}, "
        f"{actions} action(s). Equity ₹{final['equity']:.2f}, cash ₹{final['cash']:.2f}."
    )
    db.commit()

    if actions == 0:
        alerts.push_alert(
            db, "Scan complete: holding",
            message=briefing or f"No trades. {run.summary}", level="info", category="system",
        )

    log.info(run.summary)
    return {
        "run_id": run.id,
        "regime": regime.label,
        "actions": actions,
        "scanned": len(candidates),
        "summary": run.summary,
        "briefing": briefing,
        "portfolio": final,
    }
