"""
Structure Detection — Pure mathematical logic.
No AI involved. Groq never determines bias.
All values come directly from TwelveData candle data.
"""
from typing import List, Optional


def find_swing_highs(candles: List[dict], lookback: int = 2) -> List[dict]:
    """
    A swing high is a candle whose high is greater than
    the 'lookback' candles on both sides.
    """
    swing_highs = []
    for i in range(lookback, len(candles) - lookback):
        current_high = candles[i]["high"]
        left = all(candles[i - j]["high"] < current_high for j in range(1, lookback + 1))
        right = all(candles[i + j]["high"] < current_high for j in range(1, lookback + 1))
        if left and right:
            swing_highs.append({
                "index": i,
                "price": current_high,
                "datetime": candles[i]["datetime"]
            })
    return swing_highs


def find_swing_lows(candles: List[dict], lookback: int = 2) -> List[dict]:
    """
    A swing low is a candle whose low is less than
    the 'lookback' candles on both sides.
    """
    swing_lows = []
    for i in range(lookback, len(candles) - lookback):
        current_low = candles[i]["low"]
        left = all(candles[i - j]["low"] > current_low for j in range(1, lookback + 1))
        right = all(candles[i + j]["low"] > current_low for j in range(1, lookback + 1))
        if left and right:
            swing_lows.append({
                "index": i,
                "price": current_low,
                "datetime": candles[i]["datetime"]
            })
    return swing_lows


def detect_structure(candles: List[dict]) -> dict:
    """
    Detect market structure bias using swing highs and lows.
    Returns Bullish, Bearish, or Ranging with supporting data.
    This is the ONLY function that determines bias — Groq never overrides this.
    """
    if not candles or len(candles) < 10:
        return {
            "bias": "INSUFFICIENT_DATA",
            "reason": "Not enough candles to determine structure",
            "swing_highs": [],
            "swing_lows": [],
            "last_swing_high": None,
            "last_swing_low": None,
            "prev_swing_high": None,
            "prev_swing_low": None
        }

    swing_highs = find_swing_highs(candles)
    swing_lows = find_swing_lows(candles)

    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return {
            "bias": "RANGING",
            "reason": "Insufficient swing points for clear structure",
            "swing_highs": swing_highs,
            "swing_lows": swing_lows,
            "last_swing_high": swing_highs[-1] if swing_highs else None,
            "last_swing_low": swing_lows[-1] if swing_lows else None,
            "prev_swing_high": swing_highs[-2] if len(swing_highs) >= 2 else None,
            "prev_swing_low": swing_lows[-2] if len(swing_lows) >= 2 else None
        }

    last_sh = swing_highs[-1]["price"]
    prev_sh = swing_highs[-2]["price"]
    last_sl = swing_lows[-1]["price"]
    prev_sl = swing_lows[-2]["price"]

    hh = last_sh > prev_sh  # Higher High
    hl = last_sl > prev_sl  # Higher Low
    lh = last_sh < prev_sh  # Lower High
    ll = last_sl < prev_sl  # Lower Low

    if hh and hl:
        bias = "BULLISH"
        reason = f"HH at {last_sh:.5f} (prev {prev_sh:.5f}), HL at {last_sl:.5f} (prev {prev_sl:.5f})"
    elif lh and ll:
        bias = "BEARISH"
        reason = f"LH at {last_sh:.5f} (prev {prev_sh:.5f}), LL at {last_sl:.5f} (prev {prev_sl:.5f})"
    else:
        bias = "RANGING"
        reason = f"Mixed structure — SH: {last_sh:.5f}, SL: {last_sl:.5f}"

    return {
        "bias": bias,
        "reason": reason,
        "swing_highs": swing_highs[-5:],  # last 5 only
        "swing_lows": swing_lows[-5:],
        "last_swing_high": swing_highs[-1],
        "last_swing_low": swing_lows[-1],
        "prev_swing_high": swing_highs[-2],
        "prev_swing_low": swing_lows[-2]
    }


def detect_premium_discount(candles: List[dict], structure: dict) -> dict:
    """
    Premium = price above 50% of last swing range (look for sells)
    Discount = price below 50% of last swing range (look for buys)
    """
    if not structure.get("last_swing_high") or not structure.get("last_swing_low"):
        return {"zone": "UNKNOWN", "fifty_percent": None, "current_price": None}

    swing_high = structure["last_swing_high"]["price"]
    swing_low = structure["last_swing_low"]["price"]
    fifty_percent = (swing_high + swing_low) / 2
    current_price = candles[-1]["close"]

    zone = "PREMIUM" if current_price > fifty_percent else "DISCOUNT"

    return {
        "zone": zone,
        "fifty_percent": round(fifty_percent, 5),
        "swing_high": round(swing_high, 5),
        "swing_low": round(swing_low, 5),
        "current_price": round(current_price, 5)
    }


def check_htf_conflict(timeframe_structures: dict) -> dict:
    """
    Check for conflicts between timeframes.
    If 4H contradicts Daily → no trade.
    If Monthly and Weekly conflict → ranging/undecided.
    """
    monthly = timeframe_structures.get("monthly", {}).get("bias")
    weekly = timeframe_structures.get("weekly", {}).get("bias")
    daily = timeframe_structures.get("daily", {}).get("bias")
    h4 = timeframe_structures.get("h4", {}).get("bias")

    conflicts = []
    valid_biases = ["BULLISH", "BEARISH"]

    # Monthly vs Weekly conflict
    if monthly in valid_biases and weekly in valid_biases and monthly != weekly:
        conflicts.append("Monthly and Weekly bias conflict — HTF direction unclear")

    # 4H vs Daily conflict — this blocks the trade
    h4_daily_conflict = False
    if h4 in valid_biases and daily in valid_biases and h4 != daily:
        conflicts.append("4H contradicts Daily bias — no trade setup")
        h4_daily_conflict = True

    # Determine overall HTF bias from Daily+Weekly alignment
    htf_bias = "UNDECIDED"
    if daily in valid_biases and weekly in valid_biases:
        if daily == weekly:
            htf_bias = daily
        elif monthly == daily:
            htf_bias = daily
        else:
            htf_bias = "RANGING"
    elif daily in valid_biases:
        htf_bias = daily

    return {
        "has_conflict": len(conflicts) > 0,
        "h4_daily_conflict": h4_daily_conflict,
        "conflicts": conflicts,
        "overall_htf_bias": htf_bias,
        "trade_valid": not h4_daily_conflict
    }
