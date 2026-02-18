from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any, Union

# ============ SHARED UTILITIES ============

def coerce_to_str(v: Any) -> str:
    """Helper to safely convert database IDs (int) to strings."""
    if v is None:
        return ""
    return str(v)

# ============ AUTH & TOKEN SCHEMAS ============

class Token(BaseModel):
    """Standard Bearer token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class TokenData(BaseModel):
    """Internal helper for JWT payload data."""
    user_id: str
    email: str
    branch_id: str
    is_admin: bool = False

    @field_validator('user_id', 'branch_id', mode='before')
    @classmethod
    def ids_to_str(cls, v: Any) -> str:
        return coerce_to_str(v)

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# ============ OTP & VERIFICATION SCHEMAS ============

class SendOTPRequest(BaseModel):
    email: EmailStr
    purpose: str = "verification"
    
    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower().strip()

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    purpose: str = "verification"
    
    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower().strip()

class VerifyOTPResponse(BaseModel):
    success: bool
    message: str
    attempts_remaining: Optional[int] = None
    cooldown_until: Optional[str] = None
    user: Optional[Dict[str, Any]] = None
    reset_token: Optional[str] = None

# ============ USER & PROFILE SCHEMAS ============

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None

class UserResponse(BaseModel):
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
    def ids_to_str(cls, v: Any) -> str:
        return coerce_to_str(v)

class UserProfileResponse(BaseModel):
    user: UserResponse
    branch: Dict[str, Any]

# ============ PRODUCT OFFER SCHEMAS ============

class BankOffer(BaseModel):
    """Schema for credit/debit card bank discounts."""
    bank_name: str
    card_type: str  # e.g., Credit Card, Debit Card
    discount_percent: float
    max_discount_amount: float
    min_purchase_amount: float

class EMIOffer(BaseModel):
    """Schema for bank EMI plans."""
    bank_name: str
    tenure_months: int
    interest_rate: float  # 0 for No Cost EMI
    min_purchase_amount: float

class UPIOffer(BaseModel):
    """Schema for digital wallet/UPI discounts."""
    platform_name: str  # GPay, PhonePe, UPI
    discount_amount: float
    is_flat_discount: bool = True

# ============ PRODUCT & INVENTORY SCHEMAS ============

class ProductCreate(BaseModel):
    """Stores product data with dedicated image and catalog links."""
    name: str = Field(..., min_length=2)
    images: Optional[str] = None   # URL to product image
    url_link: Optional[str] = None # URL to actual external product/laptop page
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)
    category: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    images: Optional[str] = None
    url_link: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    category: Optional[str] = None

class ProductResponse(BaseModel):
    """Basic product response including catalog link."""
    product_id: str
    name: str
    images: Optional[str] = None
    url_link: Optional[str] = None
    price: float
    stock_quantity: int
    category: Optional[str] = None
    branch_id: str
    created_at: str

    @field_validator('product_id', 'branch_id', mode='before')
    @classmethod
    def ids_to_str(cls, v: Any) -> str:
        return coerce_to_str(v)

class ProductDetailResponse(ProductResponse):
    """Aggregated laptop details with all offer types."""
    bank_offers: List[BankOffer] = []
    emi_offers: List[EMIOffer] = []
    upi_offers: List[UPIOffer] = []

# ============ SIGNUP & LOGIN SCHEMAS ============

class FirstUserSignup(BaseModel):
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
        return v.lower().strip()

    @model_validator(mode='after')
    def passwords_match(self) -> 'FirstUserSignup':
        if self.password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self

class InvitedUserSignup(BaseModel):
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
    email: EmailStr
    password: str
    
    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower().strip()

# ============ INVITE SCHEMAS ============

class SendInviteRequest(BaseModel):
    email: EmailStr
    
    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower().strip()

class ValidateInviteResponse(BaseModel):
    valid: bool
    email: str
    branch_name: str
    invited_by: str

# ============ BRANCH & DASHBOARD SCHEMAS ============

class BranchUpdate(BaseModel):
    """RESTORED: Missing class required by branches.py logic."""
    branch_name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None

class BranchResponse(BaseModel):
    branch_id: str
    branch_name: str
    address: str
    city: str
    created_at: str

    @field_validator('branch_id', mode='before')
    @classmethod
    def ids_to_str(cls, v: Any) -> str:
        return coerce_to_str(v)

class DashboardResponse(BaseModel):
    user: UserResponse
    branch: BranchResponse
    total_users: int
    recent_invites: List[Dict[str, Any]]
    can_manage_users: bool = True

# ============ PASSWORD RESET SCHEMAS ============

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    
    @field_validator('email')
    @classmethod
    def email_lowercase(cls, v: str) -> str:
        return v.lower().strip()

class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str = Field(..., min_length=8)

    @model_validator(mode='after')
    def passwords_match(self) -> 'ResetPasswordRequest':
        if self.new_password != self.confirm_password:
            raise ValueError('Passwords do not match')
        return self