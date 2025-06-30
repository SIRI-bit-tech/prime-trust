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
    # Determine the subject and template based on the verification type
    if is_login:
        subject = 'Login Verification Code'
        template = 'emails/login_code_email.html'
        timeout = settings.LOGIN_VERIFICATION_TIMEOUT
    else:
        subject = 'Verify Your Email Address'
        template = 'emails/verification_email.html'
        timeout = settings.EMAIL_VERIFICATION_TIMEOUT

    # Render the HTML email template
    html_message = render_to_string(template, {
        'verification_code': code
    })
    plain_message = strip_tags(html_message)

    try:
        # Send the email using the configured backend
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Store the verification code in cache
        cache_key = f"verification_code_{email}"
        cache.set(cache_key, code, timeout)
        
        return True
            
    except Exception:
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
    cache_key = f"verification_code_{email}"
    stored_code = cache.get(cache_key)
    
    if stored_code and stored_code == code:
        # Delete the code after successful verification
        cache.delete(cache_key)
        return True
    
    return False
