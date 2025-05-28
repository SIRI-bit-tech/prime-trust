from django.contrib import admin
from django.utils.html import format_html
from .models_loans import LoanApplication, LoanAccount, LoanPayment
from .models_bills import Biller, BillPayment, Payee, ScheduledPayment

@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    list_display = ('application_number', 'user', 'loan_type', 'amount', 'term_months', 'status', 'created_at')
    list_filter = ('status', 'loan_type', 'created_at')
    search_fields = ('application_number', 'user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('application_number', 'created_at', 'updated_at')
    fieldsets = (
        ('Application Information', {
            'fields': ('application_number', 'user', 'loan_type', 'status')
        }),
        ('Loan Details', {
            'fields': ('amount', 'term_months', 'purpose', 'interest_rate', 'monthly_payment')
        }),
        ('Employment Information', {
            'fields': ('employment_status', 'annual_income', 'employer_name', 'job_title', 'years_employed')
        }),
        ('Approval', {
            'fields': ('approved_by', 'approved_at', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(LoanAccount)
class LoanAccountAdmin(admin.ModelAdmin):
    list_display = ('loan_number', 'application', 'original_amount', 'current_balance', 'status')
    list_filter = ('status', 'created_at')
    search_fields = ('loan_number', 'application__application_number', 'account__account_number')
    readonly_fields = ('loan_number', 'created_at', 'updated_at')
    fieldsets = (
        ('Loan Information', {
            'fields': ('loan_number', 'application', 'account', 'status')
        }),
        ('Financial Details', {
            'fields': ('original_amount', 'current_balance', 'interest_rate', 'term_months', 'monthly_payment')
        }),
        ('Payment Schedule', {
            'fields': ('start_date', 'next_payment_date')
        }),
        ('Collateral', {
            'fields': ('collateral_description', 'collateral_value')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_number', 'loan', 'amount', 'payment_date', 'status')
    list_filter = ('status', 'payment_method', 'payment_date')
    search_fields = ('payment_number', 'loan__loan_number', 'reference_number')
    readonly_fields = ('payment_number', 'created_at', 'updated_at')
    fieldsets = (
        ('Payment Information', {
            'fields': ('payment_number', 'loan', 'status', 'payment_method')
        }),
        ('Amount Details', {
            'fields': ('amount', 'principal_amount', 'interest_amount', 'fees')
        }),
        ('Dates', {
            'fields': ('payment_date', 'due_date')
        }),
        ('Processing', {
            'fields': ('reference_number', 'notes', 'processed_by', 'processed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Biller)
class BillerAdmin(admin.ModelAdmin):
    list_display = ('name', 'biller_type', 'is_active')
    list_filter = ('biller_type', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Biller Information', {
            'fields': ('name', 'biller_type', 'description', 'logo', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('website', 'customer_service_phone')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(BillPayment)
class BillPaymentAdmin(admin.ModelAdmin):
    list_display = ('reference_number', 'biller', 'account', 'amount', 'status', 'scheduled_date')
    list_filter = ('status', 'payment_method', 'scheduled_date')
    search_fields = ('reference_number', 'biller__name', 'account__account_number', 'confirmation_number')
    readonly_fields = ('reference_number', 'created_at', 'updated_at')
    fieldsets = (
        ('Payment Information', {
            'fields': ('reference_number', 'user', 'biller', 'account', 'status')
        }),
        ('Amount & Method', {
            'fields': ('amount', 'fee', 'payment_method')
        }),
        ('Biller Details', {
            'fields': ('account_number', 'confirmation_number')
        }),
        ('Scheduling', {
            'fields': ('scheduled_date', 'processed_date', 'is_recurring', 'recurring_id')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Payee)
class PayeeAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'account_number', 'is_business', 'is_favorite')
    list_filter = ('is_business', 'is_favorite', 'created_at')
    search_fields = ('name', 'user__email', 'account_number')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Payee Information', {
            'fields': ('user', 'name', 'account_number', 'description', 'is_business', 'is_favorite')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ScheduledPayment)
class ScheduledPaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'user', 'payee', 'amount', 'frequency', 'next_payment_date', 'status')
    list_filter = ('status', 'frequency', 'start_date')
    search_fields = ('reference', 'user__email', 'payee__name', 'account__account_number')
    readonly_fields = ('reference', 'created_at', 'updated_at')
    fieldsets = (
        ('Payment Information', {
            'fields': ('reference', 'user', 'payee', 'account', 'status')
        }),
        ('Amount & Schedule', {
            'fields': ('amount', 'frequency', 'start_date', 'end_date', 'next_payment_date')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
