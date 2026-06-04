"""Market data adapters.

Primary source: Yahoo Finance chart API via our own curl_cffi client (`yahoo_client`),
which controls SSL verification (works behind corporate proxies). NSE-native fetch via
nselib is used as best-effort enrichment for index constituents. All network calls are
defensive: on failure we fall back to cached DB data or the static universe.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from app.core.logging_config import get_logger
from app.core.universe import BENCHMARK_YF, SECTOR_HINT, VIX_YF, universe_for_profile
from app.services import yahoo_client

log = get_logger("marketdata")


def to_yf(symbol: str) -> str:
    """Convert an NSE symbol to a Yahoo ticker."""
    s = symbol.strip().upper()
    return f"{s}.NS"


def fetch_history(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Return OHLCV DataFrame (index=date) for a single symbol. Empty on failure."""
    return yahoo_client.fetch_chart(to_yf(symbol), period=period, interval=interval)


def fetch_last_price(symbol: str) -> float | None:
    """Best-effort latest close."""
    return yahoo_client.fetch_last(to_yf(symbol))


def fetch_benchmark_history(period: str = "6mo") -> pd.DataFrame:
    return yahoo_client.fetch_chart(BENCHMARK_YF, period=period, interval="1d")


def fetch_india_vix() -> float | None:
    return yahoo_client.fetch_last(VIX_YF)


def get_universe(profile: str) -> list[dict]:
    """Return list of {symbol, sector} for the given risk profile.

    Tries nselib for live NIFTY constituents; falls back to the static list.
    """
    symbols = universe_for_profile(profile)
    try:
        from nselib import capital_market

        live = capital_market.nifty50_equity_list()
        if live is not None and not live.empty:
            col = "Symbol" if "Symbol" in live.columns else live.columns[0]
            live_syms = [str(s).strip().upper() for s in live[col].tolist()]
            if profile.lower() == "conservative":
                symbols = live_syms[:30]
            elif profile.lower() == "moderate":
                symbols = live_syms
            else:  # aggressive: nifty50 live + static extras
                from app.core.universe import NIFTY_NEXT_EXTRA

                symbols = list(dict.fromkeys(live_syms + NIFTY_NEXT_EXTRA))
            log.info("Loaded %d live NIFTY constituents", len(live_syms))
    except Exception as e:  # noqa: BLE001
        log.info("nselib unavailable, using static universe (%s)", e)

    return [{"symbol": s, "sector": SECTOR_HINT.get(s)} for s in symbols]


def is_market_open(now: dt.datetime | None = None) -> bool:
    """Rudimentary NSE session check (Mon-Fri, 09:15-15:30 IST)."""
    ist = dt.timezone(dt.timedelta(hours=5, minutes=30))
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(ist)
    if now.weekday() >= 5:
        return False
    start = now.replace(hour=9, minute=15, second=0, microsecond=0)
    end = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return start <= now <= end
