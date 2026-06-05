from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from middleware.auth import get_current_user, supabase_admin
from services.analyzer import run_full_analysis
from services.twelvedata import SUPPORTED_PAIRS

router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


class AnalysisRequest(BaseModel):
    pair: str
    entry_timeframe: str


VALID_ENTRY_TIMEFRAMES = ["15min", "30min", "1h", "4h"]


@router.post("/run")
async def run_analysis(request: AnalysisRequest, user: dict = Depends(get_current_user)):
    """
    Run full SMC analysis for a pair and timeframe.
    Returns full data for Pro users, limited for trial.
    """
    # Validate pair
    if request.pair not in SUPPORTED_PAIRS:
        raise HTTPException(
            status_code=400,
            detail=f"Pair {request.pair} not supported. Supported: {SUPPORTED_PAIRS}"
        )

    # Validate entry timeframe
    if request.entry_timeframe not in VALID_ENTRY_TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe. Use one of: {VALID_ENTRY_TIMEFRAMES}"
        )

    try:
        result = await run_full_analysis(
            pair=request.pair,
            entry_tf=request.entry_timeframe,
            user_plan=user["plan"]
        )

        # Save signal to database
        if result.get("entry_price"):
            signal_record = {
                "user_id": user["id"],
                "pair": request.pair,
                "entry_timeframe": request.entry_timeframe,
                "bias": result.get("overall_bias"),
                "entry_price": result.get("entry_price"),
                "stop_loss": result.get("stop_loss"),
                "take_profit_1": result.get("take_profit_1"),
                "take_profit_2": result.get("take_profit_2"),
                "rr_ratio": result.get("rr1"),
                "confluence_score": result.get("confluence", {}).get("score"),
                "confluence_details": result.get("confluence", {}).get("breakdown"),
                "candlestick_pattern": result.get("candlestick_pattern", {}).get("pattern"),
                "volume_status": result.get("volume", {}).get("status"),
                "ai_narrative": result.get("ai_narrative"),
                "htf_bias_summary": result.get("htf_summary"),
                "signal_valid": result.get("signal_valid"),
                "conflict_reason": "; ".join(result.get("conflict_check", {}).get("conflicts", []))
            }
            supabase_admin.table("signals").insert(signal_record).execute()

            # Track API usage
            _track_api_usage("twelvedata", 7)  # 7 calls per analysis (5 TF + cache)
            _track_api_usage("groq", 1 if user["plan"] == "trial" else 2)

        return result

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/history")
async def get_signal_history(user: dict = Depends(get_current_user)):
    """
    Get signal history.
    Trial: last 3 signals only.
    Pro: unlimited.
    """
    query = supabase_admin.table("signals").select("*").eq("user_id", user["id"]).order("created_at", desc=True)

    if user["plan"] == "trial":
        query = query.limit(3)

    result = query.execute()
    return {"signals": result.data, "plan": user["plan"]}


@router.get("/pairs")
async def get_supported_pairs():
    return {"pairs": SUPPORTED_PAIRS}


@router.get("/timeframes")
async def get_supported_timeframes():
    return {
        "entry_timeframes": VALID_ENTRY_TIMEFRAMES,
        "htf_timeframes": ["4h", "1day", "1week", "1month"],
        "note": "HTF timeframes are automatic — not user-selected"
    }


def _track_api_usage(service: str, calls: int):
    try:
        from datetime import date
        today = str(date.today())
        existing = supabase_admin.table("api_usage").select("*").eq("service", service).eq("date", today).execute()
        if existing.data:
            new_count = existing.data[0]["calls_made"] + calls
            supabase_admin.table("api_usage").update({"calls_made": new_count}).eq("service", service).eq("date", today).execute()
        else:
            supabase_admin.table("api_usage").insert({"service": service, "calls_made": calls, "date": today}).execute()
    except Exception:
        pass  # Non-critical, don't break analysis
