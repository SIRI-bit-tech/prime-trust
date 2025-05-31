from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Transaction, Account
from .utils import send_notification

User = get_user_model()

@receiver(post_save, sender=Transaction)
def notify_transaction_created(sender, instance, created, **kwargs):
    """Send notification when a transaction is created"""
    if created:
        # Notify sender
        if instance.from_account and instance.from_account.user != instance.to_account.user:
            send_notification(
                user=instance.from_account.user,
                notification_type='transaction',
                title=f"Transaction Sent: {instance.amount} {instance.currency}",
                message=f"You sent {instance.amount} {instance.currency} to {instance.to_account.user.get_full_name() or instance.to_account.user.email}.",
                related_transaction=instance
            )
        
        # Notify recipient
        if instance.to_account and instance.to_account.user != instance.from_account.user:
            send_notification(
                user=instance.to_account.user,
                notification_type='transaction',
                title=f"Transaction Received: {instance.amount} {instance.currency}",
                message=f"You received {instance.amount} {instance.currency} from {instance.from_account.user.get_full_name() or instance.from_account.user.email}.",
                related_transaction=instance
            )

@receiver(post_save, sender=Account)
def notify_account_updated(sender, instance, created, **kwargs):
    """Send notification when an account is created or updated"""
    if created:
        send_notification(
            user=instance.user,
            notification_type='account',
            title=f"New {instance.get_account_type_display()} Account Created",
            message=f"Your new {instance.get_account_type_display()} account has been created successfully with account number {instance.account_number}."
        )
    # Add more conditions for specific account updates if needed
