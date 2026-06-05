import os
from fastapi import HTTPException, Header
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "haroldmanduna388@gmail.com")

supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


async def get_current_user(authorization: str = Header(None)) -> dict:
    """
    Verify JWT token from Supabase and return user data.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.replace("Bearer ", "")

    try:
        # Verify token with Supabase
        user_response = supabase_admin.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        supabase_user = user_response.user

        # Get user profile from our users table
        user_data = supabase_admin.table("users").select("*").eq("id", supabase_user.id).single().execute()

        if not user_data.data:
            raise HTTPException(status_code=404, detail="User profile not found")

        user = user_data.data

        # Check if suspended
        if user.get("is_suspended"):
            raise HTTPException(status_code=403, detail="Account suspended. Contact support.")

        # Check trial expiry
        if user["plan"] == "trial":
            from datetime import datetime, timezone
            trial_end = user.get("trial_end")
            if trial_end:
                trial_end_dt = datetime.fromisoformat(trial_end.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > trial_end_dt:
                    # Downgrade expired trial
                    supabase_admin.table("users").update({
                        "plan": "trial",
                        "is_active": False
                    }).eq("id", user["id"]).execute()
                    raise HTTPException(
                        status_code=403,
                        detail="Free trial expired. Please upgrade to Pro to continue."
                    )

        return user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


async def require_pro(user: dict = None) -> dict:
    if user["plan"] != "pro":
        raise HTTPException(
            status_code=403,
            detail="This feature requires a Pro subscription. Upgrade for $10/month."
        )
    return user


async def require_admin(user: dict = None) -> dict:
    if user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_super_admin(user: dict = None) -> dict:
    if user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")
    return user
