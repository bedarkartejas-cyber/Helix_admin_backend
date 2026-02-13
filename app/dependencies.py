from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

# Updated imports to reflect modular structure
from app.core.security import verify_token
from app.db.supabase import select_one

# Initializing security scheme for Bearer token injection
security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Dependency to validate the JWT from the Authorization header and 
    return the current active user from the database.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token using centralized security logic
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    # Fetch user from the centralized database layer
    # This replaces the old supabase_client.py import
    user = await select_one("users", {"user_id": token_data.user_id, "is_active": True})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account is inactive",
        )
    
    return user

async def get_current_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to restrict access to endpoints that require 
    administrative privileges at the branch level.
    """
    # Enforce strict admin check based on database flag
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges are required for this action"
        )
    return current_user