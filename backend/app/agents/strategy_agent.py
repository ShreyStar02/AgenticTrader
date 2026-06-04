"""Strategy agent: fuse technical + sentiment into a composite signal."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.core.logging_config import get_logger
from app.services import market_data, news
from app.services.indicators import TechnicalResult, analyze

log = get_logger("agent.strategy")

# Weights for the composite score.
W_TECHNICAL = 0.7
W_SENTIMENT = 0.3

# How many trailing daily points to embed for the detail-view chart.
CHART_POINTS = 130


def _num(x) -> float | None:
    return None if x is None or pd.isna(x) else round(float(x), 2)


def build_chart_series(df: pd.DataFrame, points: int = CHART_POINTS) -> dict:
    """Compact trailing OHLC/SMA/volume series for the signal detail chart."""
    close = df["Close"].astype(float)
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    has_vol = "Volume" in df.columns
    idx = df.index[-points:]

    dates = [d.date().isoformat() if hasattr(d, "date") else str(d) for d in idx]
    series = {
        "dates": dates,
        "close": [_num(v) for v in close.iloc[-points:]],
        "sma20": [_num(v) for v in sma20.iloc[-points:]],
        "sma50": [_num(v) for v in sma50.iloc[-points:]],
    }
    if has_vol:
        vol = df["Volume"].astype(float).iloc[-points:]
        series["volume"] = [None if pd.isna(v) else int(v) for v in vol]
    return series


@dataclass
class StrategySignal:
    symbol: str
    score: float
    technical_score: float
    sentiment_score: float
    trend: str
    last_price: float
    action: str = "HOLD"
    rationale: str = ""
    details: dict = field(default_factory=dict)


def evaluate_symbol(
    symbol: str, sector: str | None, regime_bias: float, with_news: bool = True
) -> StrategySignal | None:
    df = market_data.fetch_history(symbol, period="6mo", interval="1d")
    tech: TechnicalResult | None = analyze(symbol, df)
    if tech is None:
        return None

    sentiment = 0.0
    news_count = 0
    if with_news:
        try:
            items = news.fetch_symbol_news(symbol)
            sentiment = news.aggregate_sentiment(items)
            news_count = len(items)
        except Exception as e:  # noqa: BLE001
            log.debug("news fetch failed for %s: %s", symbol, e)

    composite = W_TECHNICAL * tech.score + W_SENTIMENT * sentiment + regime_bias
    composite = max(-1.0, min(1.0, composite))

    rationale = (
        f"Technical {tech.score:+.2f} ({tech.rationale}); "
        f"sentiment {sentiment:+.2f} from {news_count} headlines; "
        f"regime bias {regime_bias:+.2f}"
    )

    return StrategySignal(
        symbol=symbol,
        score=round(composite, 4),
        technical_score=tech.score,
        sentiment_score=sentiment,
        trend=tech.trend,
        last_price=tech.last_price,
        rationale=rationale,
        details={
            "last_price": tech.last_price,
            "rsi": tech.rsi,
            "sma20": tech.sma20,
            "sma50": tech.sma50,
            "atr_pct": tech.atr_pct,
            "sector": sector,
            "news_count": news_count,
            "chart": build_chart_series(df),
            **tech.details,
        },
    )
