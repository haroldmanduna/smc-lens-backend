from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
from middleware.auth import get_current_user, require_admin, require_super_admin, supabase_admin
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ── Dependency Helpers ────────────────────────────────────────────────────────

async def admin_user(user: dict = Depends(get_current_user)):
    return await require_admin(user)

async def super_admin_user(user: dict = Depends(get_current_user)):
    return await require_super_admin(user)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def admin_dashboard(admin: dict = Depends(admin_user)):
    """Overview stats for admin panel."""
    users = supabase_admin.table("users").select("id, plan, created_at, is_suspended").execute()
    all_users = users.data or []

    total_users = len(all_users)
    pro_users = len([u for u in all_users if u["plan"] == "pro"])
    trial_users = len([u for u in all_users if u["plan"] == "trial"])
    suspended_users = len([u for u in all_users if u.get("is_suspended")])

    pending_payments = supabase_admin.table("payments").select("id").eq("status", "pending").execute()
    open_tickets = supabase_admin.table("support_tickets").select("id").eq("status", "open").execute()

    api_usage = supabase_admin.table("api_usage").select("*").execute()

    monthly_revenue = pro_users * 10.00

    return {
        "stats": {
            "total_users": total_users,
            "pro_users": pro_users,
            "trial_users": trial_users,
            "suspended_users": suspended_users,
            "monthly_revenue_usd": monthly_revenue,
            "pending_payments": len(pending_payments.data or []),
            "open_tickets": len(open_tickets.data or [])
        },
        "api_usage": api_usage.data or []
    }


# ── User Management ───────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    search: Optional[str] = None,
    plan: Optional[str] = None,
    admin: dict = Depends(admin_user)
):
    query = supabase_admin.table("users").select("*").order("created_at", desc=True)
    result = query.execute()
    users = result.data or []

    if search:
        users = [u for u in users if search.lower() in u.get("email", "").lower() or
                 search.lower() in (u.get("full_name") or "").lower()]
    if plan:
        users = [u for u in users if u["plan"] == plan]

    return {"users": users, "total": len(users)}


@router.patch("/users/{user_id}/plan")
async def update_user_plan(
    user_id: str,
    plan: str,
    admin: dict = Depends(admin_user)
):
    if plan not in ["trial", "pro"]:
        raise HTTPException(status_code=400, detail="Plan must be 'trial' or 'pro'")

    update_data = {"plan": plan, "updated_at": datetime.now(timezone.utc).isoformat()}

    if plan == "pro":
        update_data["is_active"] = True
        # Create subscription record
        supabase_admin.table("subscriptions").insert({
            "user_id": user_id,
            "plan": "pro",
            "status": "active",
            "start_date": datetime.now(timezone.utc).isoformat(),
            "end_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }).execute()

    supabase_admin.table("users").update(update_data).eq("id", user_id).execute()

    return {"message": f"User plan updated to {plan}", "upgraded_by": admin["email"]}


@router.patch("/users/{user_id}/suspend")
async def toggle_suspend_user(user_id: str, admin: dict = Depends(admin_user)):
    user = supabase_admin.table("users").select("*").eq("id", user_id).single().execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found")

    # Super admin cannot be suspended
    if user.data.get("role") == "super_admin":
        raise HTTPException(status_code=403, detail="Cannot suspend Super Admin")

    new_status = not user.data.get("is_suspended", False)
    supabase_admin.table("users").update({
        "is_suspended": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", user_id).execute()

    action = "suspended" if new_status else "unsuspended"
    return {"message": f"User {action} successfully"}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(super_admin_user)):
    user = supabase_admin.table("users").select("role").eq("id", user_id).single().execute()
    if user.data and user.data.get("role") == "super_admin":
        raise HTTPException(status_code=403, detail="Cannot delete Super Admin account")

    supabase_admin.table("users").delete().eq("id", user_id).execute()
    return {"message": "User deleted"}


# ── Payment Management ────────────────────────────────────────────────────────

@router.get("/payments")
async def list_payments(status: Optional[str] = None, admin: dict = Depends(admin_user)):
    query = supabase_admin.table("payments").select(
        "*, users(email, full_name)"
    ).order("created_at", desc=True)

    result = query.execute()
    payments = result.data or []

    if status:
        payments = [p for p in payments if p["status"] == status]

    return {"payments": payments, "total": len(payments)}


@router.patch("/payments/{payment_id}/approve")
async def approve_payment(
    payment_id: str,
    notes: Optional[str] = None,
    admin: dict = Depends(admin_user)
):
    payment = supabase_admin.table("payments").select("*").eq("id", payment_id).single().execute()
    if not payment.data:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.data["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Payment already {payment.data['status']}")

    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)

    # Update payment
    supabase_admin.table("payments").update({
        "status": "approved",
        "reviewed_by": admin["id"],
        "reviewed_at": now.isoformat(),
        "period_start": now.isoformat(),
        "period_end": period_end.isoformat(),
        "notes": notes
    }).eq("id", payment_id).execute()

    # Upgrade user to Pro
    supabase_admin.table("users").update({
        "plan": "pro",
        "is_active": True,
        "updated_at": now.isoformat()
    }).eq("id", payment.data["user_id"]).execute()

    # Create subscription
    supabase_admin.table("subscriptions").insert({
        "user_id": payment.data["user_id"],
        "plan": "pro",
        "status": "active",
        "start_date": now.isoformat(),
        "end_date": period_end.isoformat(),
        "payment_id": payment_id
    }).execute()

    return {"message": "Payment approved. User upgraded to Pro.", "period_end": period_end.isoformat()}


@router.patch("/payments/{payment_id}/reject")
async def reject_payment(
    payment_id: str,
    notes: str,
    admin: dict = Depends(admin_user)
):
    supabase_admin.table("payments").update({
        "status": "rejected",
        "reviewed_by": admin["id"],
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes
    }).eq("id", payment_id).execute()

    return {"message": "Payment rejected"}


# ── Signal Audit Log ──────────────────────────────────────────────────────────

@router.get("/signals")
async def audit_signals(
    user_id: Optional[str] = None,
    pair: Optional[str] = None,
    admin: dict = Depends(admin_user)
):
    query = supabase_admin.table("signals").select(
        "*, users(email)"
    ).order("created_at", desc=True).limit(100)

    result = query.execute()
    signals = result.data or []

    if user_id:
        signals = [s for s in signals if s["user_id"] == user_id]
    if pair:
        signals = [s for s in signals if s["pair"] == pair]

    return {"signals": signals, "total": len(signals)}


# ── Announcements ─────────────────────────────────────────────────────────────

class AnnouncementCreate(BaseModel):
    title: str
    message: str

@router.post("/announcements")
async def create_announcement(data: AnnouncementCreate, admin: dict = Depends(admin_user)):
    result = supabase_admin.table("announcements").insert({
        "title": data.title,
        "message": data.message,
        "created_by": admin["id"],
        "is_active": True
    }).execute()
    return {"message": "Announcement created", "id": result.data[0]["id"]}

@router.patch("/announcements/{ann_id}/toggle")
async def toggle_announcement(ann_id: str, admin: dict = Depends(admin_user)):
    ann = supabase_admin.table("announcements").select("is_active").eq("id", ann_id).single().execute()
    supabase_admin.table("announcements").update({"is_active": not ann.data["is_active"]}).eq("id", ann_id).execute()
    return {"message": "Announcement toggled"}


# ── Feature Flags ─────────────────────────────────────────────────────────────

@router.get("/feature-flags")
async def list_feature_flags(admin: dict = Depends(admin_user)):
    result = supabase_admin.table("feature_flags").select("*").execute()
    return {"flags": result.data}

@router.patch("/feature-flags/{flag_name}")
async def toggle_feature_flag(flag_name: str, admin: dict = Depends(super_admin_user)):
    flag = supabase_admin.table("feature_flags").select("is_enabled").eq("feature_name", flag_name).single().execute()
    if not flag.data:
        raise HTTPException(status_code=404, detail="Feature flag not found")
    new_state = not flag.data["is_enabled"]
    supabase_admin.table("feature_flags").update({
        "is_enabled": new_state,
        "updated_by": admin["id"],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("feature_name", flag_name).execute()
    return {"feature": flag_name, "enabled": new_state}


# ── Admin Management (Super Admin Only) ──────────────────────────────────────

class AddAdminRequest(BaseModel):
    email: str

@router.post("/admins/add")
async def add_admin(data: AddAdminRequest, super_admin: dict = Depends(super_admin_user)):
    user = supabase_admin.table("users").select("*").eq("email", data.email).single().execute()
    if not user.data:
        raise HTTPException(status_code=404, detail="User not found. They must register first.")

    if user.data["role"] == "super_admin":
        raise HTTPException(status_code=400, detail="User is already Super Admin")

    supabase_admin.table("users").update({"role": "admin"}).eq("email", data.email).execute()
    return {"message": f"{data.email} is now an Admin"}

@router.post("/admins/remove")
async def remove_admin(data: AddAdminRequest, super_admin: dict = Depends(super_admin_user)):
    if data.email == super_admin["email"]:
        raise HTTPException(status_code=400, detail="Cannot remove your own Super Admin role")

    supabase_admin.table("users").update({"role": "user"}).eq("email", data.email).execute()
    return {"message": f"{data.email} admin role removed"}

@router.get("/admins")
async def list_admins(super_admin: dict = Depends(super_admin_user)):
    result = supabase_admin.table("users").select("id, email, full_name, role, created_at").in_(
        "role", ["admin", "super_admin"]
    ).execute()
    return {"admins": result.data}


# ── Support Tickets ───────────────────────────────────────────────────────────

@router.get("/tickets")
async def list_tickets(status: Optional[str] = None, admin: dict = Depends(admin_user)):
    query = supabase_admin.table("support_tickets").select(
        "*, users(email)"
    ).order("created_at", desc=True)
    result = query.execute()
    tickets = result.data or []
    if status:
        tickets = [t for t in tickets if t["status"] == status]
    return {"tickets": tickets}

class TicketReply(BaseModel):
    reply: str

@router.patch("/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: str, data: TicketReply, admin: dict = Depends(admin_user)):
    supabase_admin.table("support_tickets").update({
        "status": "resolved",
        "admin_reply": data.reply,
        "resolved_by": admin["id"],
        "resolved_at": datetime.now(timezone.utc).isoformat()
    }).eq("id", ticket_id).execute()
    return {"message": "Ticket resolved"}
