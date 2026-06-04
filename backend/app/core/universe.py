"""Static fallback universe of liquid NSE symbols grouped by index.

Used when live NSE constituent fetch fails (offline / rate-limited). Symbols are
plain NSE tickers; the yfinance suffix `.NS` is appended by the market data adapter.
"""
from __future__ import annotations

NIFTY50: list[str] = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR", "ITC", "SBIN",
    "BHARTIARTL", "LT", "KOTAKBANK", "AXISBANK", "BAJFINANCE", "ASIANPAINT", "MARUTI",
    "HCLTECH", "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO", "NESTLEIND", "POWERGRID",
    "NTPC", "TATAMOTORS", "TATASTEEL", "JSWSTEEL", "ADANIENT", "ADANIPORTS", "COALINDIA",
    "GRASIM", "HINDALCO", "BAJAJFINSV", "TECHM", "ONGC", "CIPLA", "DRREDDY", "BRITANNIA",
    "EICHERMOT", "HEROMOTOCO", "DIVISLAB", "BPCL", "INDUSINDBK", "APOLLOHOSP", "TATACONSUM",
    "BAJAJ-AUTO", "SBILIFE", "HDFCLIFE", "M&M", "SHRIRAMFIN", "LTIM",
]

# A handful of liquid mid/small caps for aggressive profile (illustrative).
NIFTY_NEXT_EXTRA: list[str] = [
    "DLF", "GODREJCP", "HAVELLS", "PIDILITIND", "SIEMENS", "PNB", "BANKBARODA",
    "GAIL", "DABUR", "AMBUJACEM", "VEDL", "ZOMATO", "PAYTM", "IRCTC", "TRENT",
    "NAUKRI", "BEL", "BHEL", "CANBK", "IDFCFIRSTB", "TATAPOWER", "MOTHERSON",
]

SECTOR_HINT: dict[str, str] = {
    "TCS": "IT", "INFY": "IT", "WIPRO": "IT", "HCLTECH": "IT", "TECHM": "IT", "LTIM": "IT",
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking", "AXISBANK": "Banking",
    "KOTAKBANK": "Banking", "INDUSINDBK": "Banking", "PNB": "Banking", "BANKBARODA": "Banking",
    "RELIANCE": "Energy", "ONGC": "Energy", "BPCL": "Energy", "GAIL": "Energy", "NTPC": "Power",
    "POWERGRID": "Power", "TATAPOWER": "Power", "COALINDIA": "Mining", "TATASTEEL": "Metals",
    "JSWSTEEL": "Metals", "HINDALCO": "Metals", "VEDL": "Metals", "MARUTI": "Auto",
    "TATAMOTORS": "Auto", "M&M": "Auto", "EICHERMOT": "Auto", "HEROMOTOCO": "Auto",
    "BAJAJ-AUTO": "Auto", "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG",
    "BRITANNIA": "FMCG", "DABUR": "FMCG", "GODREJCP": "FMCG", "TATACONSUM": "FMCG",
    "SUNPHARMA": "Pharma", "CIPLA": "Pharma", "DRREDDY": "Pharma", "DIVISLAB": "Pharma",
    "APOLLOHOSP": "Healthcare",
}

# Benchmark / regime indices on yfinance.
BENCHMARK_YF = "^NSEI"  # NIFTY 50
VIX_YF = "^INDIAVIX"


def universe_for_profile(profile: str) -> list[str]:
    profile = (profile or "moderate").lower()
    if profile == "conservative":
        return NIFTY50[:30]
    if profile == "aggressive":
        return NIFTY50 + NIFTY_NEXT_EXTRA
    return NIFTY50  # moderate
