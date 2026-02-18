from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import secrets
import string
import bcrypt
import logging

# Centralized imports from your modular structure
from app.core.config import settings
from app.schemas.schemas import TokenData

# Setup logging for security events
logger = logging.getLogger(__name__)

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict) -> str:
    """
    Generates a secure, short-lived JWT access token for API authentication.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Ensure is_admin is boolean and present
    is_admin = to_encode.get("is_admin", False)
    
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iss": "store-management-system",
        "is_admin": bool(is_admin)
    })
    return jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict) -> str:
    """
    Generates a long-lived JWT refresh token to renew access without re-login.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iss": "store-management-system"
    })
    return jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=settings.ALGORITHM)

def create_invite_token() -> str:
    """
    Creates a cryptographically secure 32-character random string for invites.
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

def create_reset_token(email: str) -> str:
    """
    Creates a highly restricted JWT specifically for password reset flows.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=2)
    to_encode = {
        "sub": email,
        "exp": expire,
        "type": "password_reset",
        "iss": "store-management-system"
    }
    return jwt.encode(to_encode, settings.APP_SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str, expected_type: str = "access") -> Optional[TokenData]:
    """
    Decodes and validates a JWT. Handles Integer IDs and Role extraction.
    """
    try:
        payload = jwt.decode(
            token, 
            settings.APP_SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # 1. Type Guard: Prevents using a reset token as an access token
        if payload.get("type") != expected_type:
            logger.warning(f"Invalid token type: expected {expected_type}, got {payload.get('type')}")
            return None

        # 2. Extract and Normalize Data
        # We cast IDs to strings to match Pydantic schemas, even if Supabase returns Ints
        user_id = str(payload.get("user_id")) if payload.get("user_id") is not None else None
        branch_id = str(payload.get("branch_id")) if payload.get("branch_id") is not None else None
        email = payload.get("email")
        
        # Role Extraction: Default to False for safety
        is_admin = payload.get("is_admin")
        if isinstance(is_admin, str):
            is_admin = is_admin.lower() == 'true'
        else:
            is_admin = bool(is_admin)

        # 3. Validation
        if not all([user_id, email, branch_id]):
            logger.error(f"Missing required token claims for user {email}")
            return None
            
        return TokenData(
            user_id=user_id,
            email=email,
            branch_id=branch_id,
            is_admin=is_admin
        )
    except JWTError as e:
        logger.debug(f"JWT Verification failed: {str(e)}")
        return None

def verify_reset_token(token: str) -> Optional[str]:
    """Validates password reset tokens and returns the email."""
    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Securely compares passwords using bcrypt."""
    try:
        # Standard bcrypt check
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        # Fallback to passlib if hash format varies
        return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generates a secure bcrypt hash with 12 rounds."""
    password_bytes = password.encode('utf-8')
    # Bcrypt has a 72-byte limit
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def format_datetime(dt: datetime) -> str:
    """Standardizes datetime for ISO 8601 storage."""
    return dt.isoformat()

def parse_datetime(dt_str: str) -> datetime:
    """Parses ISO strings and ensures they are UTC-aware."""
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt