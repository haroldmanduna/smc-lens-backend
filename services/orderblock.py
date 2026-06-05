"""
Order Block and Fair Value Gap Detection
Pure price action math — no AI involvement.
All levels come directly from TwelveData candle data.
"""
from typing import List, Optional


# ─── ORDER BLOCK DETECTION ────────────────────────────────────────────────────

def find_order_blocks(candles: List[dict], bias: str) -> dict:
    """
    Bullish OB: Last bearish candle before a strong bullish impulse move.
    Bearish OB: Last bullish candle before a strong bearish impulse move.
    Only returns unmitigated OBs (price hasn't closed through them).
    """
    if not candles or len(candles) < 5:
        return {"bullish": None, "bearish": None}

    current_price = candles[-1]["close"]
    bullish_obs = []
    bearish_obs = []

    for i in range(1, len(candles) - 3):
        candle = candles[i]
        next_1 = candles[i + 1]
        next_2 = candles[i + 2]

        # Bullish OB: bearish candle followed by strong bullish move
        if candle["close"] < candle["open"]:  # bearish candle
            impulse_size = next_1["high"] - next_1["low"]
            ob_size = candle["high"] - candle["low"]
            if next_1["close"] > candle["high"] and impulse_size > ob_size:
                ob_high = candle["high"]
                ob_low = candle["low"]
                ob_50 = (ob_high + ob_low) / 2

                # Check if mitigated (price closed inside the OB after formation)
                mitigated = False
                for j in range(i + 2, len(candles)):
                    if candles[j]["close"] < ob_low:
                        mitigated = True
                        break

                if not mitigated and current_price > ob_low:
                    bullish_obs.append({
                        "high": round(ob_high, 5),
                        "low": round(ob_low, 5),
                        "fifty_percent": round(ob_50, 5),
                        "datetime": candle["datetime"],
                        "index": i,
                        "mitigated": False
                    })

        # Bearish OB: bullish candle followed by strong bearish move
        if candle["close"] > candle["open"]:  # bullish candle
            impulse_size = next_1["high"] - next_1["low"]
            ob_size = candle["high"] - candle["low"]
            if next_1["close"] < candle["low"] and impulse_size > ob_size:
                ob_high = candle["high"]
                ob_low = candle["low"]
                ob_50 = (ob_high + ob_low) / 2

                # Check if mitigated
                mitigated = False
                for j in range(i + 2, len(candles)):
                    if candles[j]["close"] > ob_high:
                        mitigated = True
                        break

                if not mitigated and current_price < ob_high:
                    bearish_obs.append({
                        "high": round(ob_high, 5),
                        "low": round(ob_low, 5),
                        "fifty_percent": round(ob_50, 5),
                        "datetime": candle["datetime"],
                        "index": i,
                        "mitigated": False
                    })

    # Return nearest OB to current price
    nearest_bullish = None
    if bullish_obs:
        bullish_obs_below = [ob for ob in bullish_obs if ob["high"] < current_price]
        if bullish_obs_below:
            nearest_bullish = max(bullish_obs_below, key=lambda x: x["high"])

    nearest_bearish = None
    if bearish_obs:
        bearish_obs_above = [ob for ob in bearish_obs if ob["low"] > current_price]
        if bearish_obs_above:
            nearest_bearish = min(bearish_obs_above, key=lambda x: x["low"])

    return {
        "bullish": nearest_bullish,
        "bearish": nearest_bearish,
        "all_bullish": bullish_obs[-3:],
        "all_bearish": bearish_obs[-3:]
    }


# ─── FAIR VALUE GAP DETECTION ────────────────────────────────────────────────

def find_fvgs(candles: List[dict], lookback: int = 10) -> dict:
    """
    Bullish FVG: Candle 1 high < Candle 3 low (gap between them)
    Bearish FVG: Candle 1 low > Candle 3 high (gap between them)
    Only checks last 'lookback' candles.
    Only returns unmitigated FVGs.
    """
    if not candles or len(candles) < 3:
        return {"bullish": None, "bearish": None}

    current_price = candles[-1]["close"]
    recent_candles = candles[-lookback:]

    bullish_fvgs = []
    bearish_fvgs = []

    for i in range(len(recent_candles) - 2):
        c1 = recent_candles[i]
        c3 = recent_candles[i + 2]

        # Bullish FVG: gap between c1 high and c3 low
        if c3["low"] > c1["high"]:
            fvg_high = c3["low"]
            fvg_low = c1["high"]
            fvg_50 = (fvg_high + fvg_low) / 2

            # Check mitigation: price must not have entered the gap
            mitigated = False
            for j in range(i + 2, len(recent_candles)):
                if recent_candles[j]["low"] <= fvg_low:
                    mitigated = True
                    break

            if not mitigated and current_price > fvg_low:
                bullish_fvgs.append({
                    "high": round(fvg_high, 5),
                    "low": round(fvg_low, 5),
                    "fifty_percent": round(fvg_50, 5),
                    "datetime": c1["datetime"],
                    "mitigated": False
                })

        # Bearish FVG: gap between c3 high and c1 low
        if c1["low"] > c3["high"]:
            fvg_high = c1["low"]
            fvg_low = c3["high"]
            fvg_50 = (fvg_high + fvg_low) / 2

            mitigated = False
            for j in range(i + 2, len(recent_candles)):
                if recent_candles[j]["high"] >= fvg_high:
                    mitigated = True
                    break

            if not mitigated and current_price < fvg_high:
                bearish_fvgs.append({
                    "high": round(fvg_high, 5),
                    "low": round(fvg_low, 5),
                    "fifty_percent": round(fvg_50, 5),
                    "datetime": c1["datetime"],
                    "mitigated": False
                })

    nearest_bullish = None
    if bullish_fvgs:
        fvgs_below = [f for f in bullish_fvgs if f["high"] < current_price]
        if fvgs_below:
            nearest_bullish = max(fvgs_below, key=lambda x: x["high"])

    nearest_bearish = None
    if bearish_fvgs:
        fvgs_above = [f for f in bearish_fvgs if f["low"] > current_price]
        if fvgs_above:
            nearest_bearish = min(fvgs_above, key=lambda x: x["low"])

    return {
        "bullish": nearest_bullish,
        "bearish": nearest_bearish,
        "all_bullish": bullish_fvgs,
        "all_bearish": bearish_fvgs
    }


# ─── LIQUIDITY POOLS ─────────────────────────────────────────────────────────

def find_liquidity_pools(candles: List[dict]) -> dict:
    """
    Equal highs and equal lows represent liquidity resting above/below.
    Tolerance = 0.0005 (5 pips) for forex, 0.5 for gold.
    """
    if not candles or len(candles) < 10:
        return {"equal_highs": [], "equal_lows": []}

    current_price = candles[-1]["close"]

    # Determine tolerance based on price level (gold vs forex)
    tolerance = 0.5 if current_price > 100 else 0.0005

    highs = [c["high"] for c in candles[-30:]]
    lows = [c["low"] for c in candles[-30:]]

    equal_highs = []
    equal_lows = []

    for i in range(len(highs)):
        count = sum(1 for h in highs if abs(h - highs[i]) <= tolerance)
        if count >= 2 and highs[i] not in [eh["price"] for eh in equal_highs]:
            equal_highs.append({"price": round(highs[i], 5), "touches": count})

    for i in range(len(lows)):
        count = sum(1 for l in lows if abs(l - lows[i]) <= tolerance)
        if count >= 2 and lows[i] not in [el["price"] for el in equal_lows]:
            equal_lows.append({"price": round(lows[i], 5), "touches": count})

    # Sort: equal highs above price, equal lows below price
    eq_highs_above = sorted(
        [eh for eh in equal_highs if eh["price"] > current_price],
        key=lambda x: x["price"]
    )
    eq_lows_below = sorted(
        [el for el in equal_lows if el["price"] < current_price],
        key=lambda x: x["price"],
        reverse=True
    )

    return {
        "equal_highs": eq_highs_above[:3],
        "equal_lows": eq_lows_below[:3],
        "nearest_high_liquidity": eq_highs_above[0] if eq_highs_above else None,
        "nearest_low_liquidity": eq_lows_below[0] if eq_lows_below else None
    }
