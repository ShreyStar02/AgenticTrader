"""Risk manager agent: the mandatory gate before any paper trade."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.risk_profiles import RiskParams
from app.services import portfolio

log = get_logger("agent.risk")


@dataclass
class BuyDecision:
    approved: bool
    qty: int
    reason: str
    stop_loss: float | None = None
    take_profit: float | None = None


def evaluate_buy(
    db: Session,
    symbol: str,
    price: float,
    score: float,
    rp: RiskParams,
    equity: float,
    cash: float,
    open_positions: int,
    trades_today: int,
) -> BuyDecision:
    """Decide whether (and how much) to buy under the active risk profile."""
    if score < rp.min_score_to_buy:
        return BuyDecision(False, 0, f"score {score:.2f} < threshold {rp.min_score_to_buy:.2f}")

    if open_positions >= rp.max_positions:
        return BuyDecision(False, 0, f"max positions reached ({rp.max_positions})")

    if trades_today >= rp.max_daily_trades:
        return BuyDecision(False, 0, f"daily trade cap reached ({rp.max_daily_trades})")

    if portfolio.get_position(db, symbol):
        return BuyDecision(False, 0, "already holding this symbol")

    # Cash available after keeping the mandated buffer.
    investable = cash - equity * rp.cash_buffer_pct
    if investable <= price:
        return BuyDecision(False, 0, "insufficient investable cash after buffer")

    # Cap per-position allocation.
    max_alloc_value = min(investable, equity * rp.max_alloc_pct)
    qty = portfolio.affordable_qty(max_alloc_value, price)
    if qty < 1:
        return BuyDecision(False, 0, f"cannot afford 1 whole share within alloc cap (₹{price:.2f})")

    stop_loss = round(price * (1 - rp.stop_loss_pct), 2)
    take_profit = round(price * (1 + rp.take_profit_pct), 2)
    reason = (
        f"approved qty {qty} (alloc≤{rp.max_alloc_pct*100:.0f}% equity, "
        f"SL {rp.stop_loss_pct*100:.0f}%, TP {rp.take_profit_pct*100:.0f}%)"
    )
    return BuyDecision(True, qty, reason, stop_loss, take_profit)


def evaluate_buy_intraday(
    db: Session,
    symbol: str,
    price: float,
    intraday_score: float,
    daily_score: float,
    rp: RiskParams,
    equity: float,
    cash: float,
    open_positions: int,
    intraday_trades_today: int,
) -> BuyDecision:
    """Strict gate for a risk-off intraday momentum entry.

    Deliberately conservative so trades are selective, not random: it requires a
    high intraday conviction score, refuses names already in a daily downtrend
    (no catching falling knives), uses a smaller position size and a tight stop so
    the worst-case loss per trade is small.
    """
    if not rp.intraday_enabled:
        return BuyDecision(False, 0, "intraday trading disabled for this profile")

    if intraday_score < rp.intraday_min_score:
        return BuyDecision(
            False, 0,
            f"intraday score {intraday_score:.2f} < bar {rp.intraday_min_score:.2f}",
        )

    # Don't fight the daily trend: skip anything clearly trending down on the day.
    if daily_score < -0.10:
        return BuyDecision(False, 0, f"daily trend too weak ({daily_score:.2f})")

    if open_positions >= rp.max_positions:
        return BuyDecision(False, 0, f"max positions reached ({rp.max_positions})")

    if intraday_trades_today >= rp.intraday_max_trades:
        return BuyDecision(False, 0, f"intraday trade cap reached ({rp.intraday_max_trades})")

    if portfolio.get_position(db, symbol):
        return BuyDecision(False, 0, "already holding this symbol")

    investable = cash - equity * rp.cash_buffer_pct
    if investable <= price:
        return BuyDecision(False, 0, "insufficient investable cash after buffer")

    max_alloc_value = min(investable, equity * rp.intraday_max_alloc_pct)
    qty = portfolio.affordable_qty(max_alloc_value, price)
    if qty < 1:
        return BuyDecision(False, 0, f"cannot afford 1 whole share within intraday cap (₹{price:.2f})")

    stop_loss = round(price * (1 - rp.intraday_stop_loss_pct), 2)
    take_profit = round(price * (1 + rp.intraday_take_profit_pct), 2)
    reason = (
        f"intraday qty {qty} (alloc≤{rp.intraday_max_alloc_pct*100:.0f}% equity, "
        f"SL {rp.intraday_stop_loss_pct*100:.1f}%, TP {rp.intraday_take_profit_pct*100:.1f}%)"
    )
    return BuyDecision(True, qty, reason, stop_loss, take_profit)


@dataclass
class SellDecision:
    should_sell: bool
    reason: str


def evaluate_exit(
    last_price: float,
    avg_price: float,
    stop_loss: float | None,
    take_profit: float | None,
    score: float,
) -> SellDecision:
    """Exit rules for an open long position (stop-loss / take-profit / reversal)."""
    if stop_loss and last_price <= stop_loss:
        return SellDecision(True, f"stop-loss hit (₹{last_price:.2f} ≤ ₹{stop_loss:.2f})")
    if take_profit and last_price >= take_profit:
        return SellDecision(True, f"take-profit hit (₹{last_price:.2f} ≥ ₹{take_profit:.2f})")
    if score <= -0.4:
        return SellDecision(True, f"trend reversal (score {score:.2f})")
    return SellDecision(False, "hold")


@dataclass
class ShortDecision:
    approved: bool
    qty: int
    reason: str
    stop_loss: float | None = None   # ABOVE entry: cover (loss) if price rises
    take_profit: float | None = None  # BELOW entry: cover (profit) if price falls


def evaluate_short(
    db: Session,
    symbol: str,
    price: float,
    intraday_score: float,
    daily_score: float,
    rp: RiskParams,
    equity: float,
    available_cash: float,
    open_positions: int,
    short_trades_today: int,
    minutes_to_close: int | None,
    no_new_minutes: int,
) -> ShortDecision:
    """Strict gate for opening an intraday short (sell-then-buy).

    Only fires when momentum is strongly DOWN *and* the daily trend confirms the
    weakness, so we never short a rising stock. Size is small and the stop is
    tight, and we refuse to open a short too close to the forced same-day cover
    window so there is always time to buy back >=30 min before the close.
    """
    if not rp.short_enabled:
        return ShortDecision(False, 0, "short selling disabled for this profile")

    # Need enough runway to open and still force-cover >=30 min before close.
    if minutes_to_close is None:
        return ShortDecision(False, 0, "market closed: no new shorts")
    if minutes_to_close <= no_new_minutes:
        return ShortDecision(
            False, 0, f"too close to cover window ({minutes_to_close}m to close)"
        )

    # Momentum must be strongly negative (intraday score well below zero).
    if intraday_score > -rp.short_min_score:
        return ShortDecision(
            False, 0,
            f"intraday score {intraday_score:.2f} > short bar -{rp.short_min_score:.2f}",
        )

    # Don't short into strength: the daily trend must also be down.
    if daily_score > -0.05:
        return ShortDecision(False, 0, f"daily trend not down ({daily_score:.2f})")

    if open_positions >= rp.max_positions:
        return ShortDecision(False, 0, f"max positions reached ({rp.max_positions})")

    if short_trades_today >= rp.short_max_trades:
        return ShortDecision(False, 0, f"short trade cap reached ({rp.short_max_trades})")

    if portfolio.get_position(db, symbol):
        return ShortDecision(False, 0, "already have a position in this symbol")

    # Margin proxy: keep the buffer and require free cash to collateralise the short.
    investable = available_cash - equity * rp.cash_buffer_pct
    if investable <= price:
        return ShortDecision(False, 0, "insufficient free cash to collateralise short")

    max_notional = min(investable, equity * rp.short_max_alloc_pct)
    qty = portfolio.affordable_qty(max_notional, price)
    if qty < 1:
        return ShortDecision(False, 0, f"cannot short 1 whole share within cap (₹{price:.2f})")

    stop_loss = round(price * (1 + rp.short_stop_loss_pct), 2)   # above entry
    take_profit = round(price * (1 - rp.short_take_profit_pct), 2)  # below entry
    reason = (
        f"short qty {qty} (notional≤{rp.short_max_alloc_pct*100:.0f}% equity, "
        f"SL +{rp.short_stop_loss_pct*100:.1f}%, TP -{rp.short_take_profit_pct*100:.1f}%)"
    )
    return ShortDecision(True, qty, reason, stop_loss, take_profit)


@dataclass
class CoverDecision:
    should_cover: bool
    reason: str


def evaluate_cover(
    last_price: float,
    avg_price: float,
    stop_loss: float | None,
    take_profit: float | None,
    intraday_score: float,
    force: bool = False,
) -> CoverDecision:
    """Exit rules for an open short. ``force`` enforces the mandatory same-day
    cover (>=30 min before the close) regardless of P&L."""
    if force:
        return CoverDecision(True, "mandatory same-day cover (≥30m before close)")
    if stop_loss and last_price >= stop_loss:
        return CoverDecision(True, f"stop-loss hit (₹{last_price:.2f} ≥ ₹{stop_loss:.2f})")
    if take_profit and last_price <= take_profit:
        return CoverDecision(True, f"take-profit hit (₹{last_price:.2f} ≤ ₹{take_profit:.2f})")
    if intraday_score >= 0.20:
        return CoverDecision(True, f"momentum reversed up (score {intraday_score:.2f})")
    return CoverDecision(False, "hold")
