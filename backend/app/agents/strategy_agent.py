"""Strategy agent: fuse technical + sentiment into a composite signal."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.logging_config import get_logger
from app.services import market_data, news
from app.services.indicators import TechnicalResult, analyze

log = get_logger("agent.strategy")

# Weights for the composite score.
W_TECHNICAL = 0.7
W_SENTIMENT = 0.3


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
            "rsi": tech.rsi,
            "sma20": tech.sma20,
            "sma50": tech.sma50,
            "atr_pct": tech.atr_pct,
            "sector": sector,
            "news_count": news_count,
            **tech.details,
        },
    )
