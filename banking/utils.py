from django.contrib.auth import get_user_model
from .models import Notification
from django.db.models import Q

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
