"""
Production-Ready Security Models
Comprehensive security tracking, device management, and audit logging
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinLengthValidator
from encrypted_model_fields.fields import EncryptedTextField, EncryptedCharField
import uuid
import secrets
import hashlib
from datetime import timedelta

User = get_user_model()


class SecuritySettings(models.Model):
    """Enhanced security settings for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_settings')
    
    # 2FA Settings
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = EncryptedTextField(blank=True, null=True)
    two_factor_backup_tokens = EncryptedTextField(blank=True, null=True)  # JSON of backup codes
    two_factor_enabled_at = models.DateTimeField(null=True, blank=True)
    
    # Security Preferences
    login_notifications_enabled = models.BooleanField(default=True)
    transaction_notifications_enabled = models.BooleanField(default=True)
    security_alerts_enabled = models.BooleanField(default=True)
    
    # Password Policy
    password_last_changed = models.DateTimeField(auto_now_add=True)
    password_change_required = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    
    # Security Score Tracking
    security_score = models.PositiveIntegerField(default=0)
    security_score_updated = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Security Settings - {self.user.email}"
    
    def is_account_locked(self):
        """Check if account is currently locked"""
        if self.account_locked_until:
            return timezone.now() < self.account_locked_until
        return False
    
    def lock_account(self, minutes=30):
        """Lock account for specified minutes"""
        self.account_locked_until = timezone.now() + timedelta(minutes=minutes)
        self.save()
    
    def unlock_account(self):
        """Unlock account and reset failed attempts"""
        self.account_locked_until = None
        self.failed_login_attempts = 0
        self.save()


class UserDevice(models.Model):
    """Track and manage user devices for security"""
    DEVICE_TYPES = [
        ('web', 'Web Browser'),
        ('mobile', 'Mobile App'),
        ('tablet', 'Tablet'),
        ('desktop', 'Desktop Application'),
        ('api', 'API Client'),
    ]
    
    TRUST_LEVELS = [
        ('trusted', 'Trusted'),
        ('recognized', 'Recognized'),
        ('new', 'New Device'),
        ('suspicious', 'Suspicious'),
        ('blocked', 'Blocked'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_id = models.UUIDField(default=uuid.uuid4, unique=True)
    device_name = models.CharField(max_length=200)
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    
    # Device Fingerprinting
    user_agent = models.TextField()
    ip_address = models.GenericIPAddressField()
    browser_fingerprint = models.CharField(max_length=64, blank=True)  # Hash of browser characteristics
    screen_resolution = models.CharField(max_length=20, blank=True)
    timezone_offset = models.CharField(max_length=10, blank=True)
    
    # Geographic Information
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Security Status
    trust_level = models.CharField(max_length=20, choices=TRUST_LEVELS, default='new')
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(auto_now=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    
    # Authentication
    requires_2fa = models.BooleanField(default=True)
    trusted_until = models.DateTimeField(null=True, blank=True)  # Temporarily trusted
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_used']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['device_id']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        return f"{self.device_name} ({self.user.email})"
    
    def generate_fingerprint(self, request):
        """Generate device fingerprint from request"""
        fingerprint_data = f"{self.user_agent}{self.ip_address}{self.screen_resolution}{self.timezone_offset}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()
    
    def is_trusted(self):
        """Check if device is currently trusted"""
        if self.trust_level == 'trusted':
            return True
        if self.trusted_until and timezone.now() < self.trusted_until:
            return True
        return False
    
    def trust_device(self, hours=24):
        """Temporarily trust device for specified hours"""
        self.trusted_until = timezone.now() + timedelta(hours=hours)
        self.trust_level = 'recognized'
        self.save()


class SecurityEvent(models.Model):
    """Comprehensive audit logging for security events"""
    EVENT_TYPES = [
        ('login_success', 'Login Success'),
        ('login_failed', 'Login Failed'),
        ('login_blocked', 'Login Blocked'),
        ('logout', 'Logout'),
        ('password_changed', 'Password Changed'),
        ('2fa_enabled', '2FA Enabled'),
        ('2fa_disabled', '2FA Disabled'),
        ('2fa_failed', '2FA Verification Failed'),
        ('device_added', 'New Device Added'),
        ('device_trusted', 'Device Trusted'),
        ('device_blocked', 'Device Blocked'),
        ('suspicious_activity', 'Suspicious Activity'),
        ('account_locked', 'Account Locked'),
        ('account_unlocked', 'Account Unlocked'),
        ('transaction_pin_changed', 'Transaction PIN Changed'),
        ('profile_updated', 'Profile Updated'),
        ('api_access', 'API Access'),
        ('high_value_transaction', 'High Value Transaction'),
        ('failed_transaction', 'Failed Transaction'),
        ('multiple_failed_attempts', 'Multiple Failed Attempts'),
        ('geographic_anomaly', 'Geographic Anomaly'),
        ('session_expired', 'Session Expired'),
        ('backup_code_used', 'Backup Code Used'),
    ]
    
    RISK_LEVELS = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='security_events', null=True, blank=True)
    device = models.ForeignKey(UserDevice, on_delete=models.SET_NULL, null=True, blank=True)
    
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    risk_level = models.CharField(max_length=20, choices=RISK_LEVELS, default='low')
    
    # Event Details
    description = models.TextField()
    additional_data = models.JSONField(default=dict, blank=True)  # Store additional event context
    
    # Network Information
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # Geographic Information
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Outcome
    action_taken = models.CharField(max_length=200, blank=True)
    resolved = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'event_type']),
            models.Index(fields=['risk_level', 'resolved']),
            models.Index(fields=['created_at']),
            models.Index(fields=['ip_address']),
        ]
    
    def __str__(self):
        user_email = self.user.email if self.user else 'Anonymous'
        return f"{self.get_event_type_display()} - {user_email} ({self.created_at})"


class LoginAttempt(models.Model):
    """Track login attempts for brute force protection"""
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed_password', 'Failed Password'),
        ('failed_2fa', 'Failed 2FA'),
        ('account_locked', 'Account Locked'),
        ('blocked_ip', 'Blocked IP'),
        ('device_blocked', 'Device Blocked'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_attempts', null=True, blank=True)
    email = models.EmailField()  # Store even if user doesn't exist
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    # Device Information
    device = models.ForeignKey(UserDevice, on_delete=models.SET_NULL, null=True, blank=True)
    device_fingerprint = models.CharField(max_length=64, blank=True)
    
    # Geographic Information
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    
    # Failure Details
    failure_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'status']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.email} - {self.get_status_display()} ({self.created_at})"


class BackupCode(models.Model):
    """Secure storage for 2FA backup codes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='backup_codes')
    code_hash = models.CharField(max_length=128)  # Hashed backup code
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    used_from_ip = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'is_used']),
        ]
    
    def __str__(self):
        status = "Used" if self.is_used else "Active"
        return f"Backup Code - {self.user.email} ({status})"
    
    @classmethod
    def generate_codes(cls, user, count=10):
        """Generate backup codes for user"""
        codes = []
        for _ in range(count):
            # Generate 8-digit code
            code = ''.join([str(secrets.randbelow(10)) for _ in range(8)])
            formatted_code = f"{code[:4]}-{code[4:]}"
            
            # Hash and store
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            cls.objects.create(user=user, code_hash=code_hash)
            codes.append(formatted_code)
        
        return codes
    
    def verify_code(self, code):
        """Verify if provided code matches this backup code"""
        if self.is_used:
            return False
        
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        return self.code_hash == code_hash
    
    def use_code(self, ip_address=None):
        """Mark backup code as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.used_from_ip = ip_address
        self.save()


class SecurityRule(models.Model):
    """Configurable security rules for fraud detection"""
    RULE_TYPES = [
        ('transaction_amount', 'Transaction Amount Limit'),
        ('transaction_frequency', 'Transaction Frequency'),
        ('login_frequency', 'Login Frequency'),
        ('geographic_restriction', 'Geographic Restriction'),
        ('device_restriction', 'Device Restriction'),
        ('time_restriction', 'Time-based Restriction'),
        ('velocity_check', 'Velocity Check'),
    ]
    
    name = models.CharField(max_length=100)
    rule_type = models.CharField(max_length=30, choices=RULE_TYPES)
    description = models.TextField()
    
    # Rule Configuration (JSON)
    conditions = models.JSONField(default=dict)
    actions = models.JSONField(default=dict)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"


class RiskScore(models.Model):
    """Real-time risk scoring for users and transactions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='risk_scores')
    
    # Current Scores
    overall_risk_score = models.PositiveIntegerField(default=0)  # 0-100
    device_risk_score = models.PositiveIntegerField(default=0)
    behavioral_risk_score = models.PositiveIntegerField(default=0)
    geographic_risk_score = models.PositiveIntegerField(default=0)
    transaction_risk_score = models.PositiveIntegerField(default=0)
    
    # Risk Factors
    risk_factors = models.JSONField(default=list)  # List of active risk factors
    
    # Score History
    last_calculated = models.DateTimeField(auto_now=True)
    calculation_count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Risk Score - {self.user.email} (Score: {self.overall_risk_score})"
    
    def calculate_risk_score(self):
        """Calculate comprehensive risk score"""
        # This would contain sophisticated risk calculation algorithms
        # For now, implementing a basic version
        score = 0
        factors = []
        
        # Device risk (25% weight)
        device_score = self.calculate_device_risk()
        score += device_score * 0.25
        
        # Behavioral risk (25% weight)
        behavioral_score = self.calculate_behavioral_risk()
        score += behavioral_score * 0.25
        
        # Geographic risk (20% weight)
        geographic_score = self.calculate_geographic_risk()
        score += geographic_score * 0.20
        
        # Transaction risk (30% weight)
        transaction_score = self.calculate_transaction_risk()
        score += transaction_score * 0.30
        
        self.overall_risk_score = min(int(score), 100)
        self.device_risk_score = device_score
        self.behavioral_risk_score = behavioral_score
        self.geographic_risk_score = geographic_score
        self.transaction_risk_score = transaction_score
        self.risk_factors = factors
        self.calculation_count += 1
        self.save()
        
        return self.overall_risk_score
    
    def calculate_device_risk(self):
        """Calculate device-based risk score"""
        # Implementation would check device trust levels, new devices, etc.
        return 0
    
    def calculate_behavioral_risk(self):
        """Calculate behavioral risk score"""
        # Implementation would analyze user behavior patterns
        return 0
    
    def calculate_geographic_risk(self):
        """Calculate geographic risk score"""
        # Implementation would check for unusual locations
        return 0
    
    def calculate_transaction_risk(self):
        """Calculate transaction-based risk score"""
        # Implementation would analyze transaction patterns
        return 0 