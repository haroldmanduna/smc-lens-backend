"""
Main Analysis Orchestrator.
Runs all services in order and returns complete analysis result.
"""
from services.twelvedata import fetch_all_timeframes, MIN_SL_PIPS
from services.structure import detect_structure, detect_premium_discount, check_htf_conflict
from services.orderblock import find_order_blocks, find_fvgs, find_liquidity_pools
from services.entry import calculate_entry, calculate_sl, calculate_tp
from services.candlestick import detect_candlestick_pattern, analyze_volume
from services.confluence import calculate_confluence
from services.groq_ai import generate_signal_narrative, generate_htf_summary, generate_trial_narrative


TIMEFRAME_ROLES = {
    "monthly": {"label": "HTF Bias (Primary)", "description": "Overall directional bias only"},
    "weekly": {"label": "HTF Bias (Secondary)", "description": "Confirms or rejects Monthly bias"},
    "daily": {"label": "HTF Bias (Tertiary)", "description": "Narrows bias, identifies key HTF OBs"},
    "h4": {"label": "Confirmation TF", "description": "Confirms direction before entry"},
    "entry": {"label": "Entry TF", "description": "Entry trigger only — never overrides HTF bias"}
}


async def run_full_analysis(pair: str, entry_tf: str, user_plan: str) -> dict:
    """
    Complete SMC analysis pipeline.
    Returns full analysis for pro users, limited for trial.
    """

    # ── Step 1: Fetch All Candle Data ─────────────────────────────────────────
    tf_data = await fetch_all_timeframes(pair, entry_tf)
    candle_results = tf_data["data"]
    candle_errors = tf_data["errors"]

    # ── Step 2: Detect Structure on Each Timeframe ───────────────────────────
    structures = {}
    structure_errors = {}

    for role in ["monthly", "weekly", "daily", "h4", "entry"]:
        if candle_results.get(role) and candle_results[role]:
            candles = candle_results[role]["candles"]
            structures[role] = detect_structure(candles)
            structures[role]["timeframe"] = candle_results[role]["timeframe"]
            structures[role]["role"] = TIMEFRAME_ROLES[role]
        else:
            structure_errors[role] = candle_errors.get(role, "Data unavailable")
            structures[role] = {
                "bias": "UNAVAILABLE",
                "reason": structure_errors[role],
                "role": TIMEFRAME_ROLES[role]
            }

    # ── Step 3: Check HTF Conflicts ───────────────────────────────────────────
    conflict_check = check_htf_conflict(structures)
    overall_bias = conflict_check["overall_htf_bias"]

    if overall_bias in ["UNDECIDED", "RANGING"] or not conflict_check["trade_valid"]:
        # Still return partial data but mark signal invalid
        pass

    # ── Step 4: Entry Timeframe Analysis ─────────────────────────────────────
    entry_candles = candle_results.get("entry", {})
    if not entry_candles or not entry_candles.get("candles"):
        return {
            "error": f"Entry timeframe ({entry_tf}) data unavailable — cannot generate signal",
            "partial_data": structures
        }

    entry_candles_list = entry_candles["candles"]
    current_price = entry_candles_list[-1]["close"]

    # ── Step 5: OB, FVG, Liquidity Detection ─────────────────────────────────
    ob_data = find_order_blocks(entry_candles_list, overall_bias)
    fvg_data = find_fvgs(entry_candles_list)
    liquidity_pools = find_liquidity_pools(entry_candles_list)

    # ── Step 6: Premium/Discount ──────────────────────────────────────────────
    entry_structure = structures.get("entry", {})
    premium_discount = detect_premium_discount(entry_candles_list, entry_structure)

    # ── Step 7: Entry/SL/TP Calculation ──────────────────────────────────────
    entry_data = calculate_entry(overall_bias, ob_data, fvg_data, current_price)

    sl_data = {"sl_price": None, "sl_pips": None}
    tp_data = {"tp1": None, "tp2": None, "rr1": None, "rr2": None, "minimum_rr_met": False}

    if entry_data.get("entry_price"):
        sl_data = calculate_sl(overall_bias, entry_data, pair, entry_candles_list)
        if sl_data.get("sl_price"):
            tp_data = calculate_tp(
                overall_bias,
                entry_data["entry_price"],
                sl_data["sl_price"],
                liquidity_pools,
                entry_structure,
                pair
            )

    # ── Step 8: Candlestick + Volume ──────────────────────────────────────────
    zone_high = entry_data.get("zone_high") or current_price
    zone_low = entry_data.get("zone_low") or current_price
    candlestick = detect_candlestick_pattern(entry_candles_list, zone_high, zone_low)
    volume = analyze_volume(entry_candles_list)

    # ── Step 9: Confluence Score ──────────────────────────────────────────────
    confluence = calculate_confluence(
        structures, entry_data, ob_data, fvg_data,
        candlestick, volume, premium_discount, tp_data, overall_bias
    )

    signal_valid = (
        confluence["signal_valid"] and
        conflict_check["trade_valid"] and
        entry_data.get("entry_price") is not None and
        sl_data.get("sl_price") is not None
    )

    # ── Step 10: AI Narrative ──────────────────────────────────────────────────
    # Get key HTF level for summary
    daily_ob = find_order_blocks(
        candle_results.get("daily", {}).get("candles", entry_candles_list),
        overall_bias
    )
    ob_key = "bullish" if overall_bias == "BULLISH" else "bearish"
    key_htf_level = daily_ob.get(ob_key, {}).get("fifty_percent") or current_price

    try:
        if user_plan == "trial":
            ai_narrative = generate_trial_narrative(
                pair, overall_bias, confluence["score"],
                entry_data.get("entry_price"), sl_data.get("sl_price"),
                tp_data.get("tp1"), tp_data.get("rr1")
            )
            htf_summary = None
        else:
            ai_narrative = generate_signal_narrative(
                pair=pair,
                bias=overall_bias,
                monthly_bias=structures.get("monthly", {}).get("bias", "UNAVAILABLE"),
                weekly_bias=structures.get("weekly", {}).get("bias", "UNAVAILABLE"),
                daily_bias=structures.get("daily", {}).get("bias", "UNAVAILABLE"),
                h4_bias=structures.get("h4", {}).get("bias", "UNAVAILABLE"),
                entry_price=entry_data.get("entry_price"),
                sl_price=sl_data.get("sl_price"),
                tp1_price=tp_data.get("tp1"),
                tp2_price=tp_data.get("tp2"),
                rr1=tp_data.get("rr1"),
                confluence_score=confluence["score"],
                candlestick_pattern=candlestick.get("pattern"),
                volume_status=volume.get("status"),
                premium_discount_zone=premium_discount.get("zone"),
                signal_valid=signal_valid,
                conflict_reason="; ".join(conflict_check.get("conflicts", []))
            )
            htf_summary = generate_htf_summary(
                pair=pair,
                monthly_bias=structures.get("monthly", {}).get("bias", "UNAVAILABLE"),
                weekly_bias=structures.get("weekly", {}).get("bias", "UNAVAILABLE"),
                daily_bias=structures.get("daily", {}).get("bias", "UNAVAILABLE"),
                h4_bias=structures.get("h4", {}).get("bias", "UNAVAILABLE"),
                overall_bias=overall_bias,
                entry_tf=entry_tf,
                entry_tf_bias=structures.get("entry", {}).get("bias", "UNAVAILABLE"),
                key_htf_level=key_htf_level,
                premium_discount=premium_discount.get("zone"),
                trade_valid=signal_valid,
                conflicts=conflict_check.get("conflicts", [])
            )
    except Exception as e:
        ai_narrative = f"AI narrative unavailable: {str(e)}"
        htf_summary = None

    # ── Final Result ──────────────────────────────────────────────────────────
    return {
        "pair": pair,
        "entry_timeframe": entry_tf,
        "current_price": current_price,
        "overall_bias": overall_bias,
        "signal_valid": signal_valid,
        "conflict_check": conflict_check,

        # Entry levels
        "entry_price": entry_data.get("entry_price"),
        "entry_type": entry_data.get("entry_type"),
        "stop_loss": sl_data.get("sl_price"),
        "sl_pips": sl_data.get("sl_pips"),
        "take_profit_1": tp_data.get("tp1"),
        "take_profit_2": tp_data.get("tp2"),
        "rr1": tp_data.get("rr1"),
        "rr2": tp_data.get("rr2"),

        # Analysis data
        "confluence": confluence,
        "candlestick_pattern": candlestick,
        "volume": volume,
        "premium_discount": premium_discount,
        "liquidity_pools": liquidity_pools,

        # Top-down (Pro only)
        "top_down": {
            "structures": structures,
            "ob_data": {role: find_order_blocks(
                candle_results.get(role, {}).get("candles", []) or entry_candles_list,
                overall_bias
            ) for role in ["monthly", "weekly", "daily", "h4"]},
            "fvg_data": {role: find_fvgs(
                candle_results.get(role, {}).get("candles", []) or entry_candles_list
            ) for role in ["monthly", "weekly", "daily", "h4"]},
            "htf_summary": htf_summary
        } if user_plan == "pro" else None,

        # AI narrative
        "ai_narrative": ai_narrative,
        "htf_summary": htf_summary,

        # Data quality
        "data_errors": candle_errors,
        "all_timeframes_loaded": len(candle_errors) == 0
    }
