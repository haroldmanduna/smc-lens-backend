"""
Entry, Stop Loss, Take Profit, and RR Calculation.
All values derived from real price data — never estimated.
"""
from typing import Optional
from services.twelvedata import MIN_SL_PIPS, PIP_VALUE


def _get_pip_size(pair: str) -> float:
    return PIP_VALUE.get(pair, PIP_VALUE["DEFAULT"])


def _pips_to_price(pips: float, pair: str) -> float:
    return pips * _get_pip_size(pair)


def calculate_entry(
    bias: str,
    ob_data: dict,
    fvg_data: dict,
    current_price: float
) -> dict:
    """
    Entry = 50% of nearest unmitigated OB or FVG in bias direction.
    OBs take priority over FVGs.
    """
    entry_zone = None
    entry_type = None

    if bias == "BULLISH":
        # Look for bullish OB or FVG below current price
        if ob_data.get("bullish"):
            ob = ob_data["bullish"]
            if ob["high"] < current_price:
                entry_zone = ob
                entry_type = "Bullish Order Block"
        if not entry_zone and fvg_data.get("bullish"):
            fvg = fvg_data["bullish"]
            if fvg["high"] < current_price:
                entry_zone = fvg
                entry_type = "Bullish Fair Value Gap"

    elif bias == "BEARISH":
        # Look for bearish OB or FVG above current price
        if ob_data.get("bearish"):
            ob = ob_data["bearish"]
            if ob["low"] > current_price:
                entry_zone = ob
                entry_type = "Bearish Order Block"
        if not entry_zone and fvg_data.get("bearish"):
            fvg = fvg_data["bearish"]
            if fvg["low"] > current_price:
                entry_zone = fvg
                entry_type = "Bearish Fair Value Gap"

    if not entry_zone:
        return {
            "entry_price": None,
            "entry_type": None,
            "zone_high": None,
            "zone_low": None,
            "error": f"No valid {bias.lower()} entry zone found near current price"
        }

    return {
        "entry_price": entry_zone["fifty_percent"],
        "entry_type": entry_type,
        "zone_high": entry_zone["high"],
        "zone_low": entry_zone["low"]
    }


def calculate_sl(
    bias: str,
    entry_data: dict,
    pair: str,
    candles: list
) -> dict:
    """
    Bullish SL: Below the OB/FVG low minus minimum buffer.
    Bearish SL: Above the OB/FVG high plus minimum buffer.
    Enforces minimum pip distance per pair.
    """
    if not entry_data.get("entry_price"):
        return {"sl_price": None, "sl_pips": None, "error": "No entry price to base SL on"}

    entry_price = entry_data["entry_price"]
    zone_low = entry_data["zone_low"]
    zone_high = entry_data["zone_high"]
    min_pips = MIN_SL_PIPS.get(pair, 15)
    pip_size = _get_pip_size(pair)
    min_sl_distance = min_pips * pip_size

    if bias == "BULLISH":
        # SL below zone low
        raw_sl = zone_low - (pip_size * 3)  # 3 pip buffer below OB low
        distance = entry_price - raw_sl
        if distance < min_sl_distance:
            raw_sl = entry_price - min_sl_distance
        sl_pips = round((entry_price - raw_sl) / pip_size, 1)
        return {
            "sl_price": round(raw_sl, 5),
            "sl_pips": sl_pips,
            "direction": "below_ob_low"
        }

    elif bias == "BEARISH":
        # SL above zone high
        raw_sl = zone_high + (pip_size * 3)  # 3 pip buffer above OB high
        distance = raw_sl - entry_price
        if distance < min_sl_distance:
            raw_sl = entry_price + min_sl_distance
        sl_pips = round((raw_sl - entry_price) / pip_size, 1)
        return {
            "sl_price": round(raw_sl, 5),
            "sl_pips": sl_pips,
            "direction": "above_ob_high"
        }

    return {"sl_price": None, "sl_pips": None, "error": "Invalid bias for SL calculation"}


def calculate_tp(
    bias: str,
    entry_price: float,
    sl_price: float,
    liquidity_pools: dict,
    structure: dict,
    pair: str
) -> dict:
    """
    TP1 = nearest liquidity pool in bias direction.
    TP2 = next HTF OB or swing high/low.
    Minimum RR enforced at 1:2.
    """
    if not entry_price or not sl_price:
        return {"tp1": None, "tp2": None, "rr1": None, "rr2": None, "error": "Missing entry or SL"}

    pip_size = _get_pip_size(pair)
    sl_distance = abs(entry_price - sl_price)
    min_tp1_distance = sl_distance * 2  # Minimum 1:2 RR

    tp1 = None
    tp2 = None

    if bias == "BULLISH":
        # TP targets above entry
        liquidity_above = liquidity_pools.get("equal_highs", [])
        swing_high = structure.get("last_swing_high", {})

        # TP1: nearest liquidity above, must give at least 1:2
        for liq in liquidity_above:
            if liq["price"] - entry_price >= min_tp1_distance:
                tp1 = round(liq["price"], 5)
                break

        # Fallback TP1 from RR
        if not tp1:
            tp1 = round(entry_price + min_tp1_distance, 5)

        # TP2: next swing high or further liquidity
        for liq in liquidity_above:
            if liq["price"] > (tp1 or 0) and liq["price"] - entry_price > min_tp1_distance * 1.5:
                tp2 = round(liq["price"], 5)
                break

        if not tp2 and swing_high.get("price"):
            if swing_high["price"] > (tp1 or entry_price):
                tp2 = round(swing_high["price"], 5)

        if not tp2:
            tp2 = round(entry_price + (sl_distance * 3), 5)

    elif bias == "BEARISH":
        liquidity_below = liquidity_pools.get("equal_lows", [])
        swing_low = structure.get("last_swing_low", {})

        for liq in liquidity_below:
            if entry_price - liq["price"] >= min_tp1_distance:
                tp1 = round(liq["price"], 5)
                break

        if not tp1:
            tp1 = round(entry_price - min_tp1_distance, 5)

        for liq in liquidity_below:
            if liq["price"] < (tp1 or float('inf')) and entry_price - liq["price"] > min_tp1_distance * 1.5:
                tp2 = round(liq["price"], 5)
                break

        if not tp2 and swing_low.get("price"):
            if swing_low["price"] < (tp1 or entry_price):
                tp2 = round(swing_low["price"], 5)

        if not tp2:
            tp2 = round(entry_price - (sl_distance * 3), 5)

    # Calculate RR ratios
    rr1 = None
    rr2 = None
    if tp1 and sl_distance > 0:
        tp1_distance = abs(tp1 - entry_price)
        rr1 = round(tp1_distance / sl_distance, 2)
    if tp2 and sl_distance > 0:
        tp2_distance = abs(tp2 - entry_price)
        rr2 = round(tp2_distance / sl_distance, 2)

    return {
        "tp1": tp1,
        "tp2": tp2,
        "rr1": rr1,
        "rr2": rr2,
        "sl_distance_pips": round(sl_distance / pip_size, 1),
        "minimum_rr_met": rr1 is not None and rr1 >= 2.0
    }
