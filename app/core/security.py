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
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iss": "store-management-system"
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
    Decodes and validates a JWT. Corrected to handle Integer IDs from Supabase.
    """
    try:
        payload = jwt.decode(
            token, 
            settings.APP_SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Security Guard: Ensure the token type matches the intended use
        if payload.get("type") != expected_type:
            logger.warning(f"Invalid token type: expected {expected_type}, got {payload.get('type')}")
            return None

        # Fix: Explicitly cast IDs to string to prevent Pydantic validation errors
        # when the database/JWT contains integer IDs (e.g., 49, 40)
        user_id = str(payload.get("user_id")) if payload.get("user_id") is not None else None
        branch_id = str(payload.get("branch_id")) if payload.get("branch_id") is not None else None
        email = payload.get("email")
        is_admin = payload.get("is_admin", False)
        
        # Validate required claims for the TokenData schema
        if not all([user_id, email, branch_id]):
            logger.error(f"Missing required token claims. Got user_id={user_id}, email={email}, branch_id={branch_id}")
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
    """
    Validates password reset tokens and returns the associated email.
    """
    try:
        payload = jwt.decode(token, settings.APP_SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload.get("sub")
    except JWTError:
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Securely compares a plain password with its hashed version using bcrypt.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Generates a secure bcrypt hash with 12 rounds of salting.
    """
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def format_datetime(dt: datetime) -> str:
    """Standardizes datetime for storage in ISO 8601 format."""
    return dt.isoformat()

def parse_datetime(dt_str: str) -> datetime:
    """Parses ISO strings and ensures they are UTC-aware."""
    dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt