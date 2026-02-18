from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Any

# Updated imports to reflect modular structure
from app.core.security import verify_token
from app.db.supabase import select_one

# Initializing security scheme for Bearer token injection
security = HTTPBearer(auto_error=False)

def safe_get(obj: Any, key: str):
    """Safely extracts a value whether the object is a dict or a Pydantic/Class object."""
    if obj is None:
        return None
    return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)

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
            detail="No authorization header found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 1. Verify token using centralized security logic
    # This checks expiration, signature, and required claims (user_id, email, etc.)
    token_data = verify_token(credentials.credentials)
    
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid, expired, or malformed",
        )
    
    # 2. Fetch user from the database
    # We query by user_id and ensure the user is active
    user = await select_one("users", {"user_id": token_data.user_id, "is_active": True})
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists or is inactive",
        )
    
    # Return as dict to ensure compatibility with existing logic
    return user if isinstance(user, dict) else user.dict()

async def get_current_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to restrict access to endpoints that require 
    administrative privileges.
    """
    # 3. Enforce strict admin check
    # Uses safe_get to handle potential object/dict mismatch
    is_admin = safe_get(current_user, "is_admin")
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin privileges required"
        )
        
    return current_user