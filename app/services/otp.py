import secrets
import string
import smtplib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Modular imports based on the production file structure
from app.db.supabase import insert_one, select_one, update_one, select_all
from app.core.config import settings

logger = logging.getLogger(__name__)

class OTPService:
    def __init__(self):
        """Initializes the service with the database table name."""
        self.otp_table = "otp_verifications"
    
    async def generate_otp(self, email: str, purpose: str = "verification") -> str:
        """
        Generates and stores an OTP code. 
        Reliability Fix: Reuses existing code ONLY if it has > 2 mins left.
        """
        email = email.lower().strip()
        
        # 1. Check for a recent valid OTP to prevent redundant emails
        existing_otp = await select_one(
            self.otp_table,
            {
                "email": email,
                "purpose": purpose,
                "is_used": False,
                "is_expired": False
            }
        )
        
        if existing_otp:
            # Parse expiry and ensure it's UTC aware
            expires_at = datetime.fromisoformat(existing_otp["expires_at"].replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            
            time_remaining = (expires_at - current_time).total_seconds() / 60
            
            # If the code is still valid for more than 2 minutes, reuse it
            if time_remaining > 2:
                logger.info(f"✅ Reusing valid OTP for {email}. Expires in {time_remaining:.1f}m")
                return existing_otp["otp"]
            else:
                # If it's close to expiring, kill it now so we can generate a fresh one
                await update_one(self.otp_table, {"otp_id": existing_otp["otp_id"]}, {"is_expired": True})
        
        # 2. Security Check: Verify user is not currently in a lockout/cooldown
        cooldown_data = await self._check_cooldown(email)
        if cooldown_data["in_cooldown"]:
            raise Exception(f"Rate limit exceeded. Please wait {settings.OTP_COOLDOWN_MINUTES} minutes.")
        
        # 3. Cleanup: Expire any old, unused codes for this email to prevent conflicts
        await self._cleanup_old_otps(email)
        
        # 4. Generate a Fresh 6-Digit Code
        otp = ''.join(secrets.choice(string.digits) for _ in range(settings.OTP_LENGTH))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        
        otp_record = {
            "email": email,
            "otp": otp,
            "purpose": purpose,
            "expires_at": expires_at.isoformat(),
            "attempts": 0,
            "is_used": False,
            "is_expired": False,
            "is_locked": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = await insert_one(self.otp_table, otp_record)
        if not result:
            raise Exception("Critical: Failed to persist OTP to database.")
        
        logger.info(f"✨ Fresh OTP generated for {email}: {otp} (Purpose: {purpose})")
        return otp

    async def send_otp_email(self, email: str, otp: str, purpose: str = "verification") -> bool:
        """
        Dispatches the OTP via SMTP using a secure HTML template.
        Integrated with settings for Gmail/SMTP delivery.
        """
        # Always log to terminal for development/debugging
        logger.info("=" * 60)
        logger.info(f"📧 [OTP DELIVERY] To: {email} | Code: {otp}")
        logger.info(f"Purpose: {purpose} | Expires in: {settings.OTP_EXPIRE_MINUTES}m")
        logger.info("=" * 60)

        if not all([settings.SMTP_SERVER, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
            logger.warning(f"⚠️ SMTP not configured. OTP will ONLY appear in console.")
            return True

        subject = "🔐 Account Verification" if purpose == "verification" else "🔑 Password Reset Code"
        header = "Verify Your Account" if purpose == "verification" else "Reset Your Password"

        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', sans-serif; background-color: #f3f4f6; padding: 20px;">
            <div style="max-width: 450px; margin: auto; background: white; padding: 40px; border-radius: 12px; border: 1px solid #e5e7eb;">
                <h2 style="color: #4F46E5; text-align: center; margin-bottom: 24px;">{header}</h2>
                <p style="color: #374151; font-size: 16px; text-align: center; line-height: 1.5;">
                    Please use the following code to complete your request. It will expire in <strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong>.
                </p>
                <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0; border: 1px dashed #4F46E5;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 10px; color: #111827;">{otp}</span>
                </div>
                <p style="color: #9ca3af; font-size: 12px; text-align: center;">
                    If you did not request this code, please ignore this email safely.
                </p>
            </div>
        </body>
        </html>
        """

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.EMAIL_FROM or settings.SMTP_USERNAME
            msg["To"] = email
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"✅ OTP email successfully dispatched to {email}")
            return True
        except Exception as e:
            logger.error(f"❌ SMTP Error sending OTP: {str(e)}")
            return False

    async def verify_otp(self, email: str, otp: str, purpose: str = "verification") -> Dict:
        """Validates the OTP and manages attempt counts/lockouts."""
        try:
            email = email.lower().strip()
            otp_record = await select_one(
                self.otp_table, 
                {"email": email, "purpose": purpose, "is_used": False}
            )
            
            if not otp_record:
                return {"success": False, "message": "No valid verification code found."}
            
            # 1. Check Expiration (Ensuring UTC-aware comparison)
            expires_at = datetime.fromisoformat(otp_record["expires_at"].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_at:
                await update_one(self.otp_table, {"otp_id": otp_record["otp_id"]}, {"is_expired": True})
                return {"success": False, "message": "Verification code has expired."}
            
            # 2. Rate Limiting: Check and increment failed attempts
            attempts = otp_record.get("attempts", 0) + 1
            if attempts > settings.OTP_MAX_ATTEMPTS:
                cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_COOLDOWN_MINUTES)
                await update_one(
                    self.otp_table,
                    {"otp_id": otp_record["otp_id"]},
                    {"is_locked": True, "locked_until": cooldown_until.isoformat()}
                )
                return {
                    "success": False, 
                    "message": "Too many failed attempts. Account temporarily locked.",
                    "cooldown_until": cooldown_until.isoformat()
                }
            
            # Update attempt count
            await update_one(self.otp_table, {"otp_id": otp_record["otp_id"]}, {"attempts": attempts})
            
            # 3. Verify Code Match
            if otp_record["otp"] != otp:
                remaining = settings.OTP_MAX_ATTEMPTS - attempts
                return {"success": False, "message": f"Invalid code. {remaining} attempts left.", "attempts_remaining": remaining}
            
            # 4. Success: Mark as used
            await update_one(
                self.otp_table,
                {"otp_id": otp_record["otp_id"]},
                {"is_used": True, "used_at": datetime.now(timezone.utc).isoformat()}
            )
            
            logger.info(f"✅ OTP verified successfully for {email}")
            return {"success": True, "message": "Verification successful."}
            
        except Exception as e:
            logger.error(f"❌ OTP verification failure: {str(e)}")
            return {"success": False, "message": "An internal error occurred."}

    async def _cleanup_old_otps(self, email: str):
        """Internal: Marks previous unused OTPs as expired to prevent database clutter."""
        try:
            old_otps = await select_all(self.otp_table, {"email": email.lower(), "is_used": False})
            for otp in old_otps:
                await update_one(self.otp_table, {"otp_id": otp["otp_id"]}, {"is_expired": True})
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}")

    async def _check_cooldown(self, email: str) -> Dict:
        """Internal: Checks if a user is currently in a lockout period."""
        try:
            locked_otp = await select_one(self.otp_table, {"email": email.lower(), "is_locked": True})
            if locked_otp and locked_otp.get("locked_until"):
                locked_until = datetime.fromisoformat(locked_otp["locked_until"].replace('Z', '+00:00'))
                if datetime.now(timezone.utc) < locked_until:
                    return {"in_cooldown": True, "cooldown_until": locked_until.isoformat()}
            return {"in_cooldown": False}
        except Exception:
            return {"in_cooldown": False}

# Global Singleton Instance
otp_service = OTPService()