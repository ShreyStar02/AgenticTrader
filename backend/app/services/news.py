"""News & sentiment agent service.

Pulls free RSS feeds (Google News queries + broad market feeds), deduplicates,
maps headlines to symbols, and assigns a lightweight lexicon-based sentiment.
No paid APIs, no scraping of paywalled content.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import urllib.parse

from app.core.logging_config import get_logger

log = get_logger("news")

# Broad market feeds (free, public RSS).
MARKET_FEEDS = [
    "https://news.google.com/rss/search?q=NSE+India+stock+market&hl=en-IN&gl=IN&ceid=IN:en",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://www.moneycontrol.com/rss/business.xml",
]

POSITIVE = {
    "surge", "jump", "gain", "gains", "rise", "rises", "rally", "profit", "beat",
    "beats", "upgrade", "bullish", "record", "high", "soar", "soars", "growth",
    "strong", "outperform", "buy", "boost", "wins", "approval", "expansion",
}
NEGATIVE = {
    "fall", "falls", "drop", "drops", "decline", "loss", "losses", "miss", "misses",
    "downgrade", "bearish", "low", "plunge", "plunges", "weak", "underperform", "sell",
    "fraud", "probe", "ban", "cut", "cuts", "slump", "warning", "default", "lawsuit",
}


def _hash(title: str, link: str | None) -> str:
    return hashlib.sha1(f"{title}|{link or ''}".encode()).hexdigest()[:40]


def score_text(text: str) -> float:
    words = {w.strip(".,!?:;()[]'\"").lower() for w in text.split()}
    pos = len(words & POSITIVE)
    neg = len(words & NEGATIVE)
    if pos == 0 and neg == 0:
        return 0.0
    return max(-1.0, min(1.0, (pos - neg) / (pos + neg)))


def _parse_feed(url: str) -> list[dict]:
    import feedparser

    out: list[dict] = []
    try:
        parsed = feedparser.parse(url)
        source = parsed.feed.get("title", urllib.parse.urlparse(url).netloc) if parsed.feed else url
        for entry in parsed.entries[:40]:
            title = entry.get("title", "").strip()
            if not title:
                continue
            link = entry.get("link")
            published = None
            if entry.get("published_parsed"):
                published = dt.datetime(*entry.published_parsed[:6], tzinfo=dt.timezone.utc)
            out.append(
                {
                    "title": title,
                    "link": link,
                    "source": source,
                    "published_at": published,
                    "sentiment": score_text(title),
                    "hash": _hash(title, link),
                }
            )
    except Exception as e:  # noqa: BLE001
        log.warning("feed parse failed %s: %s", url, e)
    return out


def fetch_market_news() -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    for url in MARKET_FEEDS:
        for it in _parse_feed(url):
            if it["hash"] in seen:
                continue
            seen.add(it["hash"])
            items.append(it)
    return items


def fetch_symbol_news(symbol: str, name: str | None = None) -> list[dict]:
    """Fetch news for a specific symbol via Google News RSS query."""
    query = urllib.parse.quote(f"{name or symbol} NSE share")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
    items = _parse_feed(url)
    for it in items:
        it["symbol"] = symbol
    return items


def aggregate_sentiment(items: list[dict]) -> float:
    if not items:
        return 0.0
    vals = [i["sentiment"] for i in items]
    return round(sum(vals) / len(vals), 4)
