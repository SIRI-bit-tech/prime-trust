"""
Utility functions for the accounts app
"""
import random
import string
import socket
from smtplib import SMTPException
from django.core.mail import send_mail, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.cache import cache
from core.gmail_service import send_gmail
import pyotp
import qrcode
import io
import base64
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from typing import Tuple, List, Optional, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)

def generate_verification_code():
    """Generate a 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(user, code, is_login=False):
    """
    Send verification email with the provided code via Gmail API.
    
    Args:
        user: User object or email string
        code (str): The verification code
        is_login (bool): Whether this is for login verification (True) or registration (False)
    """
    # Handle both user objects and email strings
    if hasattr(user, 'email'):
        email = user.email
        user_name = user.get_full_name() if hasattr(user, 'get_full_name') else email
    else:
        email = user
        user_name = email
    
    # Determine the subject and template based on the verification type
    if is_login:
        subject = 'Login Verification Code'
        template = 'emails/login_code_email.html'
        timeout = settings.LOGIN_VERIFICATION_TIMEOUT
    else:
        subject = 'Verify Your Email Address'
        template = 'emails/verification_email.html'
        timeout = settings.EMAIL_VERIFICATION_TIMEOUT

    try:
        # Render the HTML email template
        context = {
            'verification_code': code,
            'user_name': user_name,
            'is_login': is_login
        }
        html_message = render_to_string(template, context)
        text_message = strip_tags(html_message)

        # Try Gmail API for production
        if not settings.DEBUG and hasattr(settings, 'GMAIL_SENDER_EMAIL') and settings.GMAIL_SENDER_EMAIL:
            try:
                success, result = send_gmail(
                    to_emails=[email],
                    subject=subject,
                    text_content=text_message,
                    html_content=html_message,
                    headers={'X-Verification-Type': 'login' if is_login else 'registration'}
                )
                
                if success:
                    # Store the verification code in cache
                    cache_key = f"verification_code_{email}"
                    cache.set(cache_key, code, timeout)
                    
                    logger.info(f"Verification email sent via Gmail API to {email} (login: {is_login})")
                    return True
                else:
                    logger.error(f"Gmail API failed for {email}: {result}")
                    # Fall through to Django backend
                    
            except Exception as gmail_error:
                logger.error(f"Gmail API error for {email}: {str(gmail_error)}")
                # Fall through to Django backend
        
        # Fallback to Django's email backend
        sent = send_mail(
            subject=f"{getattr(settings, 'GMAIL_SUBJECT_PREFIX', '[PrimeTrust] ')}{subject}",
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        if sent:
            # Store the verification code in cache
            cache_key = f"verification_code_{email}"
            cache.set(cache_key, code, timeout)
            
            logger.info(f"Verification email sent via Django backend to {email} (login: {is_login})")
            return True
        else:
            logger.error(f"Django email backend failed for {email}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending verification email to {email}: {str(e)}", exc_info=True)
        return False

def verify_code(email, provided_code):
    """
    Verify the provided code against the cached code.
    
    Args:
        email (str): The user's email address
        provided_code (str): The code provided by the user
        
    Returns:
        bool: True if the code is valid, False otherwise
    """
    try:
        cache_key = f"verification_code_{email}"
        stored_code = cache.get(cache_key)
        
        if stored_code and stored_code == provided_code:
            # Remove the code from cache after successful verification
            cache.delete(cache_key)
            logger.info(f"Verification code verified successfully for {email}")
            return True
        else:
            logger.warning(f"Invalid verification code provided for {email}")
            return False
            
    except Exception as e:
        logger.error(f"Error verifying code for {email}: {str(e)}")
        return False

def send_password_reset_email(user, reset_link):
    """
    Send password reset email via Gmail API
    
    Args:
        user: User object
        reset_link (str): Password reset link
    """
    try:
        subject = 'Password Reset Request'
        
        context = {
            'user_name': user.get_full_name(),
            'reset_link': reset_link,
            'site_name': 'PrimeTrust'
        }
        
        html_message = render_to_string('emails/password_reset.html', context)
        text_message = strip_tags(html_message)
        
        # Try Gmail API for production
        if not settings.DEBUG and hasattr(settings, 'GMAIL_SENDER_EMAIL') and settings.GMAIL_SENDER_EMAIL:
            success, result = send_gmail(
                to_emails=[user.email],
                subject=subject,
                text_content=text_message,
                html_content=html_message,
                headers={'X-Password-Reset': 'true'}
            )
            
            if success:
                logger.info(f"Password reset email sent via Gmail API to {user.email}")
                return True
            else:
                logger.error(f"Gmail API failed for password reset: {result}")
        
        # Fallback to Django backend
        sent = send_mail(
            subject=f"{getattr(settings, 'GMAIL_SUBJECT_PREFIX', '[PrimeTrust] ')}{subject}",
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        if sent:
            logger.info(f"Password reset email sent via Django backend to {user.email}")
            return True
        else:
            logger.error(f"Failed to send password reset email to {user.email}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending password reset email: {str(e)}", exc_info=True)
        return False

class TwoFactorAuth:
    """Production-grade 2FA implementation with TOTP and backup codes"""
    
    def __init__(self, user):
        self.user = user
        self.security_settings = self.get_or_create_security_settings()
    
    def get_or_create_security_settings(self):
        """Get or create security settings for the user"""
        from .models_security import SecuritySettings
        settings, created = SecuritySettings.objects.get_or_create(
            user=self.user,
            defaults={
                'two_factor_enabled': False,
                'security_score': 50,  # Default score
                'password_last_changed': timezone.now(),
                'failed_login_attempts': 0,
                'login_notifications_enabled': True,
                'transaction_notifications_enabled': True,
                'security_alerts_enabled': True,
                'password_change_required': False,
            }
        )
        return settings
    
    def generate_secret_key(self) -> str:
        """Generate a secure secret key for TOTP"""
        return pyotp.random_base32()
    
    def enable_2fa(self) -> Tuple[str, str]:
        """
        Enable 2FA for the user
        Returns: (secret_key, qr_code_url)
        """
        try:
            # Generate secret key
            secret_key = self.generate_secret_key()
            
            # Create TOTP instance
            totp = pyotp.TOTP(secret_key)
            
            # Generate QR code URL
            qr_code_url = totp.provisioning_uri(
                name=self.user.email,
                issuer_name="PrimeTrust Banking"
            )
            
            # Save encrypted secret key
            self.security_settings.two_factor_secret = secret_key
            self.security_settings.two_factor_enabled = True
            self.security_settings.save()
            
            # Log security event
            self.log_security_event('2FA_ENABLED', 'low')
            
            return secret_key, qr_code_url
            
        except Exception as e:
            logger.error(f"Error enabling 2FA for user {self.user.id}: {str(e)}")
            self.log_security_event('2FA_ENABLE_FAILED', 'medium', description=str(e))
            raise
    
    def disable_2fa(self) -> bool:
        """Disable 2FA for the user"""
        try:
            self.security_settings.two_factor_enabled = False
            self.security_settings.two_factor_secret = None
            self.security_settings.save()
            
            # Log security event
            self.log_security_event('2FA_DISABLED', 'low')
            
            return True
            
        except Exception as e:
            logger.error(f"Error disabling 2FA for user {self.user.id}: {str(e)}")
            self.log_security_event('2FA_DISABLE_FAILED', 'medium', description=str(e))
            return False
    
    def verify_totp(self, token: str) -> bool:
        """Verify TOTP token"""
        if not self.security_settings.two_factor_enabled:
            return False
        
        try:
            # Check if token was recently used (prevent replay attacks)
            cache_key = f"totp_used_{self.user.id}_{token}"
            if cache.get(cache_key):
                self.log_security_event('2FA_REPLAY_ATTEMPT', 'medium')
                return False
            
            # Verify token
            totp = pyotp.TOTP(self.security_settings.two_factor_secret)
            is_valid = totp.verify(token, valid_window=1)  # Allow 1 time step tolerance
            
            if is_valid:
                # Mark token as used for 60 seconds
                cache.set(cache_key, True, 60)
                self.log_security_event('2FA_SUCCESS', 'low')
                
                # Update security score
                self.update_security_score('2fa_success', 5)
            else:
                self.log_security_event('2FA_FAILED', 'medium')
                self.update_security_score('2fa_failure', -10)
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error verifying TOTP for user {self.user.id}: {str(e)}")
            self.log_security_event('2FA_VERIFY_ERROR', 'high', description=str(e))
            return False
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Generate secure backup codes"""
        try:
            from .models_security import BackupCode
            
            # Clear existing backup codes
            self.clear_backup_codes()
            
            backup_codes = []
            for _ in range(count):
                # Generate 8-digit code
                code = f"{secrets.randbelow(100000000):08d}"
                backup_codes.append(code)
                
                # Save hashed code
                BackupCode.objects.create(
                    user=self.user,
                    code_hash=make_password(code),
                    created_at=timezone.now()
                )
            
            # Log security event
            self.log_security_event('BACKUP_CODES_GENERATED', 'low')
            
            return backup_codes
            
        except Exception as e:
            logger.error(f"Error generating backup codes for user {self.user.id}: {str(e)}")
            self.log_security_event('BACKUP_CODE_GENERATION_FAILED', 'high', description=str(e))
            return []
    
    def verify_backup_code(self, code: str, request=None) -> bool:
        """Verify backup code"""
        try:
            from .models_security import BackupCode
            
            # Get unused backup codes
            backup_codes = BackupCode.objects.filter(
                user=self.user,
                is_used=False
            )
            
            for backup_code in backup_codes:
                if check_password(code, backup_code.code_hash):
                    # Mark as used
                    backup_code.is_used = True
                    backup_code.used_at = timezone.now()
                    if request:
                        backup_code.used_ip = self.get_client_ip(request)
                    backup_code.save()
                    
                    # Log security event
                    self.log_security_event('BACKUP_CODE_USED', 'low')
                    
                    return True
            
            # Log failed attempt
            self.log_security_event('BACKUP_CODE_FAILED', 'medium')
            return False
            
        except Exception as e:
            logger.error(f"Error verifying backup code for user {self.user.id}: {str(e)}")
            self.log_security_event('BACKUP_CODE_VERIFY_ERROR', 'high', description=str(e))
            return False
    
    def clear_backup_codes(self):
        """Clear all backup codes"""
        from .models_security import BackupCode
        BackupCode.objects.filter(user=self.user).delete()
    
    def get_backup_codes_status(self) -> Dict[str, Any]:
        """Get backup codes status"""
        from .models_security import BackupCode
        
        total_codes = BackupCode.objects.filter(user=self.user).count()
        used_codes = BackupCode.objects.filter(user=self.user, is_used=True).count()
        
        return {
            'total': total_codes,
            'used': used_codes,
            'remaining': total_codes - used_codes,
            'generated': total_codes > 0  # Check if codes exist
        }
    
    def generate_qr_code(self, provisioning_uri: str) -> str:
        """Generate QR code as base64 string"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Convert to base64
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            return f"data:image/png;base64,{img_base64}"
            
        except Exception as e:
            logger.error(f"Error generating QR code: {str(e)}")
            return ""
    
    def get_2fa_status(self) -> Dict[str, Any]:
        """Get comprehensive 2FA status"""
        backup_status = self.get_backup_codes_status()
        
        return {
            'enabled': self.security_settings.two_factor_enabled,
            'secret_configured': bool(self.security_settings.two_factor_secret),
            'backup_codes': backup_status,
            'can_disable': self.security_settings.two_factor_enabled,
            'setup_complete': (
                self.security_settings.two_factor_enabled and 
                backup_status['generated']
            )
        }
    
    def log_security_event(self, event_type: str, risk_level: str = 'low', description: str = None):
        """Log security event"""
        try:
            from .models_security import SecurityEvent
            
            SecurityEvent.objects.create(
                user=self.user,
                event_type=event_type,
                risk_level=risk_level,
                description=description or "",
                ip_address='127.0.0.1',  # Default IP, can be improved to get actual IP
                user_agent='',  # Can be improved to get actual user agent
            )
            
        except Exception as e:
            logger.error(f"Error logging security event: {str(e)}")
    
    def update_security_score(self, action: str, score_change: int):
        """Update user security score"""
        try:
            current_score = self.security_settings.security_score
            new_score = max(0, min(100, current_score + score_change))
            
            self.security_settings.security_score = new_score
            self.security_settings.save()
            
            # Log significant score changes
            if abs(score_change) >= 10:
                self.log_security_event(
                    'SECURITY_SCORE_UPDATED',
                    'low',
                    description=f"Score changed from {current_score} to {new_score} ({action})"
                )
                
        except Exception as e:
            logger.error(f"Error updating security score: {str(e)}")
    
    def get_client_ip(self, request) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or '127.0.0.1'


def generate_secure_token(length: int = 32) -> str:
    """Generate secure random token"""
    return secrets.token_urlsafe(length)


def hash_device_fingerprint(user_agent: str, ip_address: str) -> str:
    """Create device fingerprint hash"""
    fingerprint_data = f"{user_agent}:{ip_address}".encode('utf-8')
    return hashlib.sha256(fingerprint_data).hexdigest()


def is_suspicious_login(user, ip_address: str, user_agent: str) -> bool:
    """Check if login attempt is suspicious"""
    try:
        from .models_security import UserDevice, SecurityEvent
        
        # Check if device is known
        device_hash = hash_device_fingerprint(user_agent, ip_address)
        known_device = UserDevice.objects.filter(
            user=user,
            browser_fingerprint=device_hash,
            trust_level__in=['trusted', 'recognized']
        ).exists()
        
        if known_device:
            return False
        
        # Check recent failed attempts
        recent_failures = SecurityEvent.objects.filter(
            user=user,
            event_type='LOGIN_FAILED',
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        return recent_failures >= 3
        
    except Exception as e:
        logger.error(f"Error checking suspicious login: {str(e)}")
        return False


def rate_limit_key(user_id: int, action: str) -> str:
    """Generate rate limit cache key"""
    return f"rate_limit:{user_id}:{action}"


def is_rate_limited(user_id: int, action: str, limit: int = 5, window: int = 300) -> bool:
    """Check if user is rate limited"""
    try:
        cache_key = rate_limit_key(user_id, action)
        attempts = cache.get(cache_key, 0)
        
        if attempts >= limit:
            return True
        
        # Increment attempts
        cache.set(cache_key, attempts + 1, window)
        return False
        
    except Exception as e:
        logger.error(f"Error checking rate limit: {str(e)}")
        return False
