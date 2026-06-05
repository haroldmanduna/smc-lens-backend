from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from middleware.auth import get_current_user, supabase_admin
from datetime import datetime, timezone, timedelta
import os

router = APIRouter(prefix="/api/auth", tags=["Auth"])

SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "haroldmanduna388@gmail.com")


class RegisterRequest(BaseModel):
    email: str
    full_name: str


@router.post("/register-profile")
async def register_profile(data: RegisterRequest, user: dict = Depends(get_current_user)):
    """
    Called after Supabase auth signup to create the user profile.
    """
    existing = supabase_admin.table("users").select("id").eq("id", user["id"]).execute()
    if existing.data:
        return {"message": "Profile already exists", "user": user}

    role = "super_admin" if data.email == SUPER_ADMIN_EMAIL else "user"
    plan = "pro" if data.email == SUPER_ADMIN_EMAIL else "trial"

    now = datetime.now(timezone.utc)
    trial_end = now + timedelta(days=30)

    new_user = supabase_admin.table("users").insert({
        "id": user["id"],
        "email": data.email,
        "full_name": data.full_name,
        "plan": plan,
        "role": role,
        "trial_start": now.isoformat(),
        "trial_end": trial_end.isoformat(),
        "is_active": True
    }).execute()

    return {"message": "Profile created", "user": new_user.data[0] if new_user.data else {}}


@router.get("/me")
async def get_my_profile(user: dict = Depends(get_current_user)):
    return {"user": user}


@router.get("/announcements")
async def get_announcements():
    result = supabase_admin.table("announcements").select("*").eq("is_active", True).order(
        "created_at", desc=True
    ).execute()
    return {"announcements": result.data}


class SupportTicketCreate(BaseModel):
    subject: str
    message: str


@router.post("/support")
async def create_support_ticket(data: SupportTicketCreate, user: dict = Depends(get_current_user)):
    result = supabase_admin.table("support_tickets").insert({
        "user_id": user["id"],
        "subject": data.subject,
        "message": data.message
    }).execute()
    return {"message": "Support ticket submitted. We'll respond within 24 hours.", "ticket_id": result.data[0]["id"]}
