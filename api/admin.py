from django.contrib import admin
from .models import (
    WebhookEndpoint, WebhookEvent, WebhookDelivery, 
    WebhookSignature, WebhookTemplate, WebhookLog
)

@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'user', 'is_active', 'success_rate', 'total_deliveries', 'created_at']
    list_filter = ['is_active', 'created_at', 'events']
    search_fields = ['name', 'url', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_used_at', 'total_deliveries', 
                      'successful_deliveries', 'failed_deliveries', 'success_rate']
    fieldsets = [
        ('Basic Information', {
            'fields': ['id', 'user', 'name', 'url', 'is_active']
        }),
        ('Event Configuration', {
            'fields': ['events', 'secret']
        }),
        ('Delivery Settings', {
            'fields': ['timeout_seconds', 'max_retries', 'retry_delay_seconds']
        }),
        ('Statistics', {
            'fields': ['total_deliveries', 'successful_deliveries', 'failed_deliveries', 'success_rate'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at', 'last_used_at'],
            'classes': ['collapse']
        })
    ]
    
    def success_rate(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate.short_description = 'Success Rate'


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'status', 'user', 'delivery_attempts', 'created_at', 'next_retry_at']
    list_filter = ['event_type', 'status', 'created_at']
    search_fields = ['event_type', 'user__email']
    readonly_fields = ['id', 'created_at', 'processed_at']
    fieldsets = [
        ('Event Information', {
            'fields': ['id', 'event_type', 'status', 'user']
        }),
        ('Payload Data', {
            'fields': ['payload'],
            'classes': ['collapse']
        }),
        ('Processing Info', {
            'fields': ['delivery_attempts', 'next_retry_at']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'processed_at']
        })
    ]
    
    actions = ['retry_failed_events', 'cancel_pending_events']
    
    def retry_failed_events(self, request, queryset):
        count = 0
        for event in queryset.filter(status='failed'):
            event.status = 'pending'
            event.schedule_retry()
            count += 1
        self.message_user(request, f'{count} events scheduled for retry.')
    retry_failed_events.short_description = 'Retry selected failed events'
    
    def cancel_pending_events(self, request, queryset):
        count = queryset.filter(status='pending').update(status='cancelled')
        self.message_user(request, f'{count} events cancelled.')
    cancel_pending_events.short_description = 'Cancel selected pending events'


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ['webhook_endpoint', 'webhook_event', 'status', 'http_status_code', 
                   'attempt_number', 'response_time_ms', 'attempted_at']
    list_filter = ['status', 'http_status_code', 'attempted_at', 'is_retry']
    search_fields = ['webhook_endpoint__name', 'webhook_event__event_type']
    readonly_fields = ['id', 'attempted_at', 'completed_at', 'is_successful']
    fieldsets = [
        ('Delivery Information', {
            'fields': ['id', 'webhook_endpoint', 'webhook_event', 'status', 'attempt_number', 'is_retry']
        }),
        ('Response Details', {
            'fields': ['http_status_code', 'response_body', 'error_message', 'response_time_ms']
        }),
        ('Request Details', {
            'fields': ['request_headers', 'request_body'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['attempted_at', 'completed_at']
        })
    ]
    
    def is_successful(self, obj):
        return obj.is_successful
    is_successful.boolean = True
    is_successful.short_description = 'Successful'


@admin.register(WebhookSignature)
class WebhookSignatureAdmin(admin.ModelAdmin):
    list_display = ['webhook_endpoint', 'method', 'algorithm', 'created_at']
    list_filter = ['method', 'algorithm', 'created_at']
    search_fields = ['webhook_endpoint__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = [
        ('Signature Configuration', {
            'fields': ['id', 'webhook_endpoint', 'method', 'secret_key']
        }),
        ('JWT Configuration', {
            'fields': ['algorithm', 'issuer', 'audience'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at']
        })
    ]


@admin.register(WebhookTemplate)
class WebhookTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'event_type', 'version', 'is_active', 'created_at']
    list_filter = ['event_type', 'is_active', 'version', 'created_at']
    search_fields = ['name', 'event_type', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    fieldsets = [
        ('Template Information', {
            'fields': ['id', 'event_type', 'name', 'description', 'version', 'is_active']
        }),
        ('Template Configuration', {
            'fields': ['payload_template', 'headers_template']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at']
        })
    ]


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    list_display = ['level', 'message_preview', 'webhook_endpoint', 'webhook_event', 'created_at']
    list_filter = ['level', 'created_at']
    search_fields = ['message', 'webhook_endpoint__name', 'webhook_event__event_type']
    readonly_fields = ['id', 'created_at']
    fieldsets = [
        ('Log Information', {
            'fields': ['id', 'level', 'message']
        }),
        ('Related Objects', {
            'fields': ['webhook_endpoint', 'webhook_event', 'webhook_delivery']
        }),
        ('Additional Details', {
            'fields': ['details'],
            'classes': ['collapse']
        }),
        ('Timestamp', {
            'fields': ['created_at']
        })
    ]
    
    def message_preview(self, obj):
        return obj.message[:50] + ('...' if len(obj.message) > 50 else '')
    message_preview.short_description = 'Message'
    
    actions = ['clear_old_logs']
    
    def clear_old_logs(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        # Delete logs older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        count = queryset.filter(created_at__lt=cutoff_date).delete()[0]
        self.message_user(request, f'{count} old log entries deleted.')
    clear_old_logs.short_description = 'Clear logs older than 30 days'
