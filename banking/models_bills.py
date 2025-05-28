from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from accounts.models import CustomUser
from .models import Account

class Biller(models.Model):
    """A company or entity that can receive bill payments"""
    BILLER_TYPES = (
        ('utilities', 'Utilities'),
        ('telecom', 'Telecommunications'),
        ('credit_card', 'Credit Card'),
        ('loan', 'Loan Payment'),
        ('insurance', 'Insurance'),
        ('education', 'Education'),
        ('government', 'Government'),
        ('other', 'Other'),
    )
    
    name = models.CharField(max_length=100)
    biller_type = models.CharField(max_length=20, choices=BILLER_TYPES)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='billers/logos/', null=True, blank=True)
    website = models.URLField(blank=True)
    customer_service_phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class BillPayment(models.Model):
    """A bill payment made by a user"""
    PAYMENT_METHODS = (
        ('checking', 'Checking Account'),
        ('savings', 'Savings Account'),
        ('debit_card', 'Debit Card'),
        ('credit_card', 'Credit Card'),
    )
    
    PAYMENT_STATUS = (
        ('scheduled', 'Scheduled'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='bill_payments')
    biller = models.ForeignKey(Biller, on_delete=models.PROTECT, related_name='payments')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='bill_payments')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reference_number = models.CharField(max_length=50, blank=True)
    account_number = models.CharField(max_length=50, help_text="User's account number with the biller")
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='scheduled')
    scheduled_date = models.DateField()
    processed_date = models.DateField(null=True, blank=True)
    confirmation_number = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=False)
    recurring_id = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"{self.biller.name} - {self.amount} ({self.status})"
    
    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        super().save(*args, **kwargs)
    
    def generate_reference_number(self):
        """Generate a unique reference number for the payment"""
        from django.utils.timezone import now
        import random
        
        timestamp = now().strftime('%y%m%d%H%M%S')
        random_str = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        return f"BP{timestamp}{random_str}"


class Payee(models.Model):
    """A payee that a user can send payments to"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payees')
    name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True)
    is_business = models.BooleanField(default=False)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address_line1 = models.CharField(max_length=100, blank=True)
    address_line2 = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=50, blank=True)
    state = models.CharField(max_length=50, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=50, default='United States')
    is_favorite = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['user', 'name', 'account_number']
    
    def __str__(self):
        return f"{self.name} ({self.account_number[-4:]})"


class ScheduledPayment(models.Model):
    """A recurring or future-dated payment"""
    FREQUENCIES = (
        ('once', 'One Time'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('biweekly', 'Every 2 Weeks'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    )
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='scheduled_payments')
    payee = models.ForeignKey(Payee, on_delete=models.PROTECT, related_name='scheduled_payments')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='scheduled_payments')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCIES, default='once')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_payment_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    reference = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['next_payment_date']
    
    def __str__(self):
        return f"{self.payee.name} - {self.amount} ({self.get_frequency_display()})"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()
        super().save(*args, **kwargs)
    
    def generate_reference(self):
        """Generate a unique reference for the scheduled payment"""
        from django.utils.timezone import now
        import random
        
        timestamp = now().strftime('%y%m%d%H%M%S')
        random_str = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        return f"SP{timestamp}{random_str}"
    
    def calculate_next_payment_date(self):
        """Calculate the next payment date based on frequency"""
        from dateutil.relativedelta import relativedelta
        
        if self.frequency == 'once':
            return None
        elif self.frequency == 'daily':
            return self.next_payment_date + relativedelta(days=1)
        elif self.frequency == 'weekly':
            return self.next_payment_date + relativedelta(weeks=1)
        elif self.frequency == 'biweekly':
            return self.next_payment_date + relativedelta(weeks=2)
        elif self.frequency == 'monthly':
            return self.next_payment_date + relativedelta(months=1)
        elif self.frequency == 'quarterly':
            return self.next_payment_date + relativedelta(months=3)
        elif self.frequency == 'yearly':
            return self.next_payment_date + relativedelta(years=1)
        return None
