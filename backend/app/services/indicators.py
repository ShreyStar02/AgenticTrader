"""Technical analysis: indicators + trend/momentum/volatility scoring.

Produces a normalized technical score in [-1, 1] plus a human-readable rationale.
Uses the `ta` library where helpful, with pandas fallbacks.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class TechnicalResult:
    symbol: str
    score: float
    trend: str
    last_price: float
    rsi: float | None
    sma20: float | None
    sma50: float | None
    atr_pct: float | None
    details: dict = field(default_factory=dict)
    rationale: str = ""


def _sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n).mean()


def _rsi(series: pd.Series, n: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(n).mean()
    loss = (-delta.clip(upper=0)).rolling(n).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.rolling(n).mean()


def analyze(symbol: str, df: pd.DataFrame) -> TechnicalResult | None:
    """Compute a composite technical score from an OHLCV DataFrame."""
    if df is None or df.empty or len(df) < 30:
        return None

    close = df["Close"].astype(float)
    last = float(close.iloc[-1])

    sma20 = _sma(close, 20)
    sma50 = _sma(close, 50)
    rsi = _rsi(close, 14)
    macd, macd_sig = _macd(close)
    atr = _atr(df, 14)

    sma20_v = float(sma20.iloc[-1]) if not np.isnan(sma20.iloc[-1]) else None
    sma50_v = float(sma50.iloc[-1]) if len(sma50.dropna()) else None
    rsi_v = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else None
    atr_v = float(atr.iloc[-1]) if not np.isnan(atr.iloc[-1]) else None
    atr_pct = (atr_v / last) if (atr_v and last) else None

    reasons: list[str] = []
    components: list[float] = []

    # 1) Price vs SMA20 (trend follow)
    if sma20_v:
        d = (last - sma20_v) / sma20_v
        c = float(np.clip(d * 8, -1, 1))
        components.append(c)
        reasons.append(f"price {'above' if d>=0 else 'below'} SMA20 ({d*100:.1f}%)")

    # 2) SMA20 vs SMA50 (golden/death cross bias)
    if sma20_v and sma50_v:
        d = (sma20_v - sma50_v) / sma50_v
        c = float(np.clip(d * 10, -1, 1))
        components.append(c)
        reasons.append(f"SMA20 {'>' if d>=0 else '<'} SMA50")

    # 3) RSI momentum (centered at 50, penalize overbought >70)
    if rsi_v is not None:
        c = float(np.clip((rsi_v - 50) / 30, -1, 1))
        if rsi_v > 75:
            c -= 0.4  # overbought caution
        if rsi_v < 25:
            c += 0.2  # oversold bounce potential
        c = float(np.clip(c, -1, 1))
        components.append(c)
        reasons.append(f"RSI {rsi_v:.0f}")

    # 4) MACD histogram
    hist = float((macd - macd_sig).iloc[-1])
    c = float(np.clip(hist / (last * 0.01 + 1e-9), -1, 1))
    components.append(c)
    reasons.append(f"MACD hist {'+' if hist>=0 else '-'}")

    # 5) Short-term return (10-day)
    if len(close) > 11:
        ret10 = (last - float(close.iloc[-11])) / float(close.iloc[-11])
        c = float(np.clip(ret10 * 5, -1, 1))
        components.append(c)
        reasons.append(f"10d return {ret10*100:.1f}%")

    score = float(np.clip(np.mean(components), -1, 1)) if components else 0.0

    if score > 0.33:
        trend = "uptrend"
    elif score < -0.33:
        trend = "downtrend"
    else:
        trend = "sideways"

    return TechnicalResult(
        symbol=symbol,
        score=round(score, 4),
        trend=trend,
        last_price=round(last, 2),
        rsi=round(rsi_v, 1) if rsi_v is not None else None,
        sma20=round(sma20_v, 2) if sma20_v else None,
        sma50=round(sma50_v, 2) if sma50_v else None,
        atr_pct=round(atr_pct, 4) if atr_pct else None,
        details={
            "macd_hist": round(hist, 4),
            "components": [round(x, 3) for x in components],
        },
        rationale="; ".join(reasons),
    )
