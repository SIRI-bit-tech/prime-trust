from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
from accounts.models import CustomUser
from django.conf import settings
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image

class Account(models.Model):
    ACCOUNT_TYPES = (
        ('checking', 'Checking'),
        ('savings', 'Savings'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='accounts')
    account_number = models.CharField(max_length=20, unique=True)
    routing_number = models.CharField(max_length=9, blank=True)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_TYPES, default='checking')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def generate_routing_number(self):
        """Generate a 9-digit routing number"""
        import random
        # Generate 8 random digits
        routing = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        # Add a check digit (simple checksum for example)
        check_digit = sum(int(d) * (7 if i % 2 == 0 else 3) for i, d in enumerate(routing)) % 10
        return f"{routing}{check_digit}"
    
    @staticmethod
    def generate_account_number(length=12):
        """Generate a numeric account number of given length"""
        import random
        return ''.join(str(random.randint(0, 9)) for _ in range(length))
        
    def generate_card_number(self, card_type='visa'):
        """Generate a 16-digit card number"""
        import random
        # Start with 4 for Visa or 5 for Mastercard
        prefix = '4' if card_type == 'visa' else '5'
        # Generate remaining 15 digits
        card_number = prefix + ''.join([str(random.randint(0, 9)) for _ in range(15)])
        return card_number
        
    def create_virtual_card(self):
        """Create a virtual card for this account"""
        from datetime import date
        from dateutil.relativedelta import relativedelta
        
        # Generate expiry date 3 years from now
        expiry_date = date.today() + relativedelta(years=3)
        
        # Generate CVV (3 or 4 digits)
        import random
        cvv = str(random.randint(100, 9999)).zfill(3 if random.random() > 0.5 else 4)
        
        # Create the virtual card
        card = VirtualCard.objects.create(
            user=self.user,
            card_number=self.generate_card_number(),
            card_type='visa',  # Default to Visa
            expiry_date=expiry_date,
            cvv=cvv
        )
        return card
        
    def save(self, *args, **kwargs):
        # Always generate a numeric-only account number on creation (10 digits)
        if self._state.adding:
            self.account_number = self.generate_account_number(length=10)
        # Generate routing number if this is a new account
        if not self.routing_number:
            self.routing_number = self.generate_routing_number()
        super().save(*args, **kwargs)
        
        # Create a virtual card if this is a new account and it's a checking account
        if self._state.adding and self.account_type == 'checking':
            self.create_virtual_card()

    def __str__(self):
        return f"{self.user.email} - {self.get_account_type_display()} ({self.account_number})"

class VirtualCard(models.Model):
    CARD_TYPES = (
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='virtual_cards')
    card_number = models.CharField(max_length=16)
    card_type = models.CharField(max_length=10, choices=CARD_TYPES)
    expiry_date = models.DateField()
    cvv = models.CharField(max_length=4)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_card_type_display()} - {self.card_number[-4:]}"

class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('transfer', 'Transfer'),
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('bitcoin_send', 'Bitcoin Send'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('declined', 'Declined'),
        ('failed', 'Failed'),
    )

    from_account = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        related_name='transactions_sent',
        null=True,
        blank=True
    )
    to_account = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        related_name='transactions_received',
        null=True,
        blank=True
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True)
    reference = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Bitcoin-specific fields
    bitcoin_amount = models.DecimalField(
        max_digits=18, 
        decimal_places=8, 
        null=True, 
        blank=True,
        help_text="Amount in Bitcoin for crypto transactions"
    )
    bitcoin_address = models.CharField(
        max_length=100, 
        null=True, 
        blank=True,
        help_text="Bitcoin wallet address for crypto transactions"
    )
    bitcoin_tx_hash = models.CharField(
        max_length=64, 
        null=True, 
        blank=True,
        help_text="Bitcoin transaction hash"
    )
    balance_source = models.CharField(
        max_length=20, 
        null=True, 
        blank=True,
        choices=[('fiat', 'Fiat Balance'), ('bitcoin', 'Bitcoin Balance')],
        help_text="Source of funds for Bitcoin transactions"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.transaction_type == 'bitcoin_send':
            return f"Bitcoin Send - {self.bitcoin_amount} BTC ({self.status})"
        return f"{self.get_transaction_type_display()} - {self.amount} ({self.status})"

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('transaction', 'Transaction Update'),
        ('account', 'Account Update'),
        ('security', 'Security Alert'),
        ('general', 'General Notification'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=100)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_transaction = models.ForeignKey(
        Transaction, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.title}"

class BitcoinWallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    address = models.CharField(max_length=100, unique=True, blank=True, null=True)
    balance = models.DecimalField(max_digits=18, decimal_places=8, default=Decimal('0.00000000'))
    qr_code = models.ImageField(upload_to='bitcoin_qr_codes/', blank=True, null=True, help_text="Upload QR code image for this wallet address")
    btc_price_usd = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)

    @property
    def balance_usd(self):
        return self.balance * self.btc_price_usd if self.balance and self.btc_price_usd else Decimal('0.00')

    def __str__(self):
        return f"Bitcoin Wallet - {self.user.email}"