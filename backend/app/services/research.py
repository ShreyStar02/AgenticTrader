"""On-demand research service: evaluate a single symbol and persist a Signal.

Used by the "research a stock" feature. Runs the same StrategyAgent pipeline the
autonomous cycle uses (technicals + news sentiment + regime bias), stores the
result as a normal Signal row (so it shows up in the dashboard's Signals list and
detail view with a chart), and returns it as a SignalOut-shaped dict.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.agents import regime_agent
from app.agents.strategy_agent import evaluate_symbol
from app.core.logging_config import get_logger
from app.core.risk_profiles import get_risk_params
from app.core.universe import SECTOR_HINT
from app.models import Signal
from app.schemas import SignalOut
from app.services import settings_store

log = get_logger("research")


def research_symbol(db: Session, symbol: str) -> dict | None:
    """Research one symbol, persist a Signal, and return it as a dict.

    Returns None if no price history could be fetched for the symbol.
    """
    sym = symbol.strip().upper()
    if not sym:
        return None

    profile = settings_store.get_risk_profile(db)
    rp = get_risk_params(profile)
    regime = regime_agent.assess_regime()

    sig = evaluate_symbol(sym, SECTOR_HINT.get(sym), regime.bias, with_news=True)
    if sig is None:
        return None

    action = "BUY" if sig.score >= rp.min_score_to_buy else (
        "SELL" if sig.score <= -0.4 else "HOLD"
    )
    row = Signal(
        run_id=None, symbol=sig.symbol, score=sig.score,
        technical_score=sig.technical_score, sentiment_score=sig.sentiment_score,
        trend=sig.trend, action=action, rationale=sig.rationale,
        details_json=json.dumps(sig.details, default=str),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    log.info("Researched %s -> score %.2f (%s)", sym, sig.score, action)
    return SignalOut.model_validate(row).model_dump(mode="json")
