from fastapi import APIRouter, Depends, HTTPException, status
import logging
from typing import List

# Modular imports reflecting the production directory structure
from app.db.supabase import select_one, update_one, select_all
from app.dependencies import get_current_user, get_current_admin_user
from app.schemas.schemas import UserUpdate, UserResponse

# Initialize the router for the users module
router = APIRouter()
logger = logging.getLogger(__name__)

# ============ PROFILE OPERATIONS ============

@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """
    Returns the profile of the currently authenticated user.
    """
    return current_user

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update personal profile information (Name, Email).
    Uses Pydantic model_dump to handle partial updates.
    """
    updated_user = await update_one(
        "users", 
        {"user_id": current_user["user_id"]}, 
        profile_data.model_dump(exclude_unset=True)
    )
    
    if not updated_user:
        logger.error(f"Failed to update profile for user {current_user['user_id']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to update profile"
        )
        
    logger.info(f"✅ Profile updated for user {current_user['user_id']}")
    return updated_user

# ============ ADMIN STAFF OPERATIONS ============

@router.put("/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Activate/deactivate a user.
    Security: Restricted to administrators of the same branch.
    """
    # Fetch target user and verify branch isolation
    target_user = await select_one("users", {"user_id": user_id})
    if not target_user or target_user["branch_id"] != current_user["branch_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found in your branch"
        )
    
    # Prevent admin from deactivating themselves accidentally
    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=400, 
            detail="You cannot deactivate your own administrative account."
        )
        
    new_status = not target_user.get("is_active", True)
    await update_one("users", {"user_id": user_id}, {"is_active": new_status})
    
    logger.info(f"👤 User {user_id} status changed to {'Active' if new_status else 'Inactive'} by admin {current_user['user_id']}")
    return {"message": f"User status successfully updated to {'active' if new_status else 'inactive'}"}

@router.put("/{user_id}/make-admin")
async def make_user_admin(
    user_id: str,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Promote a staff member to an administrative role.
    Security: Restricted to branch administrators.
    """
    target_user = await select_one("users", {"user_id": user_id})
    if not target_user or target_user["branch_id"] != current_user["branch_id"]:
        raise HTTPException(status_code=404, detail="User not found in your branch")

    await update_one("users", {"user_id": user_id}, {"is_admin": True})
    
    logger.info(f"⭐ User {user_id} promoted to Admin by {current_user['user_id']}")
    return {"message": "User has been granted administrative privileges"}