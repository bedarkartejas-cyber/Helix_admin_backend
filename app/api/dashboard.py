from fastapi import APIRouter, Depends, HTTPException
import logging
from typing import Any, List

# Internal imports
from app.db.supabase import select_one, select_all
from app.dependencies import get_current_user
from app.schemas.schemas import DashboardResponse

# Setup logging for production debugging
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/summary", response_model=DashboardResponse)
async def get_dashboard_summary(current_user: Any = Depends(get_current_user)):
    """
    Fetches aggregated data for the dashboard.
    Fix: Safely handles current_user as a dict OR a Pydantic object to prevent AttributeErrors.
    """
    try:
        # --- SAFE DATA EXTRACTION ---
        # Checks if current_user is a dict (current_user['key']) or object (current_user.key)
        if isinstance(current_user, dict):
            uid = current_user.get("user_id")
            bid = current_user.get("branch_id")
            is_admin = current_user.get("is_admin", False)
        else:
            uid = getattr(current_user, "user_id", None)
            bid = getattr(current_user, "branch_id", None)
            is_admin = getattr(current_user, "is_admin", False)

        if not uid or not bid:
            logger.error(f"❌ Session data missing for user: {current_user}")
            raise HTTPException(status_code=401, detail="Invalid session data. Please log in again.")

        logger.info(f"📊 Generating dashboard summary for User: {uid} | Branch: {bid}")

        # 1. Fetch Fresh User Profile (to get the latest name/email)
        user = await select_one("users", {"user_id": uid})
        if not user:
            raise HTTPException(status_code=404, detail="User profile not found.")

        # 2. Fetch Branch Details
        branch = await select_one("branches", {"branch_id": bid})
        if not branch:
            logger.error(f"❌ Branch record {bid} missing for active user {uid}")
            raise HTTPException(status_code=404, detail="Branch record not found.")

        # 3. Get Total Staff Count (Strictly scoped to this branch only)
        branch_staff = await select_all("users", {"branch_id": bid})
        total_staff_count = len(branch_staff)

        # 4. Get Recent Invites (Strictly scoped to this branch only)
        invites = await select_all("invites", {"branch_id": bid})
        
        # Sort invites by created_at descending (latest first) and take the top 5
        recent_invites = sorted(
            invites, 
            key=lambda x: x.get('created_at', ''), 
            reverse=True
        )[:5]

        # 5. Build and Return Response matching DashboardResponse schema
        return {
            "user": user,
            "branch": branch,
            "total_users": total_staff_count,
            "recent_invites": recent_invites,
            "can_manage_users": is_admin
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        # Logs the specific error (like the dict attribute error) for debugging
        logger.error(f"❌ Dashboard logic failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail="An internal error occurred while loading dashboard statistics."
        )