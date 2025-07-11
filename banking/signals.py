from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Transaction, Account, BitcoinWallet
from .utils import send_notification
from accounts.models import CustomUser
import secrets
import hashlib

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
                title=f"Transaction Sent: {instance.amount}",
                message=f"You sent {instance.amount} to {instance.to_account.user.get_full_name() or instance.to_account.user.email}.",
                related_transaction=instance
            )
        
        # Notify recipient
        if instance.to_account and instance.to_account.user != instance.from_account.user:
            send_notification(
                user=instance.to_account.user,
                notification_type='transaction',
                title=f"Transaction Received: {instance.amount}",
                message=f"You received {instance.amount} from {instance.from_account.user.get_full_name() or instance.from_account.user.email}.",
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

@receiver(post_save, sender=CustomUser)
def create_user_accounts(sender, instance, created, **kwargs):
    """Create accounts for new users"""
    if created:
        import uuid
        
        # Create a single checking account with a unique account number
        account = Account.objects.create(
            user=instance,
            account_number=f"PT{uuid.uuid4().hex[:8].upper()}",
            account_type='checking',
            balance=0.00
        )
        
        # Trigger webhook event for account creation
        try:
            from api.webhook_delivery import trigger_account_created
            trigger_account_created(account)
        except Exception as webhook_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to trigger account_created webhook for {instance.email}: {str(webhook_error)}")
        
        # Create Bitcoin wallet with a unique address
        wallet_seed = secrets.token_bytes(32)
        wallet_address = hashlib.sha256(wallet_seed).hexdigest()
        BitcoinWallet.objects.create(
            user=instance,
            address=wallet_address
        )
