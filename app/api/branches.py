from fastapi import APIRouter, Depends, HTTPException, status
import logging
from typing import List

# Modular imports reflecting the production directory structure
from app.db.supabase import select_one, update_one, get_users_by_branch
from app.dependencies import get_current_admin_user
from app.schemas.schemas import BranchResponse, BranchUpdate, UserResponse

# Setup logging for store-level administrative auditing
logger = logging.getLogger(__name__)

router = APIRouter()

# ============ BRANCH CONFIGURATION ============

@router.get("/settings", response_model=BranchResponse)
async def get_branch_settings(current_user: dict = Depends(get_current_admin_user)):
    """
    Retrieve the current store/branch details for the administrator.
    Verification: Automatically restricted to the administrator's own branch_id from JWT.
    """
    try:
        # Fetch branch details using the branch_id from the authenticated admin's token
        branch = await select_one("branches", {"branch_id": current_user["branch_id"]})
        
        if not branch:
            logger.warning(f"⚠️ Branch {current_user['branch_id']} not found for admin {current_user['user_id']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Branch details could not be located"
            )
            
        return branch
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching branch settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal server error while retrieving settings"
        )

@router.put("/settings", response_model=BranchResponse)
async def update_branch_settings(
    settings_data: BranchUpdate,
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Updates branch-wide settings (Name, Address, City).
    Security: Uses partial updates (exclude_unset=True) to prevent accidental data overwrites.
    """
    logger.info(f"🔄 Admin {current_user['user_id']} is updating settings for branch {current_user['branch_id']}")
    
    # 1. Prepare data using Pydantic v2 model_dump
    update_data = settings_data.model_dump(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="No valid update fields provided"
        )

    # 2. Apply update strictly to the admin's branch_id
    updated_branch = await update_one(
        "branches", 
        {"branch_id": current_user["branch_id"]}, 
        update_data
    )
    
    if not updated_branch:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to apply branch setting updates to the database"
        )
    
    logger.info(f"✅ Branch settings updated successfully for branch {current_user['branch_id']}")
    return updated_branch

# ============ STAFF MANAGEMENT ============

@router.get("/users", response_model=List[UserResponse])
async def get_branch_staff(current_user: dict = Depends(get_current_admin_user)):
    """
    Retrieves a list of all users/staff members associated with this specific branch.
    Admin Only: Restricted to branch administrators.
    """
    try:
        # Fetch staff members specifically associated with the admin's branch_id
        # This uses the specialized helper in app/db/supabase.py
        staff = await get_users_by_branch(current_user["branch_id"])
        
        if staff is None:
            return []
            
        return staff
    except Exception as e:
        logger.error(f"❌ Error fetching branch staff: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to retrieve staff list from the database"
        )