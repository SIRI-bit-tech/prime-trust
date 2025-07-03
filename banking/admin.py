from django import forms
from django.contrib import admin
from django.utils.html import format_html
from .models import Account, VirtualCard, Transaction, Notification, BitcoinWallet
from .models_loans import LoanApplication, LoanAccount, LoanPayment
from .models_bills import Biller, BillPayment, Payee, ScheduledPayment
from .admin_loans_bills import *
from .admin_investments_insurance import *

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'user', 'account_type', 'balance', 'created_at')
    list_filter = ('account_type', 'created_at')
    search_fields = ('account_number', 'user__email')
    readonly_fields = ('account_number', 'routing_number', 'created_at', 'updated_at')
    fieldsets = (
        ('Account Information', {
            'fields': ('user', 'account_number', 'routing_number', 'account_type', 'balance')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(VirtualCard)
class VirtualCardAdmin(admin.ModelAdmin):
    list_display = ('card_number_masked', 'card_type', 'expiry_date', 'is_active')
    list_filter = ('card_type', 'is_active', 'expiry_date')
    search_fields = ('card_number', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    def card_number_masked(self, obj):
        return f"**** **** **** {obj.card_number[-4:]}"
    card_number_masked.short_description = 'Card Number'
    
    fieldsets = (
        ('Card Information', {
            'fields': ('user', 'card_number', 'card_type', 'expiry_date', 'cvv', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'from_account', 'to_account', 'amount', 'transaction_type', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('reference', 'from_account__account_number', 'to_account__account_number')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    fieldsets = (
        ('Transaction Information', {
            'fields': ('reference', 'transaction_type', 'status')
        }),
        ('Accounts', {
            'fields': ('from_account', 'to_account')
        }),
        ('Amount & Details', {
            'fields': ('amount', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

class NotificationForm(forms.ModelForm):
    send_to_all = forms.BooleanField(
        label='Send to all users',
        required=False,
        help_text='If checked, this notification will be sent to all active users.'
    )
    
    class Meta:
        model = Notification
        fields = '__all__'

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    form = NotificationForm
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__email')
    readonly_fields = ('created_at',)
    actions = ['mark_as_read', 'mark_as_unread', 'resend_notification']
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'notification_type', 'title', 'message', 'is_read')
        }),
        ('Batch Sending', {
            'fields': ('send_to_all',),
            'classes': ('collapse',),
            'description': 'Use these options to send notifications to multiple users.'
        }),
        ('Related Transaction', {
            'fields': ('related_transaction',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        from .utils import send_notification
        
        if not change and form.cleaned_data.get('send_to_all'):
            # If this is a new notification and 'send to all' is checked
            obj.save()  # Save the original instance first
            send_notification(
                user='all',
                notification_type=obj.notification_type,
                title=obj.title,
                message=obj.message,
                related_transaction=obj.related_transaction
            )
            return
        
        # For normal saves
        super().save_model(request, obj, form, change)
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"Marked {updated} notifications as read.")
    mark_as_read.short_description = "Mark selected notifications as read"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"Marked {updated} notifications as unread.")
    mark_as_unread.short_description = "Mark selected notifications as unread"
    
    def resend_notification(self, request, queryset):
        from .utils import send_notification
        
        count = 0
        for notification in queryset:
            send_notification(
                user=notification.user,
                notification_type=notification.notification_type,
                title=notification.title,
                message=notification.message,
                related_transaction=notification.related_transaction
            )
            count += 1
            
        self.message_user(request, f"Resent {count} notifications.")
    resend_notification.short_description = "Resend selected notifications"

# Register loan and bill models
# Note: Models are registered using @admin.register decorator in admin_loans_bills.py

@admin.register(BitcoinWallet)
class BitcoinWalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'address', 'balance', 'is_active', 'qr_code_preview')
    search_fields = ('user__email', 'address')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('balance', 'btc_price_usd', 'created_at', 'updated_at', 'qr_code_preview')
    fields = ('user', 'address', 'qr_code', 'qr_code_preview', 'is_active', 'balance', 'btc_price_usd', 'created_at', 'updated_at')
    
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50" />', obj.qr_code.url)
        return "No QR code"
    qr_code_preview.short_description = 'QR Code'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only for new wallets
            obj.is_active = True
        super().save_model(request, obj, form, change)

# All these models are already registered elsewhere in the project
# admin.site.register(Account)
# admin.site.register(Transaction)
# admin.site.register(Notification)
# admin.site.register(VirtualCard)
