from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from decimal import Decimal
from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
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

class AddBitcoinBalanceForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=20,
        decimal_places=8,
        min_value=Decimal('0.00000001'),
        label='Bitcoin Amount to Add',
        help_text='Enter the amount of Bitcoin to add to this wallet (up to 8 decimal places)',
        widget=forms.NumberInput(attrs={
            'step': '0.00000001',
            'placeholder': '0.00000000',
            'class': 'form-control'
        })
    )
    reason = forms.CharField(
        max_length=200,
        required=False,
        label='Reason (Optional)',
        help_text='Optional reason for adding this balance',
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., User deposit, Bonus credit, Manual adjustment',
            'class': 'form-control'
        })
    )

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
    list_display = ('user', 'address', 'balance', 'balance_usd', 'is_active', 'qr_code_preview', 'add_balance_link')
    search_fields = ('user__email', 'address')
    list_filter = ('is_active', 'created_at')
    readonly_fields = ('btc_price_usd', 'created_at', 'updated_at', 'qr_code_preview', 'balance_usd', 'add_balance_link')
    fields = ('user', 'address', 'qr_code', 'qr_code_preview', 'is_active', 'balance', 'balance_usd', 'btc_price_usd', 'created_at', 'updated_at', 'add_balance_link')
    actions = ['add_bitcoin_balance_bulk', 'activate_wallets', 'deactivate_wallets']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:wallet_id>/add-balance/',
                self.admin_site.admin_view(self.add_balance_view),
                name='banking_bitcoinwallet_add_balance',
            ),
        ]
        return custom_urls + urls
    
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50" />', obj.qr_code.url)
        return "No QR code"
    qr_code_preview.short_description = 'QR Code'
    
    def balance_usd(self, obj):
        if obj.balance and obj.btc_price_usd:
            usd_value = obj.balance * obj.btc_price_usd
            return format_html('<span style="color: green;">${:.2f}</span>', usd_value)
        return '$0.00'
    balance_usd.short_description = 'Balance (USD)'
    
    def add_balance_link(self, obj):
        if obj.pk:
            url = f'/admin/banking/bitcoinwallet/{obj.pk}/add-balance/'
            return format_html(
                '<a class="button" href="{}">Add Balance</a>',
                url
            )
        return "Save wallet first"
    add_balance_link.short_description = 'Actions'
    
    def add_balance_view(self, request, wallet_id):
        wallet = get_object_or_404(BitcoinWallet, pk=wallet_id)
        
        if request.method == 'POST':
            form = AddBitcoinBalanceForm(request.POST)
            if form.is_valid():
                amount = form.cleaned_data['amount']
                reason = form.cleaned_data['reason'] or 'Admin balance addition'
                
                # Update wallet balance
                original_balance = wallet.balance
                wallet.balance += amount
                wallet.save()
                
                # Create transaction record
                Transaction.objects.create(
                    user=wallet.user,
                    to_account=None,  # Bitcoin wallet doesn't use Account model
                    amount=amount * (wallet.btc_price_usd or Decimal('0')),  # USD equivalent
                    bitcoin_amount=amount,
                    bitcoin_address=wallet.address,
                    transaction_type='bitcoin_deposit',
                    status='completed',
                    description=f'Admin added {amount} BTC to wallet. Reason: {reason}',
                    reference=f'ADMIN{wallet.id}{int(amount * 100000000)}',  # Unique reference
                    balance_source='admin'
                )
                
                # Create notification for user
                Notification.objects.create(
                    user=wallet.user,
                    notification_type='transaction',
                    title='Bitcoin Balance Added',
                    message=f'Your Bitcoin wallet has been credited with {amount} BTC by an administrator.'
                )
                
                # Log the action
                self.log_change(
                    request, 
                    wallet, 
                    f'Added {amount} BTC to wallet. Previous balance: {original_balance} BTC, New balance: {wallet.balance} BTC. Reason: {reason}'
                )
                
                messages.success(
                    request, 
                    f'Successfully added {amount} BTC to {wallet.user.email}\'s wallet. '
                    f'New balance: {wallet.balance} BTC'
                )
                
                return HttpResponseRedirect(f'/admin/banking/bitcoinwallet/{wallet_id}/change/')
        else:
            form = AddBitcoinBalanceForm()
        
        context = {
            'form': form,
            'wallet': wallet,
            'title': f'Add Bitcoin Balance - {wallet.user.email}',
            'opts': self.model._meta,
            'has_change_permission': True,
            'original': wallet,
        }
        
        return render(request, 'admin/banking/add_bitcoin_balance.html', context)
    
    def add_bitcoin_balance_bulk(self, request, queryset):
        """Bulk action to add Bitcoin balance to multiple wallets"""
        selected = queryset.count()
        if selected == 1:
            wallet = queryset.first()
            return HttpResponseRedirect(f'/admin/banking/bitcoinwallet/{wallet.pk}/add-balance/')
        else:
            self.message_user(
                request, 
                "Please select only one wallet at a time for adding balance. "
                "Use the 'Add Balance' link in the Actions column for individual wallets.", 
                level=messages.WARNING
            )
    add_bitcoin_balance_bulk.short_description = "Add Bitcoin balance to selected wallet"
    
    def activate_wallets(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} Bitcoin wallets.")
    activate_wallets.short_description = "Activate selected wallets"
    
    def deactivate_wallets(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} Bitcoin wallets.")
    deactivate_wallets.short_description = "Deactivate selected wallets"
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only for new wallets
            obj.is_active = True
        
        # Log balance changes
        if change and 'balance' in form.changed_data:
            original = BitcoinWallet.objects.get(pk=obj.pk)
            self.log_change(
                request, 
                obj, 
                f'Balance changed from {original.balance} BTC to {obj.balance} BTC'
            )
        
        super().save_model(request, obj, form, change)

# All these models are already registered elsewhere in the project
# admin.site.register(Account)
# admin.site.register(Transaction)
# admin.site.register(Notification)
# admin.site.register(VirtualCard)
