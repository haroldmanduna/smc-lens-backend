"""
Candlestick Pattern Detection at OB/FVG zones.
Volume Analysis for confluence scoring.
Pure math — no AI.
"""
from typing import List, Optional


def detect_candlestick_pattern(candles: List[dict], zone_high: float, zone_low: float) -> dict:
    """
    Detect confirmation candlestick patterns at OB/FVG zones.
    Only meaningful if price is currently at or near the zone.
    """
    if not candles or len(candles) < 3:
        return {"pattern": "No confirmation pattern yet", "strength": "NONE"}

    c1 = candles[-3]
    c2 = candles[-2]
    c3 = candles[-1]

    zone_range = zone_high - zone_low
    c3_body = abs(c3["close"] - c3["open"])
    c3_range = c3["high"] - c3["low"]
    c3_upper_wick = c3["high"] - max(c3["open"], c3["close"])
    c3_lower_wick = min(c3["open"], c3["close"]) - c3["low"]
    c3_bullish = c3["close"] > c3["open"]

    # Check if price is near the zone
    current_price = c3["close"]
    near_zone = zone_low <= current_price <= zone_high or \
                abs(current_price - zone_high) / zone_range < 0.3 or \
                abs(current_price - zone_low) / zone_range < 0.3

    if not near_zone:
        return {"pattern": "Price not at zone yet", "strength": "WAITING"}

    # ── Bullish Patterns ──────────────────────────────────────────────────────

    # Bullish Engulfing
    if (c2["close"] < c2["open"] and  # c2 bearish
        c3["close"] > c3["open"] and  # c3 bullish
        c3["open"] <= c2["close"] and
        c3["close"] >= c2["open"]):
        return {"pattern": "Bullish Engulfing", "strength": "STRONG", "direction": "BULLISH"}

    # Hammer (bullish)
    if (c3_lower_wick >= c3_body * 2 and
        c3_upper_wick <= c3_body * 0.3 and
        c3_range > 0):
        return {"pattern": "Hammer", "strength": "MODERATE", "direction": "BULLISH"}

    # Morning Star
    if (c1["close"] < c1["open"] and  # c1 bearish
        abs(c2["close"] - c2["open"]) < (c1["high"] - c1["low"]) * 0.3 and  # c2 small
        c3["close"] > c3["open"] and  # c3 bullish
        c3["close"] > (c1["open"] + c1["close"]) / 2):
        return {"pattern": "Morning Star", "strength": "STRONG", "direction": "BULLISH"}

    # Bullish Pin Bar
    if (c3_lower_wick >= c3_range * 0.6 and c3_bullish):
        return {"pattern": "Bullish Pin Bar", "strength": "MODERATE", "direction": "BULLISH"}

    # ── Bearish Patterns ──────────────────────────────────────────────────────

    # Bearish Engulfing
    if (c2["close"] > c2["open"] and  # c2 bullish
        c3["close"] < c3["open"] and  # c3 bearish
        c3["open"] >= c2["close"] and
        c3["close"] <= c2["open"]):
        return {"pattern": "Bearish Engulfing", "strength": "STRONG", "direction": "BEARISH"}

    # Shooting Star
    if (c3_upper_wick >= c3_body * 2 and
        c3_lower_wick <= c3_body * 0.3 and
        c3_range > 0):
        return {"pattern": "Shooting Star", "strength": "MODERATE", "direction": "BEARISH"}

    # Evening Star
    if (c1["close"] > c1["open"] and
        abs(c2["close"] - c2["open"]) < (c1["high"] - c1["low"]) * 0.3 and
        c3["close"] < c3["open"] and
        c3["close"] < (c1["open"] + c1["close"]) / 2):
        return {"pattern": "Evening Star", "strength": "STRONG", "direction": "BEARISH"}

    # Bearish Pin Bar
    if (c3_upper_wick >= c3_range * 0.6 and not c3_bullish):
        return {"pattern": "Bearish Pin Bar", "strength": "MODERATE", "direction": "BEARISH"}

    # Doji at key level
    if c3_body <= c3_range * 0.1 and c3_range > 0:
        return {"pattern": "Doji at Key Level", "strength": "WEAK", "direction": "NEUTRAL"}

    return {"pattern": "No confirmation pattern yet", "strength": "NONE"}


def analyze_volume(candles: List[dict]) -> dict:
    """
    Compare last candle volume to 20-candle average.
    Above average = strong confluence. Below = weak.
    If volume data is unavailable (some forex pairs), return neutral.
    """
    if not candles or len(candles) < 5:
        return {"status": "INSUFFICIENT_DATA", "ratio": None, "score": 0}

    # Check if volume data exists
    volumes = [c.get("volume", 0) for c in candles[-21:]]
    if all(v == 0 for v in volumes):
        return {
            "status": "UNAVAILABLE",
            "note": "Volume not available for this instrument",
            "ratio": None,
            "score": 0
        }

    recent_volumes = volumes[-21:-1]  # last 20 candles excluding current
    current_volume = volumes[-1]

    if not recent_volumes or sum(recent_volumes) == 0:
        return {"status": "INSUFFICIENT_DATA", "ratio": None, "score": 0}

    avg_volume = sum(recent_volumes) / len(recent_volumes)
    ratio = round(current_volume / avg_volume, 2) if avg_volume > 0 else 0

    if ratio >= 1.5:
        return {"status": "STRONG", "ratio": ratio, "score": 1, "note": f"Volume {ratio}x above average — strong confirmation"}
    elif ratio >= 1.0:
        return {"status": "AVERAGE", "ratio": ratio, "score": 0, "note": f"Volume at average levels"}
    else:
        return {"status": "WEAK", "ratio": ratio, "score": 0, "note": f"Volume below average — weak confirmation"}
