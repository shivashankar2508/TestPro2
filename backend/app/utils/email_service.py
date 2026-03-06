import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
from typing import Optional

load_dotenv()

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@testtrack.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")
SENDER_NAME = os.getenv("SENDER_NAME", "TestTrack Pro")

# Frontend URL for email links
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

class EmailService:
    """Email service for sending verification and reset emails"""
    
    @staticmethod
    def send_email(
        recipient: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """Send email"""
        try:
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
            message["To"] = recipient
            
            if plain_content:
                message.attach(MIMEText(plain_content, "plain"))
            message.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SENDER_EMAIL, SENDER_PASSWORD)
                server.sendmail(SENDER_EMAIL, recipient, message.as_string())
            
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False
    
    @staticmethod
    def send_verification_email(email: str, verification_token: str) -> bool:
        """Send email verification link"""
        verification_url = f"{FRONTEND_URL}/auth/verify-email?token={verification_token}"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>Welcome to TestTrack Pro!</h2>
                    <p>Thank you for registering. Please verify your email address to activate your account.</p>
                    <p>
                        <a href="{verification_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                            Verify Email Address
                        </a>
                    </p>
                    <p>Or copy and paste this link in your browser:</p>
                    <p><code>{verification_url}</code></p>
                    <p>This link will expire in 24 hours.</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        If you didn't create this account, you can safely ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        plain_content = f"""
        Welcome to TestTrack Pro!
        
        Please verify your email address to activate your account.
        
        Click here: {verification_url}
        
        Or copy and paste this link in your browser:
        {verification_url}
        
        This link will expire in 24 hours.
        """
        
        return EmailService.send_email(
            email,
            "Verify Your Email - TestTrack Pro",
            html_content,
            plain_content
        )
    
    @staticmethod
    def send_password_reset_email(email: str, reset_token: str) -> bool:
        """Send password reset link"""
        reset_url = f"{FRONTEND_URL}/auth/reset-password?token={reset_token}"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>Password Reset Request</h2>
                    <p>We received a request to reset your password. Click the link below to create a new password.</p>
                    <p>
                        <a href="{reset_url}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                            Reset Password
                        </a>
                    </p>
                    <p>Or copy and paste this link in your browser:</p>
                    <p><code>{reset_url}</code></p>
                    <p>This link will expire in 1 hour.</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        If you didn't request this, you can safely ignore this email.
                    </p>
                </div>
            </body>
        </html>
        """
        
        plain_content = f"""
        Password Reset Request
        
        We received a request to reset your password. Click the link below to create a new password.
        
        {reset_url}
        
        This link will expire in 1 hour.
        """
        
        return EmailService.send_email(
            email,
            "Password Reset - TestTrack Pro",
            html_content,
            plain_content
        )
    
    @staticmethod
    def send_account_locked_email(email: str, lockout_minutes: int) -> bool:
        """Send account locked notification"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>Account Locked</h2>
                    <p>Your account has been locked due to multiple failed login attempts.</p>
                    <p>Your account will be automatically unlocked in <strong>{lockout_minutes} minutes</strong>.</p>
                    <p>If you think this is an error, please contact support.</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        TestTrack Pro Security Team
                    </p>
                </div>
            </body>
        </html>
        """
        
        plain_content = f"""
        Account Locked
        
        Your account has been locked due to multiple failed login attempts.
        Your account will be automatically unlocked in {lockout_minutes} minutes.
        """
        
        return EmailService.send_email(
            email,
            "Account Locked - TestTrack Pro",
            html_content,
            plain_content
        )

    @staticmethod
    def send_login_notification_email(email: str, device_info: str = "") -> bool:
        """Send successful login notification"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>New Login to Your Account</h2>
                    <p>Your account was just accessed from a new device.</p>
                    <p><strong>Device Information:</strong> {device_info if device_info else "Unknown Device"}</p>
                    <p>If this wasn't you, please reset your password immediately.</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        TestTrack Pro Security Team
                    </p>
                </div>
            </body>
        </html>
        """
        
        plain_content = f"""
        New Login to Your Account
        
        Your account was just accessed from a new device.
        Device: {device_info if device_info else "Unknown"}
        """
        
        return EmailService.send_email(
            email,
            "New Login to Your Account - TestTrack Pro",
            html_content,
            plain_content
        )

    @staticmethod
    def send_welcome_email(email: str, full_name: str, temp_password: str) -> bool:
        """Send welcome email with temporary password"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>Welcome to TestTrack Pro!</h2>
                    <p>Hello {full_name},</p>
                    <p>Your account has been created by an administrator.</p>
                    <p><strong>Your temporary password:</strong> {temp_password}</p>
                    <p>Please log in and change your password immediately at:</p>
                    <a href="{FRONTEND_URL}/auth/login.html" style="color: #667eea;">Login Here</a>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        TestTrack Pro Team
                    </p>
                </div>
            </body>
        </html>
        """
        
        return EmailService.send_email(
            email,
           "Welcome to TestTrack Pro",
            html_content
        )
    
    @staticmethod
    def send_welcome_email_temp_password(email: str, full_name: str) -> bool:
        """Send welcome email when user should choose their own password"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>Welcome to TestTrack Pro!</h2>
                    <p>Hello {full_name},</p>
                    <p>Your account has been created. Please choose a password to get started:</p>
                    <a href="{FRONTEND_URL}/auth/login.html" style="color: #667eea;">Set Your Password</a>
                    <p style="font-size: 12px; color: #666;">
                        TestTrack Pro Team
                    </p>
                </div>
            </body>
        </html>
        """
        
        return EmailService.send_email(
            email,
            "Welcome to TestTrack Pro",
            html_content
        )

    @staticmethod
    def send_role_change_notification(email: str, full_name: str, new_role: str) -> bool:
        """Notify user of role change"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>Your Role Has Been Updated</h2>
                    <p>Hello {full_name},</p>
                    <p>Your role in TestTrack Pro has been changed to <strong>{new_role.upper()}</strong>.</p>
                    <p>This change may affect your access permissions.</p>
                    <p style="font-size: 12px; color: #666;">
                        TestTrack Pro Team
                    </p>
                </div>
            </body>
        </html>
        """
        
        return EmailService.send_email(
            email,
            "Role Updated - TestTrack Pro",
            html_content
        )
    
    @staticmethod
    def send_account_locked_notification(email: str, full_name: str) -> bool:
        """Notify user of account being locked by admin"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>Account Locked</h2>
                    <p>Hello {full_name},</p>
                    <p>Your TestTrack Pro account has been locked by an administrator.</p>
                    <p>Please contact support for assistance.</p>
                    <p style="font-size: 12px; color: #666;">
                        TestTrack Pro Security Team
                    </p>
                </div>
            </body>
        </html>
        """
        
        return EmailService.send_email(
            email,
           "Account Locked - TestTrack Pro",
            html_content
        )
    
    @staticmethod
    def send_account_unlocked_notification(email: str, full_name: str) -> bool:
        """Notify user of account being unlocked"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>Account Unlocked</h2>
                    <p>Hello {full_name},</p>
                    <p>Your TestTrack Pro account has been unlocked. You can now log in.</p>
                    <a href="{FRONTEND_URL}/auth/login.html" style="color: #667eea;">Login Here</a>
                    <p style="font-size: 12px; color: #666;">
                        TestTrack Pro Team
                    </p>
                </div>
            </body>
        </html>
        """
        
        return EmailService.send_email(
            email,
            "Account Unlocked - TestTrack Pro",
            html_content
        )
    
    @staticmethod
    def send_account_deactivated_notification(email: str, full_name: str) -> bool:
        """Notify user of account deactivation"""
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <div style="max-width: 600px; margin: 0 auto;">
                    <h2>Account Deactivated</h2>
                    <p>Hello {full_name},</p>
                    <p>Your TestTrack Pro account has been deactivated.</p>
                    <p>If you believe this is an error, please contact support.</p>
                    <p style="font-size: 12px; color: #666;">
                        TestTrack Pro Team
                    </p>
                </div>
            </body>
        </html>
        """
        
        return EmailService.send_email(
            email,
            "Account Deactivated - TestTrack Pro",
            html_content
        )
