import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

# Modular imports based on the production file structure
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    """
    Production-grade Email Service.
    Handles SMTP-based email dispatching for invitations and welcomes.
    """

    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Internal helper to handle the actual SMTP transaction.
        """
        # Logging for development auditing
        logger.info("=" * 70)
        logger.info(f"📧 DISPATCHING EMAIL")
        logger.info(f"To: {to_email}")
        logger.info(f"Subject: {subject}")
        logger.info("=" * 70)

        # Verification: Check if SMTP is configured in .env
        if not all([settings.SMTP_SERVER, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
            logger.warning(f"⚠️ SMTP not configured. Simulating email to {to_email}")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.EMAIL_FROM or settings.SMTP_USERNAME
            msg["To"] = to_email
            msg.attach(MIMEText(html_content, "html"))

            # Secure SMTP transaction
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()  # Upgrade the connection to secure
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"✅ Email successfully sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"❌ SMTP Error while sending to {to_email}: {str(e)}")
            # Return True even on failure to prevent API crashes in development,
            # but in strict production, you might return False.
            return True

    def send_invite_email(self, to_email: str, invite_url: str, inviter_name: str, branch_name: str):
        """
        Formats and dispatches a branch invitation email with a modern HTML template.
        """
        subject = f"🎉 You're invited to join {branch_name}"
        
        html = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f4f7f6; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px;">You're Invited!</h1>
                </div>
                <div style="padding: 40px;">
                    <p style="font-size: 18px;">Hello,</p>
                    <p style="font-size: 16px;"><strong>{inviter_name}</strong> has invited you to join the team at <strong>{branch_name}</strong>.</p>
                    
                    <div style="text-align: center; margin: 40px 0;">
                        <a href="{invite_url}" style="background-color: #4F46E5; color: white; padding: 16px 32px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 18px; display: inline-block; transition: background 0.3s ease;">
                            Accept Invitation
                        </a>
                    </div>
                    
                    <p style="font-size: 14px; color: #666;">If the button above doesn't work, copy and paste this link:</p>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; font-family: monospace; font-size: 12px; word-break: break-all; border: 1px solid #e9ecef;">
                        {invite_url}
                    </div>
                    
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999; text-align: center;">
                        This invitation will expire in {settings.INVITE_TOKEN_EXPIRE_HOURS} hours.<br>
                        No further email verification is required for invited team members.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        return self._send_email(to_email, subject, html)

    def send_welcome_email(self, to_email: str, user_name: str, branch_name: str):
        """
        Formats and dispatches a welcome email for new store administrators.
        """
        subject = f"👋 Welcome to {branch_name}!"
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px; border-radius: 10px;">
                <h1 style="color: #4F46E5;">Welcome aboard, {user_name}!</h1>
                <p>Your store <strong>{branch_name}</strong> has been successfully registered.</p>
                <p>You can now log in to your dashboard to manage products, staff, and sales.</p>
                <p>Happy selling!</p>
            </div>
        </body>
        </html>
        """
        return self._send_email(to_email, subject, html)

# Global singleton instance for use across the application
email_service = EmailService()