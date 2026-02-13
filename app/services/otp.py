import secrets
import string
import smtplib
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Modular imports reflecting the production directory structure
from app.db.supabase import insert_one, select_one, update_one, select_all
from app.core.config import settings

logger = logging.getLogger(__name__)

class OTPService:
    def __init__(self):
        """Initializes the service with the corresponding database table name."""
        self.otp_table = "otp_verifications"
    
    async def generate_otp(self, email: str, purpose: str = "verification") -> str:
        """
        Generates and stores an OTP code. 
        Reuses a valid OTP if it hasn't expired and has > 5 mins life left.
        """
        email = email.lower()
        
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
            expires_at = datetime.fromisoformat(existing_otp["expires_at"].replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            
            if current_time < expires_at:
                time_remaining = (expires_at - current_time).total_seconds() / 60
                # Reuse if the code is still valid for more than 5 minutes
                if time_remaining > 5:
                    logger.info(f"✅ Reusing valid OTP for {email}. Expires in {time_remaining:.1f}m")
                    return existing_otp["otp"]
        
        # 2. Security Check: Verify user is not currently rate-limited (cooldown)
        cooldown_data = await self._check_cooldown(email)
        if cooldown_data["in_cooldown"]:
            raise Exception(f"Rate limit exceeded. Please wait {settings.OTP_COOLDOWN_MINUTES} minutes.")
        
        # 3. Cleanup: Expire any old, unused codes for this email address
        await self._cleanup_old_otps(email)
        
        # 4. Generate New 6-Digit Code
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
        
        logger.info(f"✅ New OTP generated for {email} (Purpose: {purpose})")
        return otp

    async def send_otp_email(self, email: str, otp: str, purpose: str = "verification") -> bool:
        """
        Dispatches the OTP via SMTP using a secure HTML template.
        Integrated with settings for Gmail/SMTP delivery.
        """
        # Console Log for Development Auditing
        logger.info("=" * 70)
        logger.info(f"📧 [CONSOLE LOG] OTP for {email}: {otp}")
        logger.info(f"Purpose: {purpose}")
        logger.info("=" * 70)

        if not all([settings.SMTP_SERVER, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
            logger.warning(f"⚠️ SMTP not configured. OTP for {email} will only appear in console.")
            return True

        subject = "🔐 Account Verification" if purpose == "verification" else "🔑 Password Reset"
        header_text = "Verify Your Account" if purpose == "verification" else "Reset Your Password"
        msg_text = "Enter this code to verify your email:" if purpose == "verification" else "Use this code to reset your password:"

        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', sans-serif; background-color: #f3f4f6; padding: 20px;">
            <div style="max-width: 450px; margin: auto; background: white; padding: 40px; border-radius: 12px; border: 1px solid #e5e7eb;">
                <h2 style="color: #4F46E5; text-align: center;">{header_text}</h2>
                <p style="color: #374151; font-size: 16px; text-align: center;">{msg_text}</p>
                <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #111827;">{otp}</span>
                </div>
                <p style="color: #6B7280; font-size: 14px; text-align: center;">
                    This code will expire in <strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong>.
                </p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #9ca3af; font-size: 11px; text-align: center;">If you didn't request this, please ignore this email.</p>
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
            
            logger.info(f"✅ OTP email successfully sent to {email}")
            return True
        except Exception as e:
            logger.error(f"❌ SMTP Error sending to {email}: {str(e)}")
            return False

    async def verify_otp(self, email: str, otp: str, purpose: str = "verification") -> Dict:
        """Validates the OTP and manages attempt counts/lockouts."""
        try:
            email = email.lower()
            otp_record = await select_one(
                self.otp_table, 
                {"email": email, "purpose": purpose, "is_used": False}
            )
            
            if not otp_record:
                return {"success": False, "message": "Invalid verification code or already used."}
            
            # 1. Check Lockout Status
            if otp_record.get("is_locked"):
                return {"success": False, "message": "Account locked due to too many attempts."}

            # 2. Check Expiration
            expires_at = datetime.fromisoformat(otp_record["expires_at"].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_at:
                await update_one(self.otp_table, {"otp_id": otp_record["otp_id"]}, {"is_expired": True})
                return {"success": False, "message": "Verification code has expired."}
            
            # 3. Handle Attempts & Rate Limiting
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
                    "message": "Too many failed attempts. Try again later.",
                    "cooldown_until": cooldown_until.isoformat()
                }
            
            # Update attempt count in DB
            await update_one(self.otp_table, {"otp_id": otp_record["otp_id"]}, {"attempts": attempts})
            
            # 4. Final Validation
            if otp_record["otp"] != otp:
                remaining = settings.OTP_MAX_ATTEMPTS - attempts
                return {"success": False, "message": f"Invalid code. {remaining} attempts left.", "attempts_remaining": remaining}
            
            # 5. Mark as Used Successfully
            await update_one(
                self.otp_table,
                {"otp_id": otp_record["otp_id"]},
                {"is_used": True, "used_at": datetime.now(timezone.utc).isoformat()}
            )
            
            logger.info(f"✅ OTP successfully verified for {email}")
            return {"success": True, "message": "Verification successful."}
            
        except Exception as e:
            logger.error(f"❌ OTP verification failure: {str(e)}")
            return {"success": False, "message": "An internal error occurred during verification."}

    async def _cleanup_old_otps(self, email: str):
        """Marks previous unused OTPs as expired to prevent collisions."""
        try:
            old_otps = await select_all(self.otp_table, {"email": email.lower(), "is_used": False})
            for otp in old_otps:
                await update_one(self.otp_table, {"otp_id": otp["otp_id"]}, {"is_expired": True})
        except Exception as e:
            logger.error(f"Cleanup OTP error: {str(e)}")

    async def _check_cooldown(self, email: str) -> Dict:
        """Checks if a user is currently locked out."""
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