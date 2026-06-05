"""
Confluence Scoring System — Out of 13.
Minimum score of 8 required to show a signal.
Each factor is calculated from real data, never assumed.
"""


def calculate_confluence(
    timeframe_structures: dict,
    entry_data: dict,
    ob_data: dict,
    fvg_data: dict,
    candlestick: dict,
    volume: dict,
    premium_discount: dict,
    tp_data: dict,
    bias: str
) -> dict:
    """
    Score breakdown:
    Monthly bias aligns:       1
    Weekly bias aligns:        1
    Daily bias aligns:         1
    4H confirms:               2
    Price at discount/premium: 1
    OB present at entry zone:  2
    FVG present at entry zone: 1
    Candlestick confirmation:  2
    Volume above average:      1
    RR minimum 1:2:            1
    ─────────────────────────────
    TOTAL:                    13
    """
    score = 0
    breakdown = {}

    # ── Timeframe Alignment ───────────────────────────────────────────────────

    monthly_bias = timeframe_structures.get("monthly", {}).get("bias", "UNKNOWN")
    weekly_bias = timeframe_structures.get("weekly", {}).get("bias", "UNKNOWN")
    daily_bias = timeframe_structures.get("daily", {}).get("bias", "UNKNOWN")
    h4_bias = timeframe_structures.get("h4", {}).get("bias", "UNKNOWN")

    monthly_aligned = monthly_bias == bias
    weekly_aligned = weekly_bias == bias
    daily_aligned = daily_bias == bias
    h4_aligned = h4_bias == bias

    if monthly_aligned:
        score += 1
    breakdown["monthly_alignment"] = {
        "score": 1 if monthly_aligned else 0,
        "max": 1,
        "detail": f"Monthly: {monthly_bias}"
    }

    if weekly_aligned:
        score += 1
    breakdown["weekly_alignment"] = {
        "score": 1 if weekly_aligned else 0,
        "max": 1,
        "detail": f"Weekly: {weekly_bias}"
    }

    if daily_aligned:
        score += 1
    breakdown["daily_alignment"] = {
        "score": 1 if daily_aligned else 0,
        "max": 1,
        "detail": f"Daily: {daily_bias}"
    }

    h4_score = 2 if h4_aligned else 0
    score += h4_score
    breakdown["h4_confirmation"] = {
        "score": h4_score,
        "max": 2,
        "detail": f"4H: {h4_bias}"
    }

    # ── Premium/Discount ──────────────────────────────────────────────────────

    zone = premium_discount.get("zone", "UNKNOWN")
    pd_aligned = (bias == "BULLISH" and zone == "DISCOUNT") or \
                 (bias == "BEARISH" and zone == "PREMIUM")

    if pd_aligned:
        score += 1
    breakdown["premium_discount"] = {
        "score": 1 if pd_aligned else 0,
        "max": 1,
        "detail": f"Price in {zone} — {'aligned' if pd_aligned else 'not aligned'} with {bias.lower()} bias"
    }

    # ── Order Block ───────────────────────────────────────────────────────────

    ob_key = "bullish" if bias == "BULLISH" else "bearish"
    ob_present = ob_data.get(ob_key) is not None
    ob_score = 2 if ob_present else 0
    score += ob_score
    ob_detail = f"OB at {ob_data[ob_key]['fifty_percent']}" if ob_present else "No OB at entry zone"
    breakdown["order_block"] = {
        "score": ob_score,
        "max": 2,
        "detail": ob_detail
    }

    # ── Fair Value Gap ────────────────────────────────────────────────────────

    fvg_key = "bullish" if bias == "BULLISH" else "bearish"
    fvg_present = fvg_data.get(fvg_key) is not None
    fvg_score = 1 if fvg_present else 0
    score += fvg_score
    fvg_detail = f"FVG at {fvg_data[fvg_key]['fifty_percent']}" if fvg_present else "No FVG at entry zone"
    breakdown["fvg"] = {
        "score": fvg_score,
        "max": 1,
        "detail": fvg_detail
    }

    # ── Candlestick Pattern ───────────────────────────────────────────────────

    pattern = candlestick.get("pattern", "None")
    strength = candlestick.get("strength", "NONE")
    cs_score = 2 if strength == "STRONG" else (1 if strength == "MODERATE" else 0)
    score += cs_score
    breakdown["candlestick"] = {
        "score": cs_score,
        "max": 2,
        "detail": f"{pattern} ({strength})"
    }

    # ── Volume ────────────────────────────────────────────────────────────────

    vol_score = volume.get("score", 0)
    score += vol_score
    breakdown["volume"] = {
        "score": vol_score,
        "max": 1,
        "detail": volume.get("note", "Volume data unavailable")
    }

    # ── Risk/Reward ───────────────────────────────────────────────────────────

    rr_met = tp_data.get("minimum_rr_met", False)
    rr1 = tp_data.get("rr1")
    rr_score = 1 if rr_met else 0
    score += rr_score
    breakdown["risk_reward"] = {
        "score": rr_score,
        "max": 1,
        "detail": f"RR: 1:{rr1}" if rr1 else "RR not calculable"
    }

    # ── Signal Quality ────────────────────────────────────────────────────────

    signal_valid = score >= 8
    if score >= 11:
        quality = "HIGH_PROBABILITY"
        quality_label = "High Probability Setup"
    elif score >= 8:
        quality = "VALID"
        quality_label = "Valid Setup"
    else:
        quality = "INVALID"
        quality_label = f"Setup not ready — score too low ({score}/13, need 8+)"

    return {
        "score": score,
        "max_score": 13,
        "signal_valid": signal_valid,
        "quality": quality,
        "quality_label": quality_label,
        "breakdown": breakdown
    }
