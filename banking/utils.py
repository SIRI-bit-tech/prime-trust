from django.contrib.auth import get_user_model
from .models import Notification
from django.db.models import Q
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from decimal import Decimal
import logging
from django.db import transaction
from django.core.mail import EmailMessage
from smtplib import SMTPException
from core.gmail_service import send_gmail
import random
import string
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_reference_number(prefix="TXN"):
    """
    Generate a unique reference number for transactions.
    
    Args:
        prefix (str): Prefix for the reference number (default: "TXN")
        
    Returns:
        str: A unique reference number
    """
    # Get current date in YYYYMMDD format
    date_str = datetime.now().strftime("%Y%m%d")
    
    # Generate a random 6-digit number
    random_part = ''.join(random.choices(string.digits, k=6))
    
    # Combine prefix, date, and random part
    reference_number = f"{prefix}-{date_str}-{random_part}"
    
    return reference_number

def send_notification(user, notification_type, title, message, related_transaction=None):
    """
    Utility function to send a notification to a user
    
    Args:
        user: The user to send the notification to (can be a User instance, queryset, or 'all')
        notification_type: Type of notification (see Notification.NOTIFICATION_TYPES)
        title: Notification title
        message: Notification message
        related_transaction: Optional related transaction
        
    Returns:
        The created notification or list of notifications
    """
    User = get_user_model()
    
    if user == 'all':
        # Send to all active users
        users = User.objects.filter(is_active=True)
        notifications = []
        for u in users:
            notification = Notification.objects.create(
                user=u,
                notification_type=notification_type,
                title=title,
                message=message,
                related_transaction=related_transaction
            )
            notifications.append(notification)
        return notifications
    elif hasattr(user, '_meta') and user._meta.model == User:
        # Single user instance
        return Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_transaction=related_transaction
        )
    elif hasattr(user, 'filter'):
        # Queryset of users
        notifications = []
        for u in user:
            notification = Notification.objects.create(
                user=u,
                notification_type=notification_type,
                title=title,
                message=message,
                related_transaction=related_transaction
            )
            notifications.append(notification)
        return notifications
    return None

def send_transaction_notification(user, transaction_obj, is_sender=True):
    """
    Send transaction notification email via Gmail API for production
    
    Args:
        user (CustomUser): The user to send the notification to
        transaction_obj (Transaction): The transaction object
        is_sender (bool): Whether the user is the sender (True) or receiver (False)
    """
    try:
        # Format amount with commas for thousands
        formatted_amount = "{:,.2f}".format(transaction_obj.amount)
        
        # Determine the message based on whether user is sender or receiver
        if is_sender:
            transaction_message = f"You just sent ${formatted_amount} to {transaction_obj.to_account.user.get_full_name()}"
            subject = f"Money Sent - ${formatted_amount}"
        else:
            transaction_message = f"You just received ${formatted_amount} from {transaction_obj.from_account.user.get_full_name()}"
            subject = f"Money Received - ${formatted_amount}"
        
        # Get the logo URL
        logo_url = f"{getattr(settings, 'SITE_URL', 'https://primetrust.com')}/static/img/Primetrust-logo-med.png"
        
        # Prepare the email content
        context = {
            'recipient_name': user.get_full_name(),
            'transaction_message': transaction_message,
            'logo_url': logo_url,
            'transaction': transaction_obj,
            'is_sender': is_sender,
            'amount': formatted_amount
        }
        
        # Render the HTML email template
        html_message = render_to_string('emails/transaction_notification.html', context)
        text_message = strip_tags(html_message)
        
        # Try Gmail API first (always use Gmail API for production)
        if hasattr(settings, 'GMAIL_SENDER_EMAIL') and settings.GMAIL_SENDER_EMAIL:
            try:
                success, result = send_gmail(
                    to_emails=[user.email],
                    subject=subject,
                    text_content=text_message,
                    html_content=html_message,
                    headers={'X-Entity-Ref-ID': str(transaction_obj.id)}
                )
                
                if success:
                    logger.info(f"Transaction notification sent via Gmail API to {user.email} for transaction {transaction_obj.id}")
                    return True
                else:
                    logger.error(f"Gmail API failed: {result}")
                    # Fall through to Django email backend
                    
            except Exception as gmail_error:
                logger.error(f"Gmail API error: {str(gmail_error)}")
                # Fall through to Django email backend
        
        # Fallback to Django's email backend
        try:
            email = EmailMessage(
                subject=f"{getattr(settings, 'GMAIL_SUBJECT_PREFIX', '[PrimeTrust] ')}{subject}",
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
                headers={'X-Entity-Ref-ID': str(transaction_obj.id)}
            )
            email.content_subtype = "html"
            
            # Send with retry logic
            sent = email.send(fail_silently=False)
            
            if sent:
                logger.info(f"Transaction notification email sent via Django backend to {user.email} for transaction {transaction_obj.id}")
                return True
            else:
                logger.error(f"Django email backend failed for {user.email}")
                return False
                
        except Exception as django_error:
            logger.error(f"Django email error: {str(django_error)}")
            
            # Last resort: Log for manual follow-up
            logger.critical(f"CRITICAL: Failed to send transaction notification to {user.email} for transaction {transaction_obj.id}. Manual intervention required.")
            return False
            
    except Exception as e:
        logger.error(f"Error in send_transaction_notification: {str(e)}", exc_info=True)
        return False


def send_security_alert(user, alert_type, details):
    """
    Send security alert via Gmail API
    
    Args:
        user (CustomUser): The user to alert
        alert_type (str): Type of security alert
        details (dict): Alert details
    """
    try:
        subject = f"Security Alert: {alert_type}"
        
        context = {
            'user_name': user.get_full_name(),
            'alert_type': alert_type,
            'details': details,
            'timestamp': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
        }
        
        # Use a security alert template (you'll need to create this)
        html_message = render_to_string('emails/security_alert.html', context)
        text_message = strip_tags(html_message)
        
        # Send via Gmail API for production
        if hasattr(settings, 'GMAIL_SENDER_EMAIL') and settings.GMAIL_SENDER_EMAIL:
            success, result = send_gmail(
                to_emails=[user.email],
                subject=subject,
                text_content=text_message,
                html_content=html_message,
                headers={'X-Alert-Type': alert_type}
            )
            
            if success:
                logger.info(f"Security alert sent to {user.email}: {alert_type}")
                return True
            else:
                logger.error(f"Failed to send security alert: {result}")
                
        # Fallback to Django backend
        email = EmailMessage(
            subject=f"{getattr(settings, 'GMAIL_SUBJECT_PREFIX', '[PrimeTrust] ')}{subject}",
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            headers={'X-Alert-Type': alert_type}
        )
        email.content_subtype = "html"
        return bool(email.send(fail_silently=False))
        
    except Exception as e:
        logger.error(f"Error sending security alert: {str(e)}", exc_info=True)
        return False


def send_welcome_email(user):
    """
    Send welcome email to new users via Gmail API
    
    Args:
        user (CustomUser): The new user
    """
    try:
        subject = "Welcome to PrimeTrust Banking!"
        
        context = {
            'user_name': user.get_full_name(),
            'user_email': user.email,
            'dashboard_url': f"{getattr(settings, 'SITE_URL', 'https://primetrust.com')}/dashboard/",
            'mobile_app_url': f"{getattr(settings, 'SITE_URL', 'https://primetrust.com')}/mobile/",
            'date': datetime.now().strftime('%B %d, %Y'),
        }
        
        html_message = render_to_string('emails/welcome_email.html', context)
        text_message = strip_tags(html_message)
        
        # Send via Gmail API (always use Gmail API for production)
        if hasattr(settings, 'GMAIL_SENDER_EMAIL') and settings.GMAIL_SENDER_EMAIL:
            success, result = send_gmail(
                to_emails=[user.email],
                subject=subject,
                text_content=text_message,
                html_content=html_message,
                headers={'X-Email-Type': 'welcome'}
            )
            
            if success:
                logger.info(f"Welcome email sent to {user.email}")
                return True
            else:
                logger.error(f"Failed to send welcome email: {result}")
                
        # Fallback to Django backend
        email = EmailMessage(
            subject=f"{getattr(settings, 'GMAIL_SUBJECT_PREFIX', '[PrimeTrust] ')}{subject}",
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            headers={'X-Email-Type': 'welcome'}
        )
        email.content_subtype = "html"
        return bool(email.send(fail_silently=False))
        
    except Exception as e:
        logger.error(f"Error sending welcome email: {str(e)}", exc_info=True)
        return False


def send_account_locked_notification(user, lock_reason, activity_details, unlock_url):
    """
    Send account locked notification via Gmail API
    
    Args:
        user (CustomUser): The user whose account is locked
        lock_reason (str): Reason for the lock
        activity_details (str): Details of suspicious activity
        unlock_url (str): URL to unlock the account
    """
    try:
        subject = "URGENT: Account Security Lock - Action Required"
        
        incident_reference = f"SEC-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
        
        context = {
            'user_name': user.get_full_name(),
            'lock_reason': lock_reason,
            'activity_details': activity_details,
            'unlock_url': unlock_url,
            'lock_timestamp': datetime.now().strftime('%B %d, %Y at %I:%M %p'),
            'expiration_time': datetime.now().strftime('%B %d, %Y at %I:%M %p'),  # Add 24 hours
            'incident_reference': incident_reference,
        }
        
        html_message = render_to_string('emails/account_locked.html', context)
        text_message = strip_tags(html_message)
        
        # Send via Gmail API (always use Gmail API for production)
        if hasattr(settings, 'GMAIL_SENDER_EMAIL') and settings.GMAIL_SENDER_EMAIL:
            success, result = send_gmail(
                to_emails=[user.email],
                subject=subject,
                text_content=text_message,
                html_content=html_message,
                headers={
                    'X-Email-Type': 'security-lock',
                    'X-Incident-Reference': incident_reference,
                    'X-Priority': 'high'
                }
            )
            
            if success:
                logger.critical(f"Account locked notification sent to {user.email}. Reference: {incident_reference}")
                return True
            else:
                logger.error(f"Failed to send account locked notification: {result}")
                
        # Fallback to Django backend
        email = EmailMessage(
            subject=f"{getattr(settings, 'GMAIL_SUBJECT_PREFIX', '[PrimeTrust] ')}{subject}",
            body=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
            headers={
                'X-Email-Type': 'security-lock',
                'X-Incident-Reference': incident_reference,
                'X-Priority': 'high'
            }
        )
        email.content_subtype = "html"
        return bool(email.send(fail_silently=False))
        
    except Exception as e:
        logger.error(f"Error sending account locked notification: {str(e)}", exc_info=True)
        return False
