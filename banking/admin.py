from django.contrib import admin
from .models import Account, VirtualCard, Transaction, Notification

class AccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'user', 'account_type', 'balance', 'created_at')
    list_filter = ('account_type',)
    search_fields = ('account_number', 'user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')

class VirtualCardAdmin(admin.ModelAdmin):
    list_display = ('card_number', 'user', 'card_type', 'expiry_date', 'is_active')
    list_filter = ('card_type', 'is_active')
    search_fields = ('card_number', 'user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('reference', 'transaction_type', 'amount', 'status', 'created_at')
    list_filter = ('transaction_type', 'status')
    search_fields = ('reference', 'description', 'from_account__account_number', 'to_account__account_number')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('reference', 'transaction_type', 'amount', 'status', 'description')
        }),
        ('Accounts', {
            'fields': ('from_account', 'to_account')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__email', 'title', 'message')
    readonly_fields = ('created_at',)

admin.site.register(Account, AccountAdmin)
admin.site.register(VirtualCard, VirtualCardAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Notification, NotificationAdmin)
