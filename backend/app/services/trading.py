"""Manual (user-initiated) paper trades.

Mirrors the agent's execution path but is triggered by the user. Buys derive a
stop-loss / take-profit from the active risk profile so the autonomous exit logic
manages a manually-bought position exactly like an agent-bought one. Authorized
with the same system (funds) password used for add/withdraw.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.risk_profiles import get_risk_params
from app.services import market_data, portfolio, settings_store, wallet

log = get_logger("trading")


def _last_price(symbol: str) -> float | None:
    return market_data.fetch_last_price(symbol)


def manual_buy(db: Session, symbol: str, qty: int, password: str) -> dict:
    if not wallet.check_password(db, password):
        raise PermissionError("Invalid system password")
    sym = symbol.strip().upper()
    price = _last_price(sym)
    if not price or price <= 0:
        raise ValueError(f"Could not fetch a live price for {sym}")

    rp = get_risk_params(settings_store.get_risk_profile(db))
    stop_loss = round(price * (1 - rp.stop_loss_pct), 2)
    take_profit = round(price * (1 + rp.take_profit_pct), 2)

    res = portfolio.buy(
        db, sym, qty, price, reason="manual buy (user)",
        stop_loss=stop_loss, take_profit=take_profit,
    )
    if not res.ok:
        raise ValueError(res.message)
    return {"ok": True, "symbol": sym, "qty": qty, "price": price,
            "stop_loss": stop_loss, "take_profit": take_profit}


def manual_sell(db: Session, symbol: str, qty: int, password: str) -> dict:
    if not wallet.check_password(db, password):
        raise PermissionError("Invalid system password")
    sym = symbol.strip().upper()
    pos = portfolio.get_position(db, sym)
    if pos is None or pos.qty <= 0:
        raise ValueError(f"No open position in {sym}")
    price = _last_price(sym) or pos.last_price or pos.avg_price

    res = portfolio.sell(db, sym, qty, price, reason="manual sell (user)")
    if not res.ok:
        raise ValueError(res.message)
    return {"ok": True, "symbol": sym, "qty": min(qty, pos.qty), "price": price}
