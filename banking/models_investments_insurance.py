from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from django.core.validators import MinValueValidator

class InvestmentAccount(models.Model):
    ACCOUNT_TYPES = [
        ('brokerage', 'Brokerage Account'),
        ('ira', 'Individual Retirement Account (IRA)'),
        ('roth_ira', 'Roth IRA'),
        ('401k', '401(k)'),
        ('sep_ira', 'SEP IRA'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='investment_accounts')
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    account_number = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_account_type_display()} - {self.account_number}"

class Investment(models.Model):
    INVESTMENT_TYPES = [
        ('stock', 'Stocks'),
        ('bond', 'Bonds'),
        ('mutual_fund', 'Mutual Funds'),
        ('etf', 'Exchange-Traded Funds (ETFs)'),
        ('cd', 'Certificates of Deposit (CDs)'),
        ('real_estate', 'Real Estate'),
    ]
    
    account = models.ForeignKey(InvestmentAccount, on_delete=models.CASCADE, related_name='investments')
    investment_type = models.CharField(max_length=20, choices=INVESTMENT_TYPES)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20, blank=True, null=True)
    quantity = models.DecimalField(max_digits=15, decimal_places=6, default=0)
    purchase_price = models.DecimalField(max_digits=15, decimal_places=2)
    current_price = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    purchase_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def current_value(self):
        if self.current_price:
            return self.quantity * self.current_price
        return self.quantity * self.purchase_price

    def profit_loss(self):
        if self.current_price:
            return (self.current_price - self.purchase_price) * self.quantity
        return 0

    def __str__(self):
        return f"{self.name} ({self.get_investment_type_display()}) - {self.quantity} shares"

class InsurancePolicy(models.Model):
    POLICY_TYPES = [
        ('life', 'Life Insurance'),
        ('health', 'Health Insurance'),
        ('auto', 'Auto Insurance'),
        ('homeowners', 'Homeowners Insurance'),
        ('renters', 'Renters Insurance'),
        ('disability', 'Disability Insurance'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='insurance_policies')
    policy_type = models.CharField(max_length=20, choices=POLICY_TYPES)
    policy_number = models.CharField(max_length=50, unique=True)
    provider = models.CharField(max_length=100)
    coverage_amount = models.DecimalField(max_digits=15, decimal_places=2)
    monthly_premium = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_policy_type_display()} - {self.provider} ({self.policy_number})"

class InsuranceClaim(models.Model):
    CLAIM_STATUS = [
        ('submitted', 'Submitted'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('paid', 'Paid'),
    ]
    
    policy = models.ForeignKey(InsurancePolicy, on_delete=models.CASCADE, related_name='claims')
    claim_number = models.CharField(max_length=50, unique=True)
    claim_amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField()
    incident_date = models.DateField()
    claim_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=CLAIM_STATUS, default='submitted')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Claim {self.claim_number} - {self.get_status_display()}"
