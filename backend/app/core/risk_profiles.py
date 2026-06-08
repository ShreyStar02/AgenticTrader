"""Risk profile definitions and parameters."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskParams:
    name: str
    max_positions: int
    max_alloc_pct: float          # max % of total equity in a single position
    stop_loss_pct: float          # trailing/initial stop distance
    take_profit_pct: float        # target distance
    min_score_to_buy: float       # composite signal threshold to open
    max_daily_trades: int
    allow_midcap: bool
    cash_buffer_pct: float        # keep this % of equity as cash
    # --- Intraday momentum trades (used when the daily regime is risk-off) ---
    # These keep the agent active in bearish/volatile markets WITHOUT taking on
    # trend risk: a higher score bar, smaller size and tight stops cap the downside.
    intraday_enabled: bool = False
    intraday_min_score: float = 0.55      # higher conviction bar than swing entries
    intraday_max_trades: int = 0          # per-day cap on intraday entries
    intraday_stop_loss_pct: float = 0.015
    intraday_take_profit_pct: float = 0.025
    intraday_max_alloc_pct: float = 0.10  # smaller per-position size than swing
    # --- Intraday short selling (sell-then-buy, mandatory same-day cover) ---
    # Only taken when momentum is strongly DOWN and the daily trend confirms it.
    # Every short is force-covered >=30 min before the close, so there is never
    # overnight short risk. Sizing is small and stops are tight to keep any loss
    # rare and shallow.
    short_enabled: bool = False
    short_min_score: float = 0.25         # require intraday score <= -this
    short_max_trades: int = 0             # per-day cap on short entries
    short_stop_loss_pct: float = 0.015    # cover if price rises this far (loss)
    short_take_profit_pct: float = 0.030  # cover if price falls this far (profit)
    short_max_alloc_pct: float = 0.10     # small notional per short


PROFILES: dict[str, RiskParams] = {
    "conservative": RiskParams(
        name="conservative", max_positions=3, max_alloc_pct=0.40, stop_loss_pct=0.04,
        take_profit_pct=0.08, min_score_to_buy=0.45, max_daily_trades=2,
        allow_midcap=False, cash_buffer_pct=0.20,
        # Conservative stays out of intraday momentum entirely.
        intraday_enabled=False,
    ),
    "moderate": RiskParams(
        name="moderate", max_positions=5, max_alloc_pct=0.35, stop_loss_pct=0.06,
        take_profit_pct=0.12, min_score_to_buy=0.35, max_daily_trades=4,
        allow_midcap=False, cash_buffer_pct=0.10,
        intraday_enabled=True, intraday_min_score=0.25, intraday_max_trades=2,
        intraday_stop_loss_pct=0.012, intraday_take_profit_pct=0.022,
        intraday_max_alloc_pct=0.10,
    ),
    "aggressive": RiskParams(
        name="aggressive", max_positions=8, max_alloc_pct=0.30, stop_loss_pct=0.09,
        take_profit_pct=0.20, min_score_to_buy=0.25, max_daily_trades=8,
        allow_midcap=True, cash_buffer_pct=0.05,
        intraday_enabled=True, intraday_min_score=0.18, intraday_max_trades=4,
        intraday_stop_loss_pct=0.015, intraday_take_profit_pct=0.030,
        intraday_max_alloc_pct=0.15,
        short_enabled=True, short_min_score=0.18, short_max_trades=3,
        short_stop_loss_pct=0.015, short_take_profit_pct=0.030,
        short_max_alloc_pct=0.10,
    ),
}


def get_risk_params(profile: str) -> RiskParams:
    return PROFILES.get((profile or "moderate").lower(), PROFILES["moderate"])
