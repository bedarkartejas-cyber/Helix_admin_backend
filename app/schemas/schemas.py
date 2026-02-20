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
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class TokenData(BaseModel):
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

# ============ PROFESSIONAL FINANCIAL SCHEMAS (UPDATED) ============

class CardOfferBase(BaseModel):
    """Deep detail schema for Credit and Debit card offers."""
    bank_name: str
    bank_logo_url: Optional[str] = None
    card_network: str  # Visa, Mastercard, Rupay, Amex
    network_logo_url: Optional[str] = None
    offer_type: str = "Instant Discount" 
    discount_percent: float
    min_purchase_value: int = 0
    max_discount_amount: int = 0
    offer_description: Optional[str] = None
    tnc_link: Optional[str] = None

class EMIPlan(BaseModel):
    """
    Detailed EMI breakdown. 
    Fields like monthly_installment and total_repayment are Optional 
    because the Backend calculates them automatically based on Product Price.
    """
    institute_name: str
    institute_logo_url: Optional[str] = None
    tenure_months: int
    interest_rate_pa: float = 0.0
    is_no_cost_emi: bool = False
    processing_fee: Optional[int] = 0
    min_purchase_amount: Optional[int] = 0
    # Calculations are handled by the server
    monthly_installment: Optional[int] = None 
    total_interest_paid: Optional[int] = None
    total_repayment_amount: Optional[int] = None
    offer_text: Optional[str] = None

class UPIOffer(BaseModel):
    """Deep detail schema for Digital Wallet/UPI discounts."""
    platform_name: str 
    platform_logo_url: Optional[str] = None
    offer_type: str = "Instant Discount"
    discount_amount: float
    min_purchase_value: int = 0
    is_flat_discount: bool = True
    offer_description: Optional[str] = None
    max_cashback: Optional[int] = None

# ============ PRODUCT & INVENTORY SCHEMAS ============

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2)
    images: Optional[str] = None   
    url_link: Optional[str] = None 
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
    """The 'Master' response containing all deep financial data."""
    credit_card_offers: List[CardOfferBase] = []
    debit_card_offers: List[CardOfferBase] = []
    emi_plans: List[EMIPlan] = []
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