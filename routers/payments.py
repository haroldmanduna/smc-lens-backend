from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from middleware.auth import get_current_user, supabase_admin
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/api/payments", tags=["Payments"])

ECOCASH_NUMBER = "0777441482"
ECOCASH_NAME = "Harold Manduna"
MONTHLY_PRICE_USD = 10.00


class PaymentSubmission(BaseModel):
    ecocash_reference: str


@router.get("/info")
async def get_payment_info():
    """
    Return EcoCash payment instructions.
    """
    return {
        "method": "EcoCash",
        "number": ECOCASH_NUMBER,
        "name": ECOCASH_NAME,
        "amount_usd": MONTHLY_PRICE_USD,
        "instructions": [
            f"1. Open your EcoCash app",
            f"2. Send $10 USD equivalent to {ECOCASH_NUMBER} ({ECOCASH_NAME})",
            f"3. Copy your transaction reference number",
            f"4. Come back here and enter your reference to submit for verification",
            f"5. Your account will be upgraded within 24 hours of payment confirmation"
        ],
        "note": "Manual verification — allow up to 24 hours. Contact support if delayed."
    }


@router.post("/submit")
async def submit_payment(data: PaymentSubmission, user: dict = Depends(get_current_user)):
    """
    User submits EcoCash transaction reference for verification.
    """
    if not data.ecocash_reference or len(data.ecocash_reference.strip()) < 5:
        raise HTTPException(status_code=400, detail="Please enter a valid EcoCash transaction reference")

    # Check for duplicate reference
    existing = supabase_admin.table("payments").select("id").eq(
        "ecocash_reference", data.ecocash_reference.strip()
    ).execute()

    if existing.data:
        raise HTTPException(
            status_code=400,
            detail="This transaction reference has already been submitted. Contact support if this is an error."
        )

    # Check if user already has a pending payment
    pending = supabase_admin.table("payments").select("id").eq(
        "user_id", user["id"]
    ).eq("status", "pending").execute()

    if pending.data:
        raise HTTPException(
            status_code=400,
            detail="You already have a pending payment under review. Please wait for verification."
        )

    # Save payment record
    payment = supabase_admin.table("payments").insert({
        "user_id": user["id"],
        "ecocash_reference": data.ecocash_reference.strip().upper(),
        "amount": MONTHLY_PRICE_USD,
        "currency": "USD",
        "status": "pending"
    }).execute()

    return {
        "message": "Payment submitted successfully! Your account will be upgraded within 24 hours after verification.",
        "reference": data.ecocash_reference.strip().upper(),
        "payment_id": payment.data[0]["id"] if payment.data else None
    }


@router.get("/status")
async def get_payment_status(user: dict = Depends(get_current_user)):
    """
    Get user's payment and subscription status.
    """
    payments = supabase_admin.table("payments").select("*").eq(
        "user_id", user["id"]
    ).order("created_at", desc=True).limit(5).execute()

    subscriptions = supabase_admin.table("subscriptions").select("*").eq(
        "user_id", user["id"]
    ).order("created_at", desc=True).limit(1).execute()

    trial_end = user.get("trial_end")
    days_remaining = None
    if trial_end and user["plan"] == "trial":
        trial_end_dt = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
        delta = trial_end_dt - datetime.now(timezone.utc)
        days_remaining = max(0, delta.days)

    return {
        "plan": user["plan"],
        "trial_days_remaining": days_remaining,
        "payments": payments.data,
        "subscription": subscriptions.data[0] if subscriptions.data else None
    }
