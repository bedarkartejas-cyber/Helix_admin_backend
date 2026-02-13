from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from datetime import datetime, timezone
import logging

# Modular imports based on production project structure
from app.core.security import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, create_reset_token, verify_reset_token,
    parse_datetime
)
from app.db.supabase import (
    select_one, insert_one, update_one, create_user_with_branch
)
from app.schemas.schemas import (
    FirstUserSignup, InvitedUserSignup, LoginRequest, Token,
    ValidateInviteResponse, RefreshTokenRequest,
    SendOTPRequest, VerifyOTPRequest, VerifyOTPResponse,
    ForgotPasswordRequest, ResetPasswordRequest
)
from app.services.otp import otp_service

# Setup logging for production auditing
logger = logging.getLogger(__name__)

router = APIRouter()

# ============ AUTHENTICATION & SIGNUP ============

@router.post("/first-signup", response_model=Token)
async def first_user_signup(signup_data: FirstUserSignup):
    """Initial admin signup and branch creation - Requires OTP verification"""
    try:
        # Check if email is already in use
        existing = await select_one("users", {"email": signup_data.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Branch data extraction
        branch_data = {
            "branch_name": signup_data.store_name,
            "address": signup_data.store_address,
            "city": signup_data.city
        }
        
        # User data extraction using modern Pydantic v2 model_dump
        user_data = {
            "name": signup_data.name,
            "email": signup_data.email,
            "password_hash": get_password_hash(signup_data.password),
            "is_verified": False  # Admin must verify via OTP
        }
        
        # Atomic-like creation of branch and admin user
        user = await create_user_with_branch(user_data, branch_data)
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create account")
        
        # Return partial token state; full tokens issued only after OTP verification
        return {
            "access_token": "", 
            "refresh_token": "",
            "token_type": "bearer",
            "user": {**user, "requires_verification": True}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"First signup error: {str(e)}")
        raise HTTPException(status_code=500, detail="Signup process failed")

@router.post("/invite-signup", response_model=Token)
async def invited_user_signup(signup_data: InvitedUserSignup):
    """Signup for invited team members - Verified automatically via valid token"""
    try:
        # Validate the invitation token against unused database records
        invite = await select_one("invites", {"token": signup_data.token, "is_used": False})
        if not invite:
            raise HTTPException(status_code=400, detail="Invalid or already used invite token")
        
        # Verify invitation hasn't expired
        if datetime.now(timezone.utc) > parse_datetime(invite["expires_at"]):
            raise HTTPException(status_code=400, detail="Invite token has expired")

        user_data = {
            "name": signup_data.name,
            "email": invite["email"],
            "password_hash": get_password_hash(signup_data.password),
            "branch_id": invite["branch_id"],
            "is_admin": False,
            "is_active": True,
            "is_verified": True  # Verified via secure invite link
        }
        
        # Persist new user and invalidate the used invite token
        user = await insert_one("users", user_data)
        await update_one("invites", {"invite_id": invite["invite_id"]}, {"is_used": True})
        
        # Issue full tokens immediately for invited users
        return {
            "access_token": create_access_token({
                "user_id": user["user_id"], 
                "email": user["email"],
                "branch_id": user["branch_id"],
                "is_admin": user["is_admin"]
            }),
            "refresh_token": create_refresh_token({"user_id": user["user_id"]}),
            "token_type": "bearer",
            "user": user
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invite signup error: {str(e)}")
        raise HTTPException(status_code=500, detail="Invitation signup failed")

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Secure login with verification and activity guards"""
    user = await select_one("users", {"email": login_data.email, "is_active": True})
    
    # Credential verification
    if not user or not verify_password(login_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Block login if the account is not verified (requires OTP)
    if not user.get("is_verified", False):
        raise HTTPException(
            status_code=403, 
            detail={"message": "Verification required", "requires_verification": True, "email": user["email"]}
        )
    
    # Issue tokens with full user context payload
    return {
        "access_token": create_access_token({
            "user_id": user["user_id"], 
            "email": user["email"], 
            "branch_id": user["branch_id"], 
            "is_admin": user["is_admin"]
        }),
        "refresh_token": create_refresh_token({"user_id": user["user_id"]}),
        "token_type": "bearer",
        "user": user
    }

# ============ OTP & VERIFICATION ============

@router.post("/send-otp", response_model=VerifyOTPResponse)
async def send_otp(request: SendOTPRequest, background_tasks: BackgroundTasks):
    """Generates and dispatches OTP code via background task to prevent API blocking"""
    try:
        otp = await otp_service.generate_otp(request.email, request.purpose)
        # Offload email sending to background to speed up response time
        background_tasks.add_task(otp_service.send_otp_email, request.email, otp, request.purpose)
        return VerifyOTPResponse(success=True, message="OTP dispatched successfully")
    except Exception as e:
        return VerifyOTPResponse(success=False, message=str(e))

@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(request: VerifyOTPRequest):
    """Validates submitted OTP and updates corresponding database state"""
    result = await otp_service.verify_otp(request.email, request.otp, request.purpose)
    
    if result["success"]:
        if request.purpose == "verification":
            # Activate and verify the user account
            user = await select_one("users", {"email": request.email})
            await update_one("users", {"user_id": user["user_id"]}, {"is_verified": True})
            return VerifyOTPResponse(success=True, message="Account verified successfully", user=user)
        
        elif request.purpose == "password_reset":
            # Issue a short-lived reset token for the password update route
            return VerifyOTPResponse(success=True, reset_token=create_reset_token(request.email))
            
    return VerifyOTPResponse(**result)

# ============ PASSWORD RECOVERY ============

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """Updates password using a verified and unexpired reset token"""
    email = verify_reset_token(request.reset_token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired reset session")
    
    user = await select_one("users", {"email": email})
    # Update password with a fresh hash
    await update_one(
        "users", 
        {"user_id": user["user_id"]}, 
        {"password_hash": get_password_hash(request.new_password)}
    )
    return {"success": True, "message": "Password updated successfully"}