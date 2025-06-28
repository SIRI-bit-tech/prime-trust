"""
Utility functions for the accounts app
"""
import random
import string
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

def generate_verification_code():
    """Generate a 6-digit verification code."""
    return ''.join(random.choices(string.digits, k=6))

def send_verification_email(email, code, is_login=False):
    """
    Send verification email with the provided code.
    
    Args:
        email (str): The recipient's email address
        code (str): The verification code
        is_login (bool): Whether this is for login verification (True) or registration (False)
    """
    logger.info(f"Attempting to send verification email to {email}")
    
    # Determine the subject and template based on the verification type
    if is_login:
        subject = 'Login Verification Code'
        template = 'emails/login_code_email.html'
        timeout = settings.LOGIN_VERIFICATION_TIMEOUT
    else:
        subject = 'Verify Your Email Address'
        template = 'emails/verification_email.html'
        timeout = settings.EMAIL_VERIFICATION_TIMEOUT

    logger.info(f"Using template: {template}")

    try:
        # Render the HTML email template
        html_message = render_to_string(template, {
            'verification_code': code
        })
        plain_message = strip_tags(html_message)
        
        logger.info(f"Email content generated for {email}")

        # Send the email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email sent successfully to {email}")
        
        # Store the verification code in cache
        cache_key = f"verification_code_{email}"
        cache.set(cache_key, code, timeout)
        logger.info(f"Verification code stored in cache for {email}")
        
        return True
    except Exception as e:
        logger.error(f"Error sending verification email to {email}: {str(e)}")
        return False

def verify_code(email, code):
    """
    Verify the provided code against the stored code.
    
    Args:
        email (str): The email address
        code (str): The verification code to verify
        
    Returns:
        bool: True if verification successful, False otherwise
    """
    logger.info(f"Verifying code for {email}")
    cache_key = f"verification_code_{email}"
    stored_code = cache.get(cache_key)
    
    logger.info(f"Stored code for {email}: {stored_code}, Provided code: {code}")
    
    if stored_code and stored_code == code:
        # Delete the code after successful verification
        cache.delete(cache_key)
        logger.info(f"Verification code validated successfully for {email}")
        return True
    
    logger.warning(f"Invalid verification code attempt for {email}. Stored: {stored_code}, Provided: {code}")
    return False
