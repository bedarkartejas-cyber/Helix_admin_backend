from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any, Union

# ============ AUTH & TOKEN SCHEMAS ============

class Token(BaseModel):
    """Standard Bearer token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class TokenData(BaseModel):
    """Internal helper for JWT payload data. Corrected to handle Int/Str IDs."""
    user_id: str
    email: str
    branch_id: str
    is_admin: bool = False

    @field_validator('user_id', 'branch_id', mode='before')
    @classmethod
    def convert_ids_to_str(cls, v: Any) -> str:
        """Coerces integer IDs from Supabase into strings to satisfy schema."""
        return str(v) if v is not None else v

class RefreshTokenRequest(BaseModel):
    """Request model for refreshing expired access tokens."""
    refresh_token: str

# ============ OTP & VERIFICATION SCHEMAS ============

class SendOTPRequest(BaseModel):
    """Request to generate and dispatch a new OTP."""
    email: EmailStr
    purpose: str = "verification"  # Options: verification, password_reset
    
    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower()

class VerifyOTPRequest(BaseModel):
    """Request to validate a user-submitted OTP code."""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    purpose: str = "verification"
    
    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower()

class VerifyOTPResponse(BaseModel):
    """Response containing verification results or reset tokens."""
    success: bool
    message: str
    attempts_remaining: Optional[int] = None
    cooldown_until: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    reset_token: Optional[str] = None

# ============ USER & PROFILE SCHEMAS ============

class UserUpdate(BaseModel):
    """Schema for partial profile updates."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None

class UserResponse(BaseModel):
    """Safe public representation of a user record."""
    user_id: str
    name: str
    email: str
    branch_id: str
    is_admin: bool
    is_active: bool
    is_verified: bool
    created_at: str

    @field_validator('user_id', 'branch_id', mode='before')
    @classmethod
    def convert_ids_to_str(cls, v: Any) -> str:
        return str(v)

class UserProfileResponse(BaseModel):
    """Comprehensive profile view including branch context."""
    user: UserResponse
    branch: Dict[str, Any]

# ============ SIGNUP & LOGIN SCHEMAS ============

class FirstUserSignup(BaseModel):
    """Primary signup for store owners/admins."""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)
    store_name: str = Field(..., min_length=2, max_length=100)
    store_address: str
    city: str
    
    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower()

    @model_validator(mode='after')
    def passwords_match(self) -> 'FirstUserSignup':
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self

class InvitedUserSignup(BaseModel):
    """Signup for staff members invited to an existing branch."""
    token: str
    name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @model_validator(mode='after')
    def passwords_match(self) -> 'InvitedUserSignup':
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self

class LoginRequest(BaseModel):
    """Standard login credentials."""
    email: EmailStr
    password: str
    
    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower()

# ============ INVITE SCHEMAS ============

class SendInviteRequest(BaseModel):
    """Request to send a new branch invitation."""
    email: EmailStr
    
    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower()

class InviteResponse(BaseModel):
    """Response after successfully creating an invitation."""
    invite_id: str
    email: str
    token: str
    expires_at: str
    status: str = "sent"
    invite_url: str

class ValidateInviteResponse(BaseModel):
    """Response used when checking an invitation link."""
    valid: bool
    email: str
    branch_name: str
    invited_by: str

# ============ PRODUCT SCHEMAS ============

class ProductCreate(BaseModel):
    """Schema for adding new inventory items."""
    name: str = Field(..., min_length=2)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)
    category: Optional[str] = None

class ProductUpdate(BaseModel):
    """Schema for partial inventory updates."""
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    category: Optional[str] = None

class ProductResponse(BaseModel):
    """Inventory item details for API output."""
    product_id: str
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int
    category: Optional[str] = None
    branch_id: str
    created_at: str

    @field_validator('product_id', 'branch_id', mode='before')
    @classmethod
    def convert_ids_to_str(cls, v: Any) -> str:
        return str(v)

# ============ BRANCH & DASHBOARD SCHEMAS ============

class BranchUpdate(BaseModel):
    """Administrative updates to store settings."""
    branch_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None

class BranchResponse(BaseModel):
    """Store profile details."""
    branch_id: str
    branch_name: str
    address: str
    city: str
    created_at: str

    @field_validator('branch_id', mode='before')
    @classmethod
    def convert_ids_to_str(cls, v: Any) -> str:
        return str(v)

class DashboardResponse(BaseModel):
    """Aggregated data for the main management view."""
    user: UserResponse
    branch: BranchResponse
    total_users: int
    recent_invites: List[Dict[str, Any]]
    can_manage_users: bool = True

# ============ PASSWORD RESET SCHEMAS ============

class ForgotPasswordRequest(BaseModel):
    """Initial request for password reset."""
    email: EmailStr
    
    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower()

class ResetPasswordRequest(BaseModel):
    """Final step for password reset using the JWT token."""
    reset_token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @model_validator(mode='after')
    def passwords_match(self) -> 'ResetPasswordRequest':
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self