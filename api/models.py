from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import URLValidator
import uuid
import json
from datetime import timedelta

User = get_user_model()

class WebhookEndpoint(models.Model):
    """
    Webhook endpoint configuration for external integrations
    """
    WEBHOOK_EVENTS = [
        # User Events
        ('user.created', 'User Created'),
        ('user.updated', 'User Updated'),
        ('user.deleted', 'User Deleted'),
        ('user.login', 'User Login'),
        ('user.logout', 'User Logout'),
        
        # Account Events
        ('account.created', 'Account Created'),
        ('account.updated', 'Account Updated'),
        ('account.frozen', 'Account Frozen'),
        ('account.unfrozen', 'Account Unfrozen'),
        ('account.closed', 'Account Closed'),
        
        # Transaction Events
        ('transaction.created', 'Transaction Created'),
        ('transaction.completed', 'Transaction Completed'),
        ('transaction.failed', 'Transaction Failed'),
        ('transaction.pending', 'Transaction Pending'),
        ('transaction.cancelled', 'Transaction Cancelled'),
        
        # Transfer Events
        ('transfer.initiated', 'Transfer Initiated'),
        ('transfer.completed', 'Transfer Completed'),
        ('transfer.failed', 'Transfer Failed'),
        
        # Payment Events
        ('payment.created', 'Payment Created'),
        ('payment.completed', 'Payment Completed'),
        ('payment.failed', 'Payment Failed'),
        
        # Investment Events
        ('investment.created', 'Investment Created'),
        ('investment.updated', 'Investment Updated'),
        ('investment.sold', 'Investment Sold'),
        
        # Loan Events
        ('loan.applied', 'Loan Application Submitted'),
        ('loan.approved', 'Loan Approved'),
        ('loan.rejected', 'Loan Rejected'),
        ('loan.disbursed', 'Loan Disbursed'),
        
        # Insurance Events
        ('insurance.purchased', 'Insurance Policy Purchased'),
        ('insurance.claim_filed', 'Insurance Claim Filed'),
        ('insurance.claim_approved', 'Insurance Claim Approved'),
        
        # Security Events
        ('security.suspicious_login', 'Suspicious Login Detected'),
        ('security.account_locked', 'Account Locked'),
        ('security.password_changed', 'Password Changed'),
        ('security.2fa_enabled', '2FA Enabled'),
        ('security.device_registered', 'New Device Registered'),
        
        # System Events
        ('system.maintenance', 'System Maintenance'),
        ('system.outage', 'System Outage'),
        ('system.update', 'System Update'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='webhook_endpoints')
    name = models.CharField(max_length=255, help_text="Descriptive name for this webhook")
    url = models.URLField(validators=[URLValidator()], help_text="The URL to POST webhook data to")
    events = models.JSONField(default=list, help_text="List of events this webhook should receive")
    secret = models.CharField(max_length=255, blank=True, help_text="Secret for webhook signature verification")
    is_active = models.BooleanField(default=True)
    
    # Configuration
    timeout_seconds = models.PositiveIntegerField(default=30, help_text="Timeout for webhook requests")
    max_retries = models.PositiveIntegerField(default=3, help_text="Maximum number of retry attempts")
    retry_delay_seconds = models.PositiveIntegerField(default=60, help_text="Initial delay between retries")
    email_notifications_enabled = models.BooleanField(default=False, help_text="Send email notifications for webhook events")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    # Statistics
    total_deliveries = models.PositiveIntegerField(default=0)
    successful_deliveries = models.PositiveIntegerField(default=0)
    failed_deliveries = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'api_webhook_endpoints'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.name} ({self.url})"
    
    @property
    def success_rate(self):
        if self.total_deliveries == 0:
            return 0
        return (self.successful_deliveries / self.total_deliveries) * 100
    
    def is_subscribed_to_event(self, event_type):
        return event_type in self.events


class WebhookEvent(models.Model):
    """
    Individual webhook events that can be sent to endpoints
    """
    EVENT_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100, choices=WebhookEndpoint.WEBHOOK_EVENTS)
    status = models.CharField(max_length=20, choices=EVENT_STATUS, default='pending')
    
    # Event data
    payload = models.JSONField(help_text="The actual event data to be sent")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Processing info
    delivery_attempts = models.PositiveIntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'api_webhook_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'status']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['next_retry_at']),
        ]
        
    def __str__(self):
        return f"{self.event_type} - {self.status}"
    
    def schedule_retry(self, delay_seconds=None):
        if delay_seconds is None:
            # Exponential backoff: 60s, 180s, 540s
            delay_seconds = 60 * (3 ** self.delivery_attempts)
        
        self.next_retry_at = timezone.now() + timedelta(seconds=delay_seconds)
        self.save()


class WebhookDelivery(models.Model):
    """
    Record of webhook delivery attempts
    """
    DELIVERY_STATUS = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook_endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    webhook_event = models.ForeignKey(WebhookEvent, on_delete=models.CASCADE, related_name='deliveries')
    
    # Delivery details
    status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='pending')
    http_status_code = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    
    # Request details
    request_headers = models.JSONField(default=dict)
    request_body = models.JSONField(default=dict)
    
    # Timing
    attempted_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    # Retry info
    attempt_number = models.PositiveIntegerField(default=1)
    is_retry = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'api_webhook_deliveries'
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['webhook_endpoint', 'status']),
            models.Index(fields=['webhook_event', 'attempt_number']),
            models.Index(fields=['attempted_at']),
        ]
        
    def __str__(self):
        return f"Delivery to {self.webhook_endpoint.name} - {self.status}"
    
    @property
    def is_successful(self):
        return self.status == 'success' and 200 <= (self.http_status_code or 0) <= 299


class WebhookSignature(models.Model):
    """
    Webhook signature verification keys and methods
    """
    SIGNATURE_METHODS = [
        ('hmac_sha256', 'HMAC SHA256'),
        ('hmac_sha512', 'HMAC SHA512'),
        ('jwt', 'JSON Web Token'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook_endpoint = models.OneToOneField(WebhookEndpoint, on_delete=models.CASCADE, related_name='signature')
    
    method = models.CharField(max_length=20, choices=SIGNATURE_METHODS, default='hmac_sha256')
    secret_key = models.CharField(max_length=512)
    
    # JWT specific
    algorithm = models.CharField(max_length=10, default='HS256', blank=True)
    issuer = models.CharField(max_length=255, blank=True)
    audience = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'api_webhook_signatures'
        
    def __str__(self):
        return f"Signature for {self.webhook_endpoint.name} ({self.method})"


class WebhookTemplate(models.Model):
    """
    Pre-defined webhook payload templates for different event types
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100, choices=WebhookEndpoint.WEBHOOK_EVENTS, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Template configuration
    payload_template = models.JSONField(help_text="Template for the webhook payload")
    headers_template = models.JSONField(default=dict, help_text="Additional headers to include")
    
    # Metadata
    is_active = models.BooleanField(default=True)
    version = models.CharField(max_length=10, default='1.0')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'api_webhook_templates'
        ordering = ['event_type']
        
    def __str__(self):
        return f"Template: {self.name}"
    
    def render_payload(self, context_data):
        """
        Render the payload template with actual event data
        """
        # Simple template rendering - in production, use a proper template engine
        payload = json.loads(json.dumps(self.payload_template))
        
        def replace_variables(obj, context):
            if isinstance(obj, dict):
                return {k: replace_variables(v, context) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_variables(item, context) for item in obj]
            elif isinstance(obj, str) and obj.startswith('{{') and obj.endswith('}}'):
                var_name = obj[2:-2].strip()
                return context.get(var_name, obj)
            return obj
        
        return replace_variables(payload, context_data)


class WebhookLog(models.Model):
    """
    Audit log for webhook operations
    """
    LOG_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('debug', 'Debug'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    webhook_endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, null=True, blank=True)
    webhook_event = models.ForeignKey(WebhookEvent, on_delete=models.CASCADE, null=True, blank=True)
    webhook_delivery = models.ForeignKey(WebhookDelivery, on_delete=models.CASCADE, null=True, blank=True)
    
    level = models.CharField(max_length=10, choices=LOG_LEVELS, default='info')
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'api_webhook_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['level', 'created_at']),
            models.Index(fields=['webhook_endpoint', 'created_at']),
        ]
        
    def __str__(self):
        return f"[{self.level.upper()}] {self.message[:50]}..."
