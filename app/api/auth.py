# from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
# from datetime import datetime, timezone
# import logging

# # Modular imports based on production project structure
# from app.core.security import (
#     get_password_hash, verify_password, create_access_token,
#     create_refresh_token, create_reset_token, verify_reset_token,
#     parse_datetime
# )
# from app.db.supabase import (
#     select_one, insert_one, update_one, create_user_with_branch
# )
# from app.schemas.schemas import (
#     FirstUserSignup, InvitedUserSignup, LoginRequest, Token,
#     SendOTPRequest, VerifyOTPRequest, VerifyOTPResponse,
#     ForgotPasswordRequest, ResetPasswordRequest
# )
# from app.services.otp import otp_service

# # Setup logging for production auditing
# logger = logging.getLogger(__name__)

# router = APIRouter()

# # ============ AUTHENTICATION & SIGNUP ============

# @router.post("/first-signup", response_model=Token)
# async def first_user_signup(signup_data: FirstUserSignup):
#     """Initial admin signup and branch creation - Requires OTP verification"""
#     try:
#         existing = await select_one("users", {"email": signup_data.email})
#         if existing:
#             raise HTTPException(status_code=400, detail="Email already registered")
        
#         branch_data = {
#             "branch_name": signup_data.store_name,
#             "address": signup_data.store_address,
#             "city": signup_data.city
#         }
        
#         user_data = {
#             "name": signup_data.name,
#             "email": signup_data.email,
#             "password_hash": get_password_hash(signup_data.password),
#             "is_verified": False  # Admin must verify via OTP
#         }
        
#         user = await create_user_with_branch(user_data, branch_data)
#         if not user:
#             raise HTTPException(status_code=500, detail="Failed to create account")
        
#         return {
#             "access_token": "", 
#             "refresh_token": "",
#             "token_type": "bearer",
#             "user": {**user, "requires_verification": True}
#         }
#     except Exception as e:
#         logger.error(f"First signup error: {str(e)}")
#         raise HTTPException(status_code=500, detail="Signup failed")

# @router.post("/invite-signup", response_model=Token)
# async def invited_user_signup(signup_data: InvitedUserSignup):
#     """Signup for invited team members - Verified automatically via valid token"""
#     try:
#         invite = await select_one("invites", {"token": signup_data.token, "is_used": False})
#         if not invite:
#             raise HTTPException(status_code=400, detail="Invalid or used invite token")
        
#         if datetime.now(timezone.utc) > parse_datetime(invite["expires_at"]):
#             raise HTTPException(status_code=400, detail="Invite token has expired")

#         user_data = {
#             "name": signup_data.name,
#             "email": invite["email"],
#             "password_hash": get_password_hash(signup_data.password),
#             "branch_id": invite["branch_id"],
#             "is_admin": False,
#             "is_active": True,
#             "is_verified": True 
#         }
        
#         user = await insert_one("users", user_data)
#         await update_one("invites", {"invite_id": invite["invite_id"]}, {"is_used": True})
        
#         # Issue tokens with IDs cast to strings for schema compatibility
#         return {
#             "access_token": create_access_token({
#                 "user_id": str(user["user_id"]), 
#                 "branch_id": str(user["branch_id"]),
#                 "email": user["email"]
#             }),
#             "refresh_token": create_refresh_token({"user_id": str(user["user_id"])}),
#             "token_type": "bearer",
#             "user": user
#         }
#     except Exception as e:
#         logger.error(f"Invite signup error: {str(e)}")
#         raise HTTPException(status_code=500, detail="Signup failed")

# @router.post("/login", response_model=Token)
# async def login(login_data: LoginRequest):
#     """Secure login with verification guard"""
#     user = await select_one("users", {"email": login_data.email, "is_active": True})
    
#     if not user or not verify_password(login_data.password, user["password_hash"]):
#         raise HTTPException(status_code=401, detail="Invalid credentials")
    
#     if not user.get("is_verified", False):
#         raise HTTPException(
#             status_code=403, 
#             detail={"message": "Verification required", "requires_verification": True, "email": user["email"]}
#         )
    
#     return {
#         "access_token": create_access_token({
#             "user_id": str(user["user_id"]), 
#             "email": user["email"], 
#             "branch_id": str(user["branch_id"]), 
#             "is_admin": user["is_admin"]
#         }),
#         "refresh_token": create_refresh_token({"user_id": str(user["user_id"])}),
#         "token_type": "bearer",
#         "user": user
#     }

# # ============ PASSWORD RECOVERY (FORGOT PASSWORD) ============

# @router.post("/forgot-password")
# async def forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks):
#     """
#     Initiates the password reset flow.
#     Generates an OTP and sends it via background email task.
#     """
#     user = await select_one("users", {"email": request.email.lower(), "is_active": True})
    
#     # Security: Always return success to prevent email discovery
#     if not user:
#         logger.warning(f"Password reset attempted for non-existent email: {request.email}")
#         return {"success": True, "message": "If this email is registered, a reset code has been sent."}

#     try:
#         otp = await otp_service.generate_otp(request.email, purpose="password_reset")
        
#         background_tasks.add_task(
#             otp_service.send_otp_email, 
#             request.email, 
#             otp, 
#             "password_reset"
#         )
        
#         return {"success": True, "message": "Reset code sent to your email."}
#     except Exception as e:
#         logger.error(f"Forgot password error: {str(e)}")
#         raise HTTPException(status_code=500, detail="Failed to process reset request")

# @router.post("/reset-password")
# async def reset_password(request: ResetPasswordRequest):
#     """Updates password using a verified reset token session"""
#     email = verify_reset_token(request.reset_token)
#     if not email:
#         raise HTTPException(status_code=400, detail="Invalid or expired reset session")
    
#     user = await select_one("users", {"email": email})
#     if not user:
#         raise HTTPException(status_code=404, detail="User no longer exists")

#     await update_one(
#         "users", 
#         {"user_id": user["user_id"]}, 
#         {"password_hash": get_password_hash(request.new_password)}
#     )
#     return {"success": True, "message": "Password updated successfully"}

# # ============ OTP & VERIFICATION ============

# @router.post("/send-otp", response_model=VerifyOTPResponse)
# async def send_otp(request: SendOTPRequest, background_tasks: BackgroundTasks):
#     """Dispatches OTP code via background task"""
#     try:
#         otp = await otp_service.generate_otp(request.email, request.purpose)
#         background_tasks.add_task(otp_service.send_otp_email, request.email, otp, request.purpose)
#         return VerifyOTPResponse(success=True, message="OTP sent successfully")
#     except Exception as e:
#         return VerifyOTPResponse(success=False, message=str(e))

# @router.post("/verify-otp", response_model=VerifyOTPResponse)
# async def verify_otp(request: VerifyOTPRequest):
#     """Validates OTP and updates verification status in database"""
#     result = await otp_service.verify_otp(request.email, request.otp, request.purpose)
    
#     if result["success"]:
#         if request.purpose == "verification":
#             user = await select_one("users", {"email": request.email})
#             await update_one("users", {"user_id": user["user_id"]}, {"is_verified": True})
#             return VerifyOTPResponse(success=True, message="Account verified successfully", user=user)
        
#         elif request.purpose == "password_reset":
#             # UPDATED: Added required 'message' field to prevent Pydantic validation error
#             return VerifyOTPResponse(
#                 success=True, 
#                 message="Code verified successfully. Please set your new password.",
#                 reset_token=create_reset_token(request.email)
#             )
            
#     # Fallback to the result dictionary (ensures 'message' is present from otp_service.verify_otp)
#     return VerifyOTPResponse(**result)










































from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from datetime import datetime, timezone, timedelta
from typing import Any
import logging

# Modular imports based on production project structure
from app.core.security import (
    get_password_hash, verify_password, create_access_token,
    create_refresh_token, create_reset_token, verify_reset_token,
    parse_datetime, create_invite_token
)
from app.db.supabase import (
    select_one, insert_one, update_one, create_user_with_branch
)
from app.schemas.schemas import (
    FirstUserSignup, InvitedUserSignup, LoginRequest, Token,
    SendOTPRequest, VerifyOTPRequest, VerifyOTPResponse,
    ForgotPasswordRequest, ResetPasswordRequest, SendInviteRequest,
    ValidateInviteResponse, TokenData
)
from app.services.otp import otp_service
from app.dependencies import get_current_user
from app.core.config import settings

# Setup logging for production auditing
logger = logging.getLogger(__name__)

router = APIRouter()

# ============ HELPER: SAFE DATA EXTRACTION ============

def safe_get(obj: Any, key: str):
    """
    Safely extracts a value whether the object is a dict or a Pydantic model.
    Prevents '500 Internal Server Error' during database-to-schema mapping.
    """
    if obj is None:
        return None
    return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)

def get_session_data(current_user: Any):
    """Safely extracts IDs and roles from current_user session."""
    return {
        "uid": safe_get(current_user, "user_id"),
        "bid": safe_get(current_user, "branch_id"),
        "email": safe_get(current_user, "email"),
        "is_admin": safe_get(current_user, "is_admin") or False
    }

# ============ AUTHENTICATION & SIGNUP ============

@router.post("/first-signup", response_model=Token)
async def first_user_signup(signup_data: FirstUserSignup):
    """Initial admin signup and branch creation."""
    try:
        existing = await select_one("users", {"email": signup_data.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        branch_data = {
            "branch_name": signup_data.store_name,
            "address": signup_data.store_address,
            "city": signup_data.city
        }
        
        user_data = {
            "name": signup_data.name,
            "email": signup_data.email,
            "password_hash": get_password_hash(signup_data.password),
            "is_verified": False,
            "is_admin": True # First user is always admin
        }
        
        user = await create_user_with_branch(user_data, branch_data)
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create account")
        
        return {
            "access_token": "", 
            "refresh_token": "",
            "token_type": "bearer",
            "user": {**user, "requires_verification": True}
        }
    except Exception as e:
        logger.error(f"First signup error: {str(e)}")
        raise HTTPException(status_code=500, detail="Signup failed")

@router.get("/invite-details/{token}", response_model=ValidateInviteResponse)
async def get_invite_details(token: str):
    """Fetch store and inviter details."""
    try:
        invite = await select_one("invites", {"token": token, "is_used": False})
        if not invite:
            raise HTTPException(status_code=404, detail="Invite link is invalid or has expired")

        branch = await select_one("branches", {"branch_id": safe_get(invite, "branch_id")})
        admin = await select_one("users", {"user_id": safe_get(invite, "created_by")})

        return ValidateInviteResponse(
            valid=True,
            email=safe_get(invite, "email"),
            branch_name=safe_get(branch, "branch_name"),
            invited_by=safe_get(admin, "name")
        )
    except Exception as e:
        logger.error(f"Invite details 500 error: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not retrieve invitation details")

@router.post("/invite-signup", response_model=Token)
async def invited_user_signup(signup_data: InvitedUserSignup):
    """Signup for invited team members - Ensures Staff Dashboard redirection."""
    try:
        invite = await select_one("invites", {"token": signup_data.token, "is_used": False})
        if not invite:
            raise HTTPException(status_code=400, detail="Invalid or used invite token")
        
        if datetime.now(timezone.utc) > parse_datetime(safe_get(invite, "expires_at")):
            raise HTTPException(status_code=400, detail="Invite token has expired")

        user_data = {
            "name": signup_data.name,
            "email": safe_get(invite, "email"),
            "password_hash": get_password_hash(signup_data.password),
            "branch_id": int(safe_get(invite, "branch_id")),
            "is_admin": False, # Forced staff role
            "is_active": True,
            "is_verified": True 
        }
        
        user = await insert_one("users", user_data)
        if not user:
            raise HTTPException(status_code=500, detail="Failed to create user")
            
        await update_one("invites", {"invite_id": safe_get(invite, "invite_id")}, {"is_used": True})
        
        return {
            "access_token": create_access_token({
                "user_id": str(safe_get(user, "user_id")), 
                "branch_id": str(safe_get(user, "branch_id")),
                "email": safe_get(user, "email"),
                "is_admin": False
            }),
            "refresh_token": create_refresh_token({"user_id": str(safe_get(user, "user_id"))}),
            "token_type": "bearer",
            "user": user
        }
    except Exception as e:
        logger.error(f"Invite signup error: {str(e)}")
        raise HTTPException(status_code=500, detail="Signup failed")

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest):
    """Secure login with verification guard."""
    user = await select_one("users", {"email": login_data.email, "is_active": True})
    
    if not user or not verify_password(login_data.password, safe_get(user, "password_hash")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not safe_get(user, "is_verified"):
        raise HTTPException(
            status_code=403, 
            detail={"message": "Verification required", "requires_verification": True, "email": safe_get(user, "email")}
        )
    
    return {
        "access_token": create_access_token({
            "user_id": str(safe_get(user, "user_id")), 
            "email": safe_get(user, "email"), 
            "branch_id": str(safe_get(user, "branch_id")), 
            "is_admin": safe_get(user, "is_admin")
        }),
        "refresh_token": create_refresh_token({"user_id": str(safe_get(user, "user_id"))}),
        "token_type": "bearer",
        "user": user
    }

# ============ USER INVITATION SYSTEM ============

@router.post("/send-invite")
async def send_invite(
    request: SendInviteRequest, 
    background_tasks: BackgroundTasks, 
    current_user: Any = Depends(get_current_user)
):
    """Generates an invite link for staff if not already registered."""
    session = get_session_data(current_user)
    
    if not session["is_admin"]:
        raise HTTPException(status_code=403, detail="Only admins can invite new staff members.")

    email_to_invite = request.email.lower().strip()

    # --- SECURITY CHECK: Block inviting self or existing users ---
    if email_to_invite == session["email"]:
        raise HTTPException(
            status_code=400, 
            detail="You cannot invite your own email address."
        )

    existing_user = await select_one("users", {"email": email_to_invite})
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail=f"The email {email_to_invite} is already registered as a user."
        )

    try:
        token = create_invite_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        invite_data = {
            "email": email_to_invite,
            "token": token,
            "branch_id": int(session["bid"]), 
            "created_by": int(session["uid"]),
            "expires_at": expires_at.isoformat(),
            "is_used": False
        }
        
        invite = await insert_one("invites", invite_data)
        if not invite:
            raise HTTPException(status_code=500, detail="Database insertion failed.")
        
        invite_url = f"{settings.FRONTEND_URL}/signup-invite?token={token}"
        
        background_tasks.add_task(
            otp_service.send_invitation_email, 
            email_to_invite, 
            invite_url
        )
        
        return {
            "success": True, 
            "message": f"Invitation link generated and sent to {email_to_invite}"
        }
    except Exception as e:
        logger.error(f"Invite error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ============ PASSWORD RECOVERY ============

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    user = await select_one("users", {"email": request.email.lower(), "is_active": True})
    if not user:
        return {"success": True, "message": "If this email is registered, a reset code has been sent."}

    try:
        otp = await otp_service.generate_otp(request.email, purpose="password_reset")
        background_tasks.add_task(otp_service.send_otp_email, request.email, otp, "password_reset")
        return {"success": True, "message": "Reset code sent to your email."}
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process reset request")

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    email = verify_reset_token(request.reset_token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired reset session")
    
    user = await select_one("users", {"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User no longer exists")

    await update_one(
        "users", 
        {"user_id": safe_get(user, "user_id")}, 
        {"password_hash": get_password_hash(request.new_password)}
    )
    return {"success": True, "message": "Password updated successfully"}

# ============ OTP & VERIFICATION ============

@router.post("/send-otp", response_model=VerifyOTPResponse)
async def send_otp(request: SendOTPRequest, background_tasks: BackgroundTasks):
    try:
        otp = await otp_service.generate_otp(request.email, request.purpose)
        background_tasks.add_task(otp_service.send_otp_email, request.email, otp, request.purpose)
        return VerifyOTPResponse(success=True, message="OTP sent successfully")
    except Exception as e:
        return VerifyOTPResponse(success=False, message=str(e))

@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(request: VerifyOTPRequest):
    result = await otp_service.verify_otp(request.email, request.otp, request.purpose)
    
    if result["success"]:
        if request.purpose == "verification":
            user = await select_one("users", {"email": request.email})
            await update_one("users", {"user_id": safe_get(user, "user_id")}, {"is_verified": True})
            return VerifyOTPResponse(success=True, message="Account verified successfully", user=user)
        
        elif request.purpose == "password_reset":
            return VerifyOTPResponse(
                success=True, 
                message="Code verified. Set your new password.",
                reset_token=create_reset_token(request.email)
            )
            
    return VerifyOTPResponse(**result)
