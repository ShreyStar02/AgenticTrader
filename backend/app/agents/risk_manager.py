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
    """Exit rules for an open position (stop-loss / take-profit / trend reversal)."""
    if stop_loss and last_price <= stop_loss:
        return SellDecision(True, f"stop-loss hit (₹{last_price:.2f} ≤ ₹{stop_loss:.2f})")
    if take_profit and last_price >= take_profit:
        return SellDecision(True, f"take-profit hit (₹{last_price:.2f} ≥ ₹{take_profit:.2f})")
    if score <= -0.4:
        return SellDecision(True, f"trend reversal (score {score:.2f})")
    return SellDecision(False, "hold")
