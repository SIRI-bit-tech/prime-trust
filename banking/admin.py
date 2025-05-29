from django.contrib import admin
from .models import Account, VirtualCard, Transaction, Notification
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

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'user__email')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Notification Details', {
            'fields': ('user', 'notification_type', 'title', 'message', 'is_read')
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

# Register loan and bill models
# Note: Models are registered using @admin.register decorator in admin_loans_bills.py
