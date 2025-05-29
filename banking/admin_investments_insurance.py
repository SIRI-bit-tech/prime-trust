from django.contrib import admin
from .models_investments_insurance import InvestmentAccount, Investment, InsurancePolicy, InsuranceClaim

@admin.register(InvestmentAccount)
class InvestmentAccountAdmin(admin.ModelAdmin):
    list_display = ('account_number', 'user', 'account_type', 'balance', 'is_active')
    list_filter = ('account_type', 'is_active')
    search_fields = ('account_number', 'user__email', 'user__first_name', 'user__last_name')
    list_per_page = 20
    raw_id_fields = ('user',)

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'account', 'investment_type', 'quantity', 'purchase_price', 'current_price', 'purchase_date')
    list_filter = ('investment_type', 'purchase_date')
    search_fields = ('name', 'symbol', 'account__account_number')
    list_per_page = 20
    raw_id_fields = ('account',)

@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ('policy_number', 'user', 'policy_type', 'provider', 'coverage_amount', 'is_active')
    list_filter = ('policy_type', 'is_active')
    search_fields = ('policy_number', 'user__email', 'user__first_name', 'user__last_name', 'provider')
    list_per_page = 20
    raw_id_fields = ('user',)

@admin.register(InsuranceClaim)
class InsuranceClaimAdmin(admin.ModelAdmin):
    list_display = ('claim_number', 'policy', 'claim_amount', 'incident_date', 'status')
    list_filter = ('status', 'incident_date')
    search_fields = ('claim_number', 'policy__policy_number', 'policy__user__email')
    list_per_page = 20
    raw_id_fields = ('policy',)
