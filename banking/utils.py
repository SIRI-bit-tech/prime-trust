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

logger = logging.getLogger(__name__)

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
    Send transaction notification email for production
    
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
            subject = f"PrimeTrust: Money Sent - ${formatted_amount}"
        else:
            transaction_message = f"You just received ${formatted_amount} from {transaction_obj.from_account.user.get_full_name()}"
            subject = f"PrimeTrust: Money Received - ${formatted_amount}"
        
        # Get the logo URL
        logo_url = f"{settings.SITE_URL}/static/img/Primetrust-logo-med.png"
        
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
        
        try:
            # Create and send email
            email = EmailMessage(
                subject=subject,
                body=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
                headers={'X-Entity-Ref-ID': str(transaction_obj.id)}
            )
            email.content_subtype = "html"
            
            # Send immediately in production
            email.send(fail_silently=False)
            
            logger.info(f"Transaction notification email sent successfully to {user.email} for transaction {transaction_obj.id}")
            return True
            
        except SMTPException as smtp_error:
            logger.error(f"SMTP Error sending transaction email to {user.email}: {str(smtp_error)}")
            # Attempt retry logic here if needed
            raise
            
    except Exception as e:
        logger.error(f"Error in send_transaction_notification: {str(e)}", exc_info=True)
        return False
