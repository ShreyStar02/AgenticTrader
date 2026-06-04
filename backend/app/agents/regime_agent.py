"""Market regime agent: bullish / bearish / volatile / sideways / risk-off."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.core.logging_config import get_logger
from app.services import market_data

log = get_logger("agent.regime")


@dataclass
class Regime:
    label: str
    bias: float          # -1..1 directional bias applied to buy thresholds
    risk_on: bool
    vix: float | None
    detail: str


def assess_regime() -> Regime:
    df = market_data.fetch_benchmark_history(period="6mo")
    vix = market_data.fetch_india_vix()

    if df is None or df.empty or "Close" not in df:
        return Regime("unknown", 0.0, True, vix, "benchmark unavailable; neutral bias")

    close = df["Close"].astype(float)
    sma50 = close.rolling(50).mean().iloc[-1]
    sma20 = close.rolling(20).mean().iloc[-1]
    last = float(close.iloc[-1])
    ret20 = (last - float(close.iloc[-21])) / float(close.iloc[-21]) if len(close) > 21 else 0.0

    above50 = last > sma50 if not np.isnan(sma50) else True
    above20 = last > sma20 if not np.isnan(sma20) else True

    high_vol = bool(vix and vix >= 20)

    if above50 and above20 and ret20 > 0.01:
        label, bias, risk_on = "bullish", 0.15, True
    elif (not above50) and ret20 < -0.01:
        label, bias, risk_on = "bearish", -0.25, False
    elif high_vol:
        label, bias, risk_on = "volatile", -0.10, False
    else:
        label, bias, risk_on = "sideways", 0.0, True

    detail = (
        f"NIFTY {last:.0f} ({'>' if above50 else '<'}SMA50, "
        f"20d {ret20*100:+.1f}%), VIX {vix:.1f}" if vix else
        f"NIFTY {last:.0f} ({'>' if above50 else '<'}SMA50, 20d {ret20*100:+.1f}%)"
    )
    log.info("Regime=%s bias=%.2f risk_on=%s", label, bias, risk_on)
    return Regime(label, bias, risk_on, vix, detail)
