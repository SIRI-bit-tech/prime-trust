from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from accounts.models import CustomUser
from .models import Account

class LoanApplication(models.Model):
    LOAN_TYPES = (
        ('personal', 'Personal Loan'),
        ('auto', 'Auto Loan'),
        ('mortgage', 'Mortgage'),
        ('education', 'Education Loan'),
        ('business', 'Business Loan'),
    )
    
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('disbursed', 'Disbursed'),
        ('withdrawn', 'Withdrawn'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='loan_applications')
    application_number = models.CharField(max_length=20, unique=True)
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('1000.00'))])
    term_months = models.PositiveIntegerField()
    purpose = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    monthly_payment = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    reason_for_loan = models.TextField(blank=True)
    employment_status = models.CharField(max_length=50, blank=True)
    annual_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    employer_name = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    years_employed = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_loans'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_loan_type_display()} - {self.amount} ({self.status})"
    
    def save(self, *args, **kwargs):
        if not self.application_number:
            self.application_number = self.generate_application_number()
        super().save(*args, **kwargs)
    
    def generate_application_number(self):
        """Generate a unique application number"""
        from django.utils.timezone import now
        import random
        
        timestamp = now().strftime('%Y%m%d%H%M%S')
        random_str = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        return f"LNA{timestamp}{random_str}"


class LoanAccount(models.Model):
    LOAN_STATUS = (
        ('active', 'Active'),
        ('paid', 'Paid Off'),
        ('defaulted', 'Defaulted'),
        ('written_off', 'Written Off'),
    )
    
    application = models.OneToOneField(
        LoanApplication, 
        on_delete=models.PROTECT, 
        related_name='loan_account'
    )
    account = models.OneToOneField(
        Account,
        on_delete=models.PROTECT,
        related_name='loan_account'
    )
    loan_number = models.CharField(max_length=20, unique=True)
    original_amount = models.DecimalField(max_digits=15, decimal_places=2)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    term_months = models.PositiveIntegerField()
    monthly_payment = models.DecimalField(max_digits=15, decimal_places=2)
    start_date = models.DateField()
    next_payment_date = models.DateField()
    status = models.CharField(max_length=20, choices=LOAN_STATUS, default='active')
    collateral_description = models.TextField(blank=True)
    collateral_value = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.loan_number} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        if not self.loan_number:
            self.loan_number = self.generate_loan_number()
        super().save(*args, **kwargs)
    
    def generate_loan_number(self):
        """Generate a unique loan account number"""
        from django.utils.timezone import now
        import random
        
        timestamp = now().strftime('%y%m%d')
        random_str = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        return f"LON{timestamp}{random_str}"


class LoanPayment(models.Model):
    PAYMENT_METHODS = (
        ('bank_transfer', 'Bank Transfer'),
        ('debit_card', 'Debit Card'),
        ('check', 'Check'),
        ('ach', 'ACH'),
    )
    
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('returned', 'Returned'),
    )
    
    loan = models.ForeignKey(LoanAccount, on_delete=models.CASCADE, related_name='payments')
    payment_number = models.CharField(max_length=20, unique=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=15, decimal_places=2)
    fees = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_date = models.DateField()
    due_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    reference_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    processed_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='processed_payments'
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"{self.payment_number} - {self.amount} ({self.status})"
    
    def save(self, *args, **kwargs):
        if not self.payment_number:
            self.payment_number = self.generate_payment_number()
        super().save(*args, **kwargs)
    
    def generate_payment_number(self):
        """Generate a unique payment number"""
        from django.utils.timezone import now
        import random
        
        timestamp = now().strftime('%y%m%d')
        random_str = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        return f"LPM{timestamp}{random_str}"
