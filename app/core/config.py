from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import logging
from pathlib import Path

# Setup logging for production visibility
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """
    Production-grade configuration management.
    Ensures all sensitive keys are loaded from environment variables and validates types.
    """
    
    # --- Supabase Configuration ---
    # These must be provided in your .env for the app to start
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_JWT_SECRET: str
    
    # --- Application Security ---
    APP_SECRET_KEY: str  # Critical for signing JWT tokens
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    INVITE_TOKEN_EXPIRE_HOURS: int = 48
    
    # --- OTP & Verification Settings ---
    OTP_EXPIRE_MINUTES: int = 10
    OTP_LENGTH: int = 6
    OTP_MAX_ATTEMPTS: int = 3
    OTP_COOLDOWN_MINUTES: int = 5
    
    # --- Frontend & CORS Integration ---
    # Setting CORS_ORIGINS to ["*"] allows any frontend (React, Vue, etc.) 
    # to communicate with this API
    FRONTEND_URL: str = "http://localhost:8000" 
    CORS_ORIGINS: List[str] = ["*"] 
    
    # --- Production Email Service (SMTP) ---
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: int = 587 
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    
    # --- Pydantic Settings Configuration ---
    # This automatically loads variables from a .env file if it exists
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore" # Prevents errors if extra variables are in .env
    )

# Global settings instance to be imported by other modules
try:
    settings = Settings()
    logger.info("✅ Configuration loaded successfully.")
except Exception as e:
    logger.error(f"❌ Failed to load configuration: {str(e)}")
    raise