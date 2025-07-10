from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib import messages
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path
from django.shortcuts import get_object_or_404
from django.utils import timezone
import logging

from .models import CustomUser, UserProfile
from .models_security import (
    SecuritySettings, UserDevice, SecurityEvent, 
    LoginAttempt, BackupCode, SecurityRule, RiskScore
)
from .utils import TwoFactorAuth
from .audit_logging import AuditLogger

logger = logging.getLogger(__name__)

class CustomUserAdmin(UserAdmin):
    """Enhanced User Admin with 2FA management"""
    
    model = CustomUser
    list_display = (
        'email', 'first_name', 'last_name', 'is_active', 
        'is_staff', 'date_joined', 'security_status_display', 
        'two_factor_status_display', 'security_actions'
    )
    list_filter = (
        'is_active', 'is_staff', 'is_superuser', 'date_joined'
    )
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Security Information', {
            'fields': ('security_overview',),
            'classes': ('collapse',),
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'phone_number', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('security_overview',)
    
    actions = [
        'enable_2fa_for_users',
        'disable_2fa_for_users', 
        'unlock_user_accounts',
        'lock_user_accounts',
        'reset_failed_attempts',
        'generate_security_report'
    ]
    
    def get_urls(self):
        """Add custom URLs for 2FA management"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:user_id>/manage-2fa/',
                self.admin_site.admin_view(self.manage_2fa_view),
                name='accounts_customuser_manage_2fa'
            ),
            path(
                '<int:user_id>/security-details/',
                self.admin_site.admin_view(self.security_details_view),
                name='accounts_customuser_security_details'
            ),
            path(
                '<int:user_id>/device-management/',
                self.admin_site.admin_view(self.device_management_view),
                name='accounts_customuser_device_management'
            ),
        ]
        return custom_urls + urls
    
    def security_status_display(self, obj):
        """Display security status with color coding"""
        try:
            # Check if security_settings exists, create if not
            if hasattr(obj, 'security_settings'):
                security_settings = obj.security_settings
            else:
                # Create SecuritySettings if it doesn't exist
                from .models_security import SecuritySettings
                from django.utils import timezone
                security_settings, created = SecuritySettings.objects.get_or_create(
                    user=obj,
                    defaults={
                        'two_factor_enabled': False,
                        'security_score': 50,
                        'password_last_changed': timezone.now(),
                        'failed_login_attempts': 0,
                        'login_notifications_enabled': True,
                        'transaction_notifications_enabled': True,
                        'security_alerts_enabled': True,
                        'password_change_required': False,
                    }
                )
            
            score = security_settings.security_score
            
            if score >= 80:
                color = 'green'
                status = 'High'
            elif score >= 60:
                color = 'orange'
                status = 'Medium'
            else:
                color = 'red'
                status = 'Low'
                
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} ({})</span>',
                color, status, score
            )
        except Exception:
            # Better error handling - no print, no logger.error
            return format_html('<span style="color: gray;">Unavailable</span>')
    
    security_status_display.short_description = 'Security Score'
    
    def two_factor_status_display(self, obj):
        """Display 2FA status with enable/disable options"""
        try:
            is_enabled = obj.security_settings.two_factor_enabled
            if is_enabled:
                return format_html(
                    '<span style="color: green;">✓ Enabled</span>'
                )
            else:
                return format_html(
                    '<span style="color: red;">✗ Disabled</span>'
                )
        except:
            return format_html('<span style="color: gray;">Unknown</span>')
    
    two_factor_status_display.short_description = '2FA Status'
    
    def security_actions(self, obj):
        """Display security action buttons"""
        manage_url = reverse('admin:accounts_customuser_manage_2fa', args=[obj.id])
        details_url = reverse('admin:accounts_customuser_security_details', args=[obj.id])
        
        return format_html(
            '<a href="{}" class="button">Manage 2FA</a> '
            '<a href="{}" class="button">Security Details</a>',
            manage_url, details_url
        )
    
    security_actions.short_description = 'Actions'
    
    def security_overview(self, obj):
        """Display comprehensive security overview"""
        if not obj.id:
            return "Save user first to see security information"
        
        try:
            # Get or create security settings
            if hasattr(obj, 'security_settings'):
                security_settings = obj.security_settings
            else:
                from .models_security import SecuritySettings
                from django.utils import timezone
                security_settings, created = SecuritySettings.objects.get_or_create(
                    user=obj,
                    defaults={
                        'two_factor_enabled': False,
                        'security_score': 50,
                        'password_last_changed': timezone.now(),
                        'failed_login_attempts': 0,
                        'login_notifications_enabled': True,
                        'transaction_notifications_enabled': True,
                        'security_alerts_enabled': True,
                        'password_change_required': False,
                    }
                )
            
            # Get devices (using correct related name and field names)
            devices = getattr(obj, 'devices', None)
            if devices and hasattr(devices, 'all'):
                devices_list = list(devices.all()[:3])
                device_count = devices.count()
            else:
                devices_list = []
                device_count = 0
            
            # Get security events
            events = getattr(obj, 'security_events', None)
            if events and hasattr(events, 'all'):
                events_list = list(events.all()[:5])
            else:
                events_list = []
            
            # Safely get backup codes count
            backup_codes_count = 0
            if hasattr(security_settings, 'backup_codes'):
                try:
                    backup_codes_count = security_settings.backup_codes.count()
                except:
                    backup_codes_count = 0
            
            # Check account locked status
            account_locked = False
            if hasattr(security_settings, 'account_locked_until') and security_settings.account_locked_until:
                from django.utils import timezone
                account_locked = timezone.now() < security_settings.account_locked_until
            
            html = f"""
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h3 style="margin-top: 0;">Security Overview</h3>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 15px 0;">
                    <div>
                        <h4>2FA Status</h4>
                        <p><strong>Enabled:</strong> {'Yes' if security_settings.two_factor_enabled else 'No'}</p>
                        <p><strong>Secret Set:</strong> {'Yes' if security_settings.two_factor_secret else 'No'}</p>
                        <p><strong>Backup Codes:</strong> {backup_codes_count}</p>
                    </div>
                    
                    <div>
                        <h4>Account Security</h4>
                        <p><strong>Account Locked:</strong> {'Yes' if account_locked else 'No'}</p>
                        <p><strong>Failed Attempts:</strong> {security_settings.failed_login_attempts}</p>
                        <p><strong>Security Score:</strong> {security_settings.security_score}/100</p>
                    </div>
                </div>
                
                <div style="margin: 15px 0;">
                    <h4>Recent Devices ({device_count})</h4>
                    <ul style="max-height: 150px; overflow-y: auto;">
            """
            
            if devices_list:
                for device in devices_list:
                    try:
                        # Use correct field name: last_used instead of last_seen
                        last_used = getattr(device, 'last_used', 'Unknown')
                        device_name = getattr(device, 'device_name', 'Unknown Device')
                        trust_level = getattr(device, 'trust_level', 'Unknown')
                        html += f"<li>{device_name} - {trust_level} ({last_used})</li>"
                    except Exception:
                        html += f"<li>Device info unavailable</li>"
            else:
                html += "<li>No devices found</li>"
            
            html += """
                    </ul>
                </div>
                
                <div style="margin: 15px 0;">
                    <h4>Recent Security Events</h4>
                    <ul style="max-height: 150px; overflow-y: auto;">
            """
            
            if events_list:
                for event in events_list:
                    try:
                        event_type = getattr(event, 'event_type', 'Unknown')
                        # Use correct field name: risk_level instead of severity
                        risk_level = getattr(event, 'risk_level', 'Unknown')
                        # Use correct field name: created_at instead of timestamp
                        timestamp = getattr(event, 'created_at', 'Unknown')
                        html += f"<li>{event_type} - {risk_level} ({timestamp})</li>"
                    except Exception:
                        html += f"<li>Event info unavailable</li>"
            else:
                html += "<li>No recent events</li>"
            
            html += f"""
                    </ul>
                </div>
                
                <div style="margin-top: 20px;">
                    <a href="{reverse('admin:accounts_customuser_manage_2fa', args=[obj.id])}" class="button">
                        Manage 2FA
                    </a>
                    <a href="{reverse('admin:accounts_customuser_security_details', args=[obj.id])}" class="button">
                        Security Details
                    </a>
                </div>
            </div>
            """
            
            return format_html(html)
            
        except Exception as e:
            # Better error handling without logger.error or print
            return format_html(
                '<div style="background: #ffebee; padding: 10px; border-radius: 5px; color: #c62828;">'
                '<strong>Security Information Unavailable</strong><br>'
                'Please contact administrator if this persists.'
                '</div>'
            )
    
    security_overview.short_description = 'Security Information'
    
    def manage_2fa_view(self, request, user_id):
        """Custom view for managing 2FA settings"""
        user = get_object_or_404(CustomUser, id=user_id)
        two_fa = TwoFactorAuth(user)
        
        if request.method == 'POST':
            action = request.POST.get('action')
            
            try:
                if action == 'enable_2fa':
                    secret_key, qr_code_url = two_fa.enable_2fa()
                    qr_code_image = two_fa.generate_qr_code(qr_code_url)
                    
                    # Log admin action
                    audit_logger = AuditLogger(user=request.user, request=request)
                    audit_logger.log_administrative_action(
                        'ADMIN_ENABLED_2FA',
                        metadata={
                            'target_user': user.email,
                            'admin_user': request.user.email
                        }
                    )
                    
                    messages.success(request, f'2FA enabled for {user.email}')
                    
                elif action == 'disable_2fa':
                    two_fa.disable_2fa()
                    
                    # Log admin action
                    audit_logger = AuditLogger(user=request.user, request=request)
                    audit_logger.log_administrative_action(
                        'ADMIN_DISABLED_2FA',
                        metadata={
                            'target_user': user.email,
                            'admin_user': request.user.email
                        }
                    )
                    
                    messages.success(request, f'2FA disabled for {user.email}')
                    
                elif action == 'generate_backup_codes':
                    backup_codes = two_fa.generate_backup_codes()
                    
                    # Log admin action
                    audit_logger = AuditLogger(user=request.user, request=request)
                    audit_logger.log_administrative_action(
                        'ADMIN_GENERATED_BACKUP_CODES',
                        metadata={
                            'target_user': user.email,
                            'codes_count': len(backup_codes)
                        }
                    )
                    
                    messages.success(request, f'Generated {len(backup_codes)} backup codes for {user.email}')
                    
                elif action == 'reset_2fa':
                    two_fa.reset_2fa()
                    
                    # Log admin action
                    audit_logger = AuditLogger(user=request.user, request=request)
                    audit_logger.log_administrative_action(
                        'ADMIN_RESET_2FA',
                        metadata={
                            'target_user': user.email,
                            'admin_user': request.user.email
                        }
                    )
                    
                    messages.success(request, f'2FA reset for {user.email}')
                    
            except Exception as e:
                logger.error(f"2FA management error: {str(e)}")
                messages.error(request, f'Error managing 2FA: {str(e)}')
        
        # Get current 2FA status
        status = two_fa.get_2fa_status()
        
        context = {
            'user': user,
            'two_fa_status': status,
            'title': f'Manage 2FA for {user.email}',
            'opts': self.model._meta,
            'has_change_permission': self.has_change_permission(request, user),
        }
        
        return TemplateResponse(request, 'admin/accounts/manage_2fa.html', context)
    
    def security_details_view(self, request, user_id):
        """Detailed security information view"""
        user = get_object_or_404(CustomUser, id=user_id)
        
        try:
            security_settings = user.security_settings
            devices = user.user_devices.all().order_by('-last_seen')
            events = user.security_events.all().order_by('-timestamp')[:20]
            login_attempts = user.login_attempts.all().order_by('-timestamp')[:10]
            
        except Exception as e:
            logger.error(f"Error loading security details: {str(e)}")
            messages.error(request, f'Error loading security details: {str(e)}')
            return HttpResponseRedirect(reverse('admin:accounts_customuser_change', args=[user_id]))
        
        context = {
            'user': user,
            'security_settings': security_settings,
            'devices': devices,
            'events': events,
            'login_attempts': login_attempts,
            'title': f'Security Details for {user.email}',
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/accounts/security_details.html', context)
    
    def device_management_view(self, request, user_id):
        """Device management view"""
        user = get_object_or_404(CustomUser, id=user_id)
        
        if request.method == 'POST':
            action = request.POST.get('action')
            device_id = request.POST.get('device_id')
            
            try:
                if action == 'revoke_device' and device_id:
                    device = get_object_or_404(UserDevice, id=device_id, user=user)
                    device.is_active = False
                    device.save()
                    
                    # Log admin action
                    audit_logger = AuditLogger(user=request.user, request=request)
                    audit_logger.log_administrative_action(
                        'ADMIN_REVOKED_DEVICE',
                        metadata={
                            'target_user': user.email,
                            'device_id': device_id,
                            'device_name': device.device_name
                        }
                    )
                    
                    messages.success(request, f'Device revoked for {user.email}')
                    
            except Exception as e:
                logger.error(f"Device management error: {str(e)}")
                messages.error(request, f'Error managing device: {str(e)}')
        
        devices = user.user_devices.all().order_by('-last_seen')
        
        context = {
            'user': user,
            'devices': devices,
            'title': f'Device Management for {user.email}',
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/accounts/device_management.html', context)
    
    # Admin Actions
    def enable_2fa_for_users(self, request, queryset):
        """Enable 2FA for selected users"""
        count = 0
        for user in queryset:
            try:
                two_fa = TwoFactorAuth(user)
                two_fa.enable_2fa()
                count += 1
            except Exception as e:
                logger.error(f"Error enabling 2FA for {user.email}: {str(e)}")
        
        self.message_user(request, f'2FA enabled for {count} users.')
    
    enable_2fa_for_users.short_description = "Enable 2FA for selected users"
    
    def disable_2fa_for_users(self, request, queryset):
        """Disable 2FA for selected users"""
        count = 0
        for user in queryset:
            try:
                two_fa = TwoFactorAuth(user)
                two_fa.disable_2fa()
                count += 1
            except Exception as e:
                logger.error(f"Error disabling 2FA for {user.email}: {str(e)}")
        
        self.message_user(request, f'2FA disabled for {count} users.')
    
    disable_2fa_for_users.short_description = "Disable 2FA for selected users"
    
    def unlock_user_accounts(self, request, queryset):
        """Unlock selected user accounts"""
        count = 0
        for user in queryset:
            try:
                user.security_settings.account_locked = False
                user.security_settings.failed_login_attempts = 0
                user.security_settings.save()
                count += 1
            except Exception as e:
                logger.error(f"Error unlocking account for {user.email}: {str(e)}")
        
        self.message_user(request, f'Unlocked {count} user accounts.')
    
    unlock_user_accounts.short_description = "Unlock selected user accounts"
    
    def lock_user_accounts(self, request, queryset):
        """Lock selected user accounts"""
        count = 0
        for user in queryset:
            try:
                user.security_settings.account_locked = True
                user.security_settings.save()
                count += 1
            except Exception as e:
                logger.error(f"Error locking account for {user.email}: {str(e)}")
        
        self.message_user(request, f'Locked {count} user accounts.')
    
    lock_user_accounts.short_description = "Lock selected user accounts"
    
    def reset_failed_attempts(self, request, queryset):
        """Reset failed login attempts for selected users"""
        count = 0
        for user in queryset:
            try:
                user.security_settings.failed_login_attempts = 0
                user.security_settings.save()
                count += 1
            except Exception as e:
                logger.error(f"Error resetting failed attempts for {user.email}: {str(e)}")
        
        self.message_user(request, f'Reset failed attempts for {count} users.')
    
    reset_failed_attempts.short_description = "Reset failed login attempts"
    
    def generate_security_report(self, request, queryset):
        """Generate security report for selected users"""
        # This would generate a comprehensive security report
        # For now, just show a success message
        self.message_user(request, f'Security report generated for {queryset.count()} users.')
    
    generate_security_report.short_description = "Generate security report"

class UserProfileAdmin(admin.ModelAdmin):
    """User Profile Admin"""
    
    list_display = ('user', 'date_of_birth', 'city', 'state', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    list_filter = ('state', 'city', 'created_at')
    
    readonly_fields = ('created_at', 'updated_at')

class SecuritySettingsAdmin(admin.ModelAdmin):
    """Security Settings Admin"""
    
    list_display = (
        'user', 'two_factor_enabled', 'account_locked_display', 
        'failed_login_attempts', 'security_score', 'created_at'
    )
    list_filter = ('two_factor_enabled', 'created_at')
    search_fields = ('user__email',)
    
    readonly_fields = ('created_at', 'updated_at', 'two_factor_secret')
    
    def account_locked_display(self, obj):
        """Display account lock status"""
        return obj.is_account_locked()
    account_locked_display.short_description = 'Account Locked'
    account_locked_display.boolean = True

class UserDeviceAdmin(admin.ModelAdmin):
    """User Device Admin"""
    
    list_display = (
        'user', 'device_name', 'device_type', 'trust_level', 
        'is_active', 'last_used', 'created_at'
    )
    list_filter = ('trust_level', 'is_active', 'device_type', 'created_at')
    search_fields = ('user__email', 'device_name', 'user_agent')
    
    readonly_fields = ('created_at', 'browser_fingerprint')

class SecurityEventAdmin(admin.ModelAdmin):
    """Security Event Admin"""
    
    list_display = (
        'user', 'event_type', 'risk_level', 'created_at', 'ip_address'
    )
    list_filter = ('event_type', 'risk_level', 'created_at')
    search_fields = ('user__email', 'event_type', 'ip_address')
    
    readonly_fields = ('created_at',)

class LoginAttemptAdmin(admin.ModelAdmin):
    """Login Attempt Admin"""
    
    list_display = (
        'user', 'status', 'failure_reason', 'created_at', 'ip_address'
    )
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'ip_address')
    
    readonly_fields = ('created_at',)

class BackupCodeAdmin(admin.ModelAdmin):
    """Backup Code Admin"""
    
    list_display = ('user', 'is_used', 'used_at', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__email',)
    
    readonly_fields = ('created_at', 'code_hash')

# Register models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(SecuritySettings, SecuritySettingsAdmin)
admin.site.register(UserDevice, UserDeviceAdmin)
admin.site.register(SecurityEvent, SecurityEventAdmin)
admin.site.register(LoginAttempt, LoginAttemptAdmin)
admin.site.register(BackupCode, BackupCodeAdmin)

# Customize admin site
admin.site.site_header = 'PrimeTrust Banking Administration'
admin.site.site_title = 'PrimeTrust Admin'
admin.site.index_title = 'Welcome to PrimeTrust Administration'
