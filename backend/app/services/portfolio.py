"""Paper execution engine: simulated buy/sell, positions, P&L.

All fills are immediate at last price adjusted for slippage; brokerage applied per side.
Whole-share constraint enforced (Indian equity delivery). No real orders are placed.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Order, Position, Trade
from app.services import alerts, wallet


@dataclass
class FillResult:
    ok: bool
    message: str
    order: Order | None = None


def _buy_cost(price: float, qty: int) -> tuple[float, float, float]:
    """Return (fill_price, fees, total_debit) for a buy."""
    fill_price = round(price * (1 + settings.slippage_pct), 4)
    gross = fill_price * qty
    fees = round(gross * settings.brokerage_pct, 4)
    return fill_price, fees, round(gross + fees, 2)


def _sell_proceeds(price: float, qty: int) -> tuple[float, float, float]:
    """Return (fill_price, fees, net_credit) for a sell."""
    fill_price = round(price * (1 - settings.slippage_pct), 4)
    gross = fill_price * qty
    fees = round(gross * settings.brokerage_pct, 4)
    return fill_price, fees, round(gross - fees, 2)


def affordable_qty(cash: float, price: float) -> int:
    """Max whole shares buyable with `cash`, accounting for slippage+fees."""
    if price <= 0:
        return 0
    eff = price * (1 + settings.slippage_pct) * (1 + settings.brokerage_pct)
    return int(cash // eff)


def get_position(db: Session, symbol: str) -> Position | None:
    return db.scalar(select(Position).where(Position.symbol == symbol))


def list_positions(db: Session) -> list[Position]:
    return list(db.scalars(select(Position).where(Position.qty > 0)))


def buy(
    db: Session,
    symbol: str,
    qty: int,
    price: float,
    reason: str | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
) -> FillResult:
    if qty <= 0:
        return FillResult(False, "Quantity must be positive")
    fill_price, fees, total = _buy_cost(price, qty)
    bal = wallet.get_balance(db)
    if total > bal:
        return FillResult(False, f"Insufficient cash: need ₹{total:.2f}, have ₹{bal:.2f}")

    wallet.debit(db, total)
    order = Order(
        symbol=symbol, side="BUY", qty=qty, requested_price=price,
        fill_price=fill_price, fees=fees, reason=reason,
    )
    db.add(order)
    db.flush()

    pos = get_position(db, symbol)
    if pos is None or pos.qty == 0:
        pos = pos or Position(symbol=symbol)
        pos.qty = qty
        pos.avg_price = fill_price
        pos.stop_loss = stop_loss
        pos.take_profit = take_profit
        pos.last_price = fill_price
        db.add(pos)
    else:
        new_qty = pos.qty + qty
        pos.avg_price = round((pos.avg_price * pos.qty + fill_price * qty) / new_qty, 4)
        pos.qty = new_qty
        if stop_loss:
            pos.stop_loss = stop_loss
        if take_profit:
            pos.take_profit = take_profit
        pos.last_price = fill_price

    db.add(Trade(symbol=symbol, side="BUY", qty=qty, price=fill_price, fees=fees,
                 realized_pnl=0.0, order_id=order.id))
    db.commit()
    db.refresh(order)
    alerts.push_alert(
        db, f"BUY {qty} {symbol} @ ₹{fill_price:.2f}",
        message=reason or "", level="success", category="trade",
    )
    return FillResult(True, "Buy filled", order)


def sell(
    db: Session, symbol: str, qty: int, price: float, reason: str | None = None
) -> FillResult:
    pos = get_position(db, symbol)
    if pos is None or pos.qty <= 0:
        return FillResult(False, f"No open position in {symbol}")
    qty = min(qty, pos.qty)
    fill_price, fees, net = _sell_proceeds(price, qty)
    realized = round((fill_price - pos.avg_price) * qty - fees, 2)

    wallet.credit(db, net)
    order = Order(
        symbol=symbol, side="SELL", qty=qty, requested_price=price,
        fill_price=fill_price, fees=fees, reason=reason,
    )
    db.add(order)
    db.flush()

    pos.qty -= qty
    pos.last_price = fill_price
    if pos.qty == 0:
        pos.stop_loss = None
        pos.take_profit = None

    db.add(Trade(symbol=symbol, side="SELL", qty=qty, price=fill_price, fees=fees,
                 realized_pnl=realized, order_id=order.id))
    db.commit()
    db.refresh(order)
    alerts.push_alert(
        db, f"SELL {qty} {symbol} @ ₹{fill_price:.2f} (P&L ₹{realized:.2f})",
        message=reason or "", level="warning" if realized < 0 else "success",
        category="trade",
    )
    return FillResult(True, "Sell filled", order)


def mark_to_market(db: Session, prices: dict[str, float]) -> None:
    """Update last_price on open positions from a {symbol: price} map."""
    for pos in list_positions(db):
        p = prices.get(pos.symbol)
        if p:
            pos.last_price = p
    db.commit()


def portfolio_summary(db: Session, prices: dict[str, float] | None = None) -> dict:
    prices = prices or {}
    positions = list_positions(db)
    cash = wallet.get_balance(db)
    holdings = []
    invested = 0.0
    market_value = 0.0
    for pos in positions:
        last = prices.get(pos.symbol) or pos.last_price or pos.avg_price
        val = last * pos.qty
        cost = pos.avg_price * pos.qty
        invested += cost
        market_value += val
        holdings.append(
            {
                "symbol": pos.symbol,
                "qty": pos.qty,
                "avg_price": round(pos.avg_price, 2),
                "last_price": round(last, 2),
                "market_value": round(val, 2),
                "unrealized_pnl": round(val - cost, 2),
                "unrealized_pct": round((val - cost) / cost * 100, 2) if cost else 0.0,
                "stop_loss": round(pos.stop_loss, 2) if pos.stop_loss else None,
                "take_profit": round(pos.take_profit, 2) if pos.take_profit else None,
            }
        )
    realized = sum(
        t.realized_pnl for t in db.scalars(select(Trade)).all()
    )
    equity = round(cash + market_value, 2)
    return {
        "cash": round(cash, 2),
        "invested": round(invested, 2),
        "market_value": round(market_value, 2),
        "equity": equity,
        "unrealized_pnl": round(market_value - invested, 2),
        "realized_pnl": round(realized, 2),
        "holdings": holdings,
    }
