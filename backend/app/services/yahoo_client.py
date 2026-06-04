"""Self-contained Yahoo Finance chart client using curl_cffi.

Avoids dependence on yfinance internals so we fully control SSL verification.
Strategy: verify against the configured CA bundle (which includes corporate root
CAs + certifi); if that fails and fallback is enabled, retry without verification
for these PUBLIC, read-only market-data endpoints (no credentials are sent).
"""
from __future__ import annotations

import os
import time

import pandas as pd
from curl_cffi import requests as cr

from app.core.config import settings
from app.core.logging_config import get_logger

log = get_logger("yahoo")

_BASE = "https://query1.finance.yahoo.com/v8/finance/chart/"
_RANGE_FOR_PERIOD = {
    "5d": "5d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y",
}


def _verify_arg():
    bundle = settings.ca_bundle
    if bundle and os.path.exists(bundle):
        return bundle
    return True


def _request(url: str, params: dict) -> dict | None:
    attempts = [(_verify_arg(), True)]
    if settings.data_ssl_fallback_insecure:
        attempts.append((False, False))
    last_err: Exception | None = None
    for verify, secure in attempts:
        try:
            r = cr.get(url, params=params, impersonate="chrome", verify=verify, timeout=20)
            if r.status_code == 200:
                if not secure:
                    log.warning("Fetched %s without SSL verification (fallback)", params.get("symbol", url))
                return r.json()
            last_err = RuntimeError(f"HTTP {r.status_code}")
        except Exception as e:  # noqa: BLE001
            last_err = e
    log.warning("Yahoo request failed for %s: %s", url, last_err)
    return None


def fetch_chart(symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Return an OHLCV DataFrame indexed by timestamp. Empty on failure."""
    rng = _RANGE_FOR_PERIOD.get(period, "6mo")
    data = _request(
        _BASE + symbol,
        {"range": rng, "interval": interval, "includePrePost": "false"},
    )
    if not data:
        return pd.DataFrame()
    try:
        result = data["chart"]["result"][0]
        ts = result.get("timestamp")
        if not ts:
            return pd.DataFrame()
        quote = result["indicators"]["quote"][0]
        df = pd.DataFrame(
            {
                "Open": quote.get("open"),
                "High": quote.get("high"),
                "Low": quote.get("low"),
                "Close": quote.get("close"),
                "Volume": quote.get("volume"),
            },
            index=pd.to_datetime(ts, unit="s"),
        )
        return df.dropna(subset=["Close"])
    except Exception as e:  # noqa: BLE001
        log.warning("parse error for %s: %s", symbol, e)
        return pd.DataFrame()


def fetch_last(symbol: str) -> float | None:
    df = fetch_chart(symbol, period="5d", interval="1d")
    if df.empty:
        return None
    return float(df["Close"].iloc[-1])


def fetch_many(symbols: list[str], period: str = "6mo", pause: float = 0.05) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for s in symbols:
        out[s] = fetch_chart(s, period=period)
        if pause:
            time.sleep(pause)
    return out
