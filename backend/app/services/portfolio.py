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
    """All open positions (long qty>0 and short qty<0)."""
    return list(db.scalars(select(Position).where(Position.qty != 0)))


def short_notional(db: Session) -> float:
    """Total entry notional of open short positions (collateral earmarked)."""
    return sum(abs(p.qty) * p.avg_price for p in list_positions(db) if p.qty < 0)


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
    # Fold brokerage into the cost basis so realized P&L over a full round-trip
    # equals the true cash change (the buy fee is part of what the share cost us).
    cost_per_share = total / qty
    if pos is None or pos.qty == 0:
        pos = pos or Position(symbol=symbol)
        pos.qty = qty
        pos.avg_price = round(cost_per_share, 4)
        pos.stop_loss = stop_loss
        pos.take_profit = take_profit
        pos.last_price = fill_price
        db.add(pos)
    else:
        new_qty = pos.qty + qty
        pos.avg_price = round((pos.avg_price * pos.qty + total) / new_qty, 4)
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


def short_sell(
    db: Session,
    symbol: str,
    qty: int,
    price: float,
    reason: str | None = None,
    stop_loss: float | None = None,
    take_profit: float | None = None,
) -> FillResult:
    """Open a short (sell-to-open). Credits the net proceeds to the wallet and
    records a negative-qty position. Stop-loss sits ABOVE entry, take-profit
    BELOW entry. Refuses to stack onto an existing position."""
    if qty <= 0:
        return FillResult(False, "Quantity must be positive")
    pos = get_position(db, symbol)
    if pos is not None and pos.qty != 0:
        return FillResult(False, f"Already have a position in {symbol}")

    fill_price, fees, net = _sell_proceeds(price, qty)
    wallet.credit(db, net)
    order = Order(
        symbol=symbol, side="SHORT", qty=qty, requested_price=price,
        fill_price=fill_price, fees=fees, reason=reason,
    )
    db.add(order)
    db.flush()

    pos = pos or Position(symbol=symbol)
    pos.qty = -qty
    # Use the NET proceeds per share (after entry brokerage) as the cost basis so
    # realized P&L on cover includes the short-entry fee and reconciles with cash.
    pos.avg_price = round(net / qty, 4)
    pos.stop_loss = stop_loss
    pos.take_profit = take_profit
    pos.last_price = fill_price
    db.add(pos)

    db.add(Trade(symbol=symbol, side="SHORT", qty=qty, price=fill_price, fees=fees,
                 realized_pnl=0.0, order_id=order.id))
    db.commit()
    db.refresh(order)
    alerts.push_alert(
        db, f"SHORT {qty} {symbol} @ ₹{fill_price:.2f}",
        message=reason or "", level="warning", category="trade",
    )
    return FillResult(True, "Short opened", order)


def cover(
    db: Session, symbol: str, qty: int, price: float, reason: str | None = None
) -> FillResult:
    """Close a short (buy-to-cover). Always allowed so a short can never be left
    open. Realized P&L = (entry - cover) * qty - fees."""
    pos = get_position(db, symbol)
    if pos is None or pos.qty >= 0:
        return FillResult(False, f"No open short in {symbol}")
    qty = min(qty, abs(pos.qty))
    fill_price, fees, total = _buy_cost(price, qty)
    realized = round((pos.avg_price - fill_price) * qty - fees, 2)

    wallet.debit(db, total)
    order = Order(
        symbol=symbol, side="COVER", qty=qty, requested_price=price,
        fill_price=fill_price, fees=fees, reason=reason,
    )
    db.add(order)
    db.flush()

    pos.qty += qty  # negative qty moves toward zero
    pos.last_price = fill_price
    if pos.qty == 0:
        pos.stop_loss = None
        pos.take_profit = None

    db.add(Trade(symbol=symbol, side="COVER", qty=qty, price=fill_price, fees=fees,
                 realized_pnl=realized, order_id=order.id))
    db.commit()
    db.refresh(order)
    alerts.push_alert(
        db, f"COVER {qty} {symbol} @ ₹{fill_price:.2f} (P&L ₹{realized:.2f})",
        message=reason or "", level="warning" if realized < 0 else "success",
        category="trade",
    )
    return FillResult(True, "Short covered", order)


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
        is_short = pos.qty < 0
        invested += abs(cost)
        market_value += val
        holdings.append(
            {
                "symbol": pos.symbol,
                "qty": pos.qty,
                "side": "SHORT" if is_short else "LONG",
                "avg_price": round(pos.avg_price, 2),
                "last_price": round(last, 2),
                "market_value": round(val, 2),
                "unrealized_pnl": round(val - cost, 2),
                "unrealized_pct": round((val - cost) / abs(cost) * 100, 2) if cost else 0.0,
                "stop_loss": round(pos.stop_loss, 2) if pos.stop_loss else None,
                "take_profit": round(pos.take_profit, 2) if pos.take_profit else None,
            }
        )
    realized = sum(
        t.realized_pnl for t in db.scalars(select(Trade)).all()
    )
    equity = round(cash + market_value, 2)
    unrealized = round(sum(h["unrealized_pnl"] for h in holdings), 2)
    return {
        "cash": round(cash, 2),
        "invested": round(invested, 2),
        "market_value": round(market_value, 2),
        "equity": equity,
        "unrealized_pnl": unrealized,
        "realized_pnl": round(realized, 2),
        "holdings": holdings,
    }
