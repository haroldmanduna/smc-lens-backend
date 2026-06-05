import httpx
import os
from typing import Optional
import time

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
BASE_URL = "https://api.twelvedata.com"

# Cache to avoid hitting rate limits
_cache = {}
CACHE_TTL = 60  # seconds

TIMEFRAME_MAP = {
    "15min": "15min",
    "30min": "30min",
    "1h": "1h",
    "4h": "4h",
    "1day": "1day",
    "1week": "1week",
    "1month": "1month"
}

HTF_TIMEFRAMES = ["1day", "1week", "1month"]
CONFIRMATION_TIMEFRAME = "4h"

SUPPORTED_PAIRS = [
    "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD",
    "USD/CHF", "NZD/USD", "GBP/JPY", "EUR/JPY", "EUR/GBP",
    "AUD/JPY", "GBP/AUD", "EUR/AUD", "XAU/USD", "XAG/USD"
]

MIN_SL_PIPS = {
    "XAU/USD": 150,
    "GBP/JPY": 30,
    "GBP/USD": 20,
    "USD/JPY": 20,
    "EUR/JPY": 25,
    "AUD/JPY": 25,
    "GBP/AUD": 25,
    "EUR/AUD": 20,
    "EUR/USD": 15,
    "AUD/USD": 15,
    "USD/CAD": 15,
    "USD/CHF": 15,
    "NZD/USD": 15,
    "EUR/GBP": 12,
    "XAG/USD": 50,
}

PIP_VALUE = {
    "XAU/USD": 0.01,
    "XAG/USD": 0.001,
    "USD/JPY": 0.01,
    "GBP/JPY": 0.01,
    "EUR/JPY": 0.01,
    "AUD/JPY": 0.01,
    "DEFAULT": 0.0001
}


def _get_pip_size(pair: str) -> float:
    return PIP_VALUE.get(pair, PIP_VALUE["DEFAULT"])


def _get_cache_key(pair: str, timeframe: str) -> str:
    return f"{pair}_{timeframe}"


def _is_cache_valid(key: str) -> bool:
    if key not in _cache:
        return False
    return (time.time() - _cache[key]["timestamp"]) < CACHE_TTL


async def fetch_candles(pair: str, timeframe: str, outputsize: int = 100) -> dict:
    """
    Fetch OHLCV candle data from TwelveData.
    Returns raw candle list or raises error — never returns estimated data.
    """
    cache_key = _get_cache_key(pair, timeframe)
    if _is_cache_valid(cache_key):
        return _cache[cache_key]["data"]

    symbol = pair.replace("/", "")

    params = {
        "symbol": symbol,
        "interval": timeframe,
        "outputsize": outputsize,
        "apikey": TWELVEDATA_API_KEY,
        "format": "JSON"
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(f"{BASE_URL}/time_series", params=params)
        response.raise_for_status()
        data = response.json()

    if data.get("status") == "error":
        raise ValueError(f"TwelveData error for {pair} {timeframe}: {data.get('message', 'Unknown error')}")

    values = data.get("values")
    if not values or len(values) < 10:
        raise ValueError(f"Insufficient candle data for {pair} {timeframe} — got {len(values) if values else 0} candles, need at least 10")

    candles = []
    for v in reversed(values):  # oldest first
        candles.append({
            "open": float(v["open"]),
            "high": float(v["high"]),
            "low": float(v["low"]),
            "close": float(v["close"]),
            "volume": float(v.get("volume", 0)),
            "datetime": v["datetime"]
        })

    _cache[cache_key] = {"data": candles, "timestamp": time.time()}
    return candles


async def fetch_all_timeframes(pair: str, entry_tf: str) -> dict:
    """
    Fetch candles for all 5 timeframes.
    Returns dict with results and errors per timeframe.
    Never fills missing data with estimates.
    """
    timeframes = {
        "monthly": "1month",
        "weekly": "1week",
        "daily": "1day",
        "h4": "4h",
        "entry": entry_tf
    }

    results = {}
    errors = {}

    for role, tf in timeframes.items():
        try:
            outputsize = 200 if tf in ["1month", "1week"] else 100
            candles = await fetch_candles(pair, tf, outputsize)
            results[role] = {"candles": candles, "timeframe": tf, "role": role}
        except Exception as e:
            errors[role] = str(e)
            results[role] = None

    return {"data": results, "errors": errors}
