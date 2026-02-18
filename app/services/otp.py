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
    
    # ============ INVITATION SYSTEM ============

    async def send_invitation_email(self, email: str, invite_url: str) -> bool:
        """
        Dispatches a professional invitation email for new staff members.
        This provides a clickable link instead of a raw OTP.
        """
        # Always log to terminal for local development tracking
        logger.info("=" * 60)
        logger.info(f"📧 [INVITATION DISPATCH] To: {email}")
        logger.info(f"🔗 Link: {invite_url}")
        logger.info("=" * 60)

        if not all([settings.SMTP_SERVER, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
            logger.warning("⚠️ SMTP not configured. Invitation only visible in logs.")
            return True

        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; background-color: #f9fafb; padding: 20px;">
            <div style="max-width: 550px; margin: auto; background: white; padding: 40px; border-radius: 16px; border: 1px solid #e5e7eb; shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
                <div style="text-align: center; margin-bottom: 24px;">
                    <div style="background: #4F46E5; width: 60px; height: 60px; border-radius: 12px; margin: auto; display: flex; align-items: center; justify-content: center; color: white; font-size: 30px; font-weight: bold;">
                        H
                    </div>
                </div>
                <h2 style="color: #111827; text-align: center; margin-bottom: 10px;">You're Invited!</h2>
                <p style="color: #4b5563; font-size: 16px; text-align: center; line-height: 1.6;">
                    An administrator has invited you to join their branch as a staff member. 
                    Please click the button below to set up your account and join the team.
                </p>
                <div style="text-align: center; margin: 35px 0;">
                    <a href="{invite_url}" style="background-color: #4F46E5; color: white; padding: 14px 30px; text-decoration: none; border-radius: 10px; font-weight: bold; font-size: 16px; display: inline-block;">
                        Accept Invitation
                    </a>
                </div>
                <p style="color: #9ca3af; font-size: 13px; text-align: center;">
                    This invitation link is unique to you and will expire in <strong>7 days</strong>.
                </p>
                <hr style="border: none; border-top: 1px solid #f3f4f6; margin: 30px 0;" />
                <p style="color: #d1d5db; font-size: 11px; text-align: center;">
                    If you weren't expecting this invitation, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "🔐 Staff Invitation - Action Required"
            msg["From"] = settings.EMAIL_FROM or settings.SMTP_USERNAME
            msg["To"] = email
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"✅ Invitation email sent successfully to {email}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send invitation email: {str(e)}")
            return False

    # ============ OTP CORE LOGIC ============

    async def generate_otp(self, email: str, purpose: str = "verification") -> str:
        """Generates and stores an OTP code. Reuses existing if valid for > 2 mins."""
        email = email.lower().strip()
        
        existing_otp = await select_one(
            self.otp_table,
            {"email": email, "purpose": purpose, "is_used": False, "is_expired": False}
        )
        
        if existing_otp:
            expires_at = datetime.fromisoformat(existing_otp["expires_at"].replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            time_remaining = (expires_at - current_time).total_seconds() / 60
            
            if time_remaining > 2:
                logger.info(f"✅ Reusing valid OTP for {email}. Expires in {time_remaining:.1f}m")
                return existing_otp["otp"]
            else:
                await update_one(self.otp_table, {"otp_id": existing_otp["otp_id"]}, {"is_expired": True})
        
        cooldown_data = await self._check_cooldown(email)
        if cooldown_data["in_cooldown"]:
            raise Exception(f"Rate limit exceeded. Please wait {settings.OTP_COOLDOWN_MINUTES} minutes.")
        
        await self._cleanup_old_otps(email)
        
        otp = ''.join(secrets.choice(string.digits) for _ in range(settings.OTP_LENGTH))
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)
        
        otp_record = {
            "email": email, "otp": otp, "purpose": purpose,
            "expires_at": expires_at.isoformat(), "attempts": 0,
            "is_used": False, "is_expired": False, "is_locked": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        result = await insert_one(self.otp_table, otp_record)
        if not result:
            raise Exception("Critical: Failed to persist OTP to database.")
        
        logger.info(f"✨ Fresh OTP generated for {email}: {otp} (Purpose: {purpose})")
        return otp

    async def send_otp_email(self, email: str, otp: str, purpose: str = "verification") -> bool:
        """Dispatches the OTP via SMTP using a secure HTML template."""
        logger.info("=" * 60)
        logger.info(f"📧 [OTP DELIVERY] To: {email} | Code: {otp}")
        logger.info("=" * 60)

        if not all([settings.SMTP_SERVER, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
            logger.warning(f"⚠️ SMTP not configured. OTP visible in console only.")
            return True

        subject = "🔐 Account Verification" if purpose == "verification" else "🔑 Password Reset Code"
        header = "Verify Your Account" if purpose == "verification" else "Reset Your Password"

        html_content = f"""
        <html>
        <body style="font-family: 'Segoe UI', sans-serif; background-color: #f3f4f6; padding: 20px;">
            <div style="max-width: 450px; margin: auto; background: white; padding: 40px; border-radius: 12px; border: 1px solid #e5e7eb;">
                <h2 style="color: #4F46E5; text-align: center; margin-bottom: 24px;">{header}</h2>
                <p style="color: #374151; font-size: 16px; text-align: center;">
                    Use this code to complete your request. Expires in <strong>{settings.OTP_EXPIRE_MINUTES}m</strong>.
                </p>
                <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; text-align: center; margin: 30px 0; border: 1px dashed #4F46E5;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 10px; color: #111827;">{otp}</span>
                </div>
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
            return True
        except Exception as e:
            logger.error(f"❌ SMTP Error: {str(e)}")
            return False

    async def verify_otp(self, email: str, otp: str, purpose: str = "verification") -> Dict:
        """Validates the OTP and manages attempt counts/lockouts."""
        try:
            email = email.lower().strip()
            otp_record = await select_one(self.otp_table, {"email": email, "purpose": purpose, "is_used": False})
            
            if not otp_record:
                return {"success": False, "message": "No valid verification code found."}
            
            expires_at = datetime.fromisoformat(otp_record["expires_at"].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_at:
                await update_one(self.otp_table, {"otp_id": otp_record["otp_id"]}, {"is_expired": True})
                return {"success": False, "message": "Verification code has expired."}
            
            attempts = otp_record.get("attempts", 0) + 1
            if attempts > settings.OTP_MAX_ATTEMPTS:
                cooldown_until = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_COOLDOWN_MINUTES)
                await update_one(self.otp_table, {"otp_id": otp_record["otp_id"]}, 
                                 {"is_locked": True, "locked_until": cooldown_until.isoformat()})
                return {"success": False, "message": "Too many failed attempts. Account locked."}
            
            await update_one(self.otp_table, {"otp_id": otp_record["otp_id"]}, {"attempts": attempts})
            
            if otp_record["otp"] != otp:
                return {"success": False, "message": f"Invalid code. {settings.OTP_MAX_ATTEMPTS - attempts} attempts left."}
            
            await update_one(self.otp_table, {"otp_id": otp_record["otp_id"]}, 
                             {"is_used": True, "used_at": datetime.now(timezone.utc).isoformat()})
            
            return {"success": True, "message": "Verification successful."}
        except Exception as e:
            logger.error(f"❌ OTP Error: {str(e)}")
            return {"success": False, "message": "Internal error."}

    async def _cleanup_old_otps(self, email: str):
        """Internal: Marks previous unused OTPs as expired."""
        try:
            old_otps = await select_all(self.otp_table, {"email": email.lower(), "is_used": False})
            for otp in old_otps:
                await update_one(self.otp_table, {"otp_id": otp["otp_id"]}, {"is_expired": True})
        except Exception: pass

    async def _check_cooldown(self, email: str) -> Dict:
        """Internal: Checks for lockout period."""
        try:
            locked_otp = await select_one(self.otp_table, {"email": email.lower(), "is_locked": True})
            if locked_otp and locked_otp.get("locked_until"):
                locked_until = datetime.fromisoformat(locked_otp["locked_until"].replace('Z', '+00:00'))
                if datetime.now(timezone.utc) < locked_until:
                    return {"in_cooldown": True}
            return {"in_cooldown": False}
        except Exception: return {"in_cooldown": False}

# Singleton Instance
otp_service = OTPService()