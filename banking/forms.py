from django import forms
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth import get_user_model

from .models import Account, Transaction
from .models_investments_insurance import InvestmentAccount, Investment, InsurancePolicy
from accounts.models import UserProfile

User = get_user_model()

# Common form field styling
INPUT_CLASSES = 'block w-full px-4 py-3 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm'
SELECT_CLASSES = 'block w-full px-4 py-3 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm'
TEXTAREA_CLASSES = 'block w-full px-4 py-3 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm'

class SendMoneyForm(forms.Form):
    """Form for sending money to another user"""
    recipient_account_number = forms.CharField(
        label='Recipient Account Number',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
            'placeholder': 'Enter 10-digit account number'
        })
    )
    
    amount = forms.DecimalField(
        label='Amount',
        max_digits=15,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'appearance-none block w-full pl-7 pr-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
            'placeholder': '0.00',
            'step': '0.01'
        })
    )
    description = forms.CharField(
        label='Description (Optional)',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
            'placeholder': 'What is this payment for?'
        })
    )
    
    transaction_pin = forms.CharField(
        label='Transaction PIN',
        max_length=4,
        min_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm text-center font-mono',
            'placeholder': 'Enter your 4-digit PIN',
            'maxlength': '4',
            'pattern': '[0-9]*',
            'inputmode': 'numeric',
            'autocomplete': 'off'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Get user's account for validation
        if self.user:
            self.user_account = Account.objects.filter(user=self.user).first()
    
    def clean_transaction_pin(self):
        pin = self.cleaned_data.get('transaction_pin')
        if not pin:
            raise forms.ValidationError('Transaction PIN is required')
        
        if not pin.isdigit():
            raise forms.ValidationError('Transaction PIN must contain only digits')
        
        if self.user and not self.user.profile.check_transaction_pin(pin):
            raise forms.ValidationError('Invalid transaction PIN')
        
        return pin

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        
        if hasattr(self, 'user_account') and self.user_account and amount:
            if amount > self.user_account.balance:
                raise forms.ValidationError(f"Insufficient funds. Your current balance is ${self.user_account.balance}")
        
        return amount


class DepositForm(forms.Form):
    """Form for depositing money into an account"""
    to_account = forms.ModelChoiceField(
        label="To Account",
        queryset=Account.objects.none(),
        empty_label=None,
        widget=forms.Select(attrs={
            'class': SELECT_CLASSES
        })
    )
    
    amount = forms.DecimalField(
        label="Amount",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('10.00'),  # Minimum deposit amount
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Enter amount to deposit',
            'step': '0.01'
        })
    )
    
    payment_method = forms.ChoiceField(
        label="Payment Method",
        choices=[
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('bank_transfer', 'Bank Transfer')
        ],
        widget=forms.Select(attrs={
            'class': SELECT_CLASSES,
            'hx-get': '/banking/payment-fields/',
            'hx-trigger': 'change',
            'hx-target': '#payment-fields',
            'hx-swap': 'innerHTML',
            'hx-include': '[name=payment_method]'
        })
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Only show accounts belonging to the user
            self.fields['to_account'].queryset = Account.objects.filter(user=user)


class InvestmentForm(forms.ModelForm):
    """Form for creating and updating investments"""
    class Meta:
        model = Investment
        fields = ['account', 'investment_type', 'name', 'symbol', 'quantity', 'purchase_price', 'purchase_date']
        widgets = {
            'account': forms.Select(attrs={'class': SELECT_CLASSES}),
            'investment_type': forms.Select(attrs={'class': SELECT_CLASSES}),
            'name': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'e.g., Apple Inc.'}),
            'symbol': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'e.g., AAPL'}),
            'quantity': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'step': '0.000001',
                'min': '0.000001',
            }),
            'purchase_price': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'step': '0.01',
                'min': '0.01',
            }),
            'purchase_date': forms.DateInput(attrs={
                'type': 'date',
                'class': INPUT_CLASSES,
                'max': timezone.now().date().isoformat(),
            }),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].queryset = InvestmentAccount.objects.filter(user=user, is_active=True)
        
        # Set initial purchase date to today if creating a new investment
        if not self.instance.pk:
            self.fields['purchase_date'].initial = timezone.now().date()

    def clean_purchase_date(self):
        purchase_date = self.cleaned_data.get('purchase_date')
        if purchase_date > timezone.now().date():
            raise forms.ValidationError("Purchase date cannot be in the future.")
        return purchase_date


class InsurancePolicyForm(forms.ModelForm):
    """Form for creating and updating insurance policies"""
    class Meta:
        model = InsurancePolicy
        fields = ['policy_type', 'policy_number', 'provider', 'coverage_amount', 
                 'monthly_premium', 'start_date', 'end_date']
        widgets = {
            'policy_type': forms.Select(attrs={'class': SELECT_CLASSES}),
            'policy_number': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Enter policy number'
            }),
            'provider': forms.TextInput(attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'e.g., State Farm, Allstate'
            }),
            'coverage_amount': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'step': '0.01',
                'min': '0.01',
            }),
            'monthly_premium': forms.NumberInput(attrs={
                'class': INPUT_CLASSES,
                'step': '0.01',
                'min': '0.01',
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': INPUT_CLASSES,
                'max': (timezone.now() + timedelta(days=365 * 10)).date().isoformat(),
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': INPUT_CLASSES,
                'min': timezone.now().date().isoformat(),
            }),
        }

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = user
        
        # Set initial start date to today if creating a new policy
        if not self.instance.pk:
            self.fields['start_date'].initial = timezone.now().date()

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            self.add_error('end_date', "End date must be after start date.")
        
        return cleaned_data
    
    def clean_start_date(self):
        start_date = self.cleaned_data.get('start_date')
        if start_date and start_date < timezone.now().date() - timedelta(days=30):
            raise forms.ValidationError("Start date cannot be more than 30 days in the past.")
        return start_date
    
    card_number = forms.CharField(
        label="Card Number",
        required=False,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Enter card number',
            'data-payment-method': 'credit_card,debit_card',
            'maxlength': '16'
        })
    )
    
    expiry_date = forms.CharField(
        label="Expiry Date (MM/YY)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'MM/YY',
            'data-payment-method': 'credit_card,debit_card',
            'maxlength': '5'
        })
    )
    
    cvv = forms.CharField(
        label="CVV",
        required=False,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'CVV',
            'data-payment-method': 'credit_card,debit_card',
            'maxlength': '4'
        })
    )
    
    bank_account_number = forms.CharField(
        label="Bank Account Number",
        required=False,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Enter bank account number',
            'data-payment-method': 'bank_transfer'
        })
    )
    
    bank_routing_number = forms.CharField(
        label="Bank Routing Number",
        required=False,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Enter bank routing number',
            'data-payment-method': 'bank_transfer'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        
        if payment_method in ['credit_card', 'debit_card']:
            card_number = cleaned_data.get('card_number')
            expiry_date = cleaned_data.get('expiry_date')
            cvv = cleaned_data.get('cvv')
            
            if not card_number:
                self.add_error('card_number', 'Card number is required')
            if not expiry_date:
                self.add_error('expiry_date', 'Expiry date is required')
            if not cvv:
                self.add_error('cvv', 'CVV is required')
                
        elif payment_method == 'bank_transfer':
            bank_account_number = cleaned_data.get('bank_account_number')
            bank_routing_number = cleaned_data.get('bank_routing_number')
            
            if not bank_account_number:
                self.add_error('bank_account_number', 'Bank account number is required')
            if not bank_routing_number:
                self.add_error('bank_routing_number', 'Bank routing number is required')
                
        return cleaned_data

class SendBitcoinForm(forms.Form):
    BALANCE_CHOICES = [
        ('fiat', 'Fiat Balance'),
        ('bitcoin', 'Bitcoin Balance'),
    ]
    
    CRYPTOCURRENCY_CHOICES = [
        ('BTC', 'Bitcoin (BTC)'),
    ]
    
    NETWORK_CHOICES = [
        ('native', 'Native'),
    ]
    
    balance_source = forms.ChoiceField(
        choices=BALANCE_CHOICES,
        label='Select Balance to Use',
        initial='bitcoin',
        widget=forms.RadioSelect(attrs={
            'class': 'focus:ring-primary-500 h-4 w-4 text-primary-600 border-gray-300'
        })
    )
    
    amount = forms.DecimalField(
        label='Amount to Transfer',
        max_digits=18,
        decimal_places=8,
        min_value=Decimal('0.00000001'),
        widget=forms.NumberInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm text-right',
            'placeholder': '0.00000000',
            'step': '0.00000001'
        })
    )
    
    cryptocurrency = forms.ChoiceField(
        choices=CRYPTOCURRENCY_CHOICES,
        label='Cryptocurrency',
        initial='BTC',
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm'
        })
    )
    
    network = forms.ChoiceField(
        choices=NETWORK_CHOICES,
        label='Network',
        initial='native',
        widget=forms.Select(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm'
        })
    )
    
    wallet_address = forms.CharField(
        label='Wallet Address',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
            'placeholder': 'Enter wallet address'
        })
    )
    
    transaction_pin = forms.CharField(
        label='Transaction PIN',
        max_length=4,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm text-center',
            'placeholder': 'Enter your 4-10 digit PIN',
            'maxlength': '10'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Get user's account balance and Bitcoin wallet balance
            user_accounts = Account.objects.filter(user=self.user)
            total_fiat_balance = sum(account.balance for account in user_accounts)
            
            try:
                bitcoin_wallet = self.user.bitcoinwallet
                bitcoin_balance = bitcoin_wallet.balance
            except:
                bitcoin_balance = Decimal('0.00000000')
            
            # Update balance choice labels with actual balances
            self.fields['balance_source'].choices = [
                ('fiat', f'Fiat Balance - ${total_fiat_balance:.2f}'),
                ('bitcoin', f'Bitcoin Balance - {bitcoin_balance:.8f} BTC'),
            ]
    
    def clean_transaction_pin(self):
        pin = self.cleaned_data.get('transaction_pin')
        if not pin:
            raise forms.ValidationError('Transaction PIN is required')
        
        if self.user and not self.user.profile.check_transaction_pin(pin):
            raise forms.ValidationError('Invalid transaction PIN')
        
        return pin
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        balance_source = self.cleaned_data.get('balance_source')
        
        if not amount:
            raise forms.ValidationError('Amount is required')
        
        if balance_source == 'bitcoin':
            # Check Bitcoin balance
            try:
                bitcoin_wallet = self.user.bitcoinwallet
                if amount > bitcoin_wallet.balance:
                    raise forms.ValidationError('Insufficient Bitcoin balance')
            except:
                raise forms.ValidationError('Bitcoin wallet not found')
        
        elif balance_source == 'fiat':
            # Check fiat balance - convert BTC amount to USD
            try:
                bitcoin_wallet = self.user.bitcoinwallet
                usd_amount = amount * bitcoin_wallet.btc_price_usd
                
                user_accounts = Account.objects.filter(user=self.user)
                total_fiat_balance = sum(account.balance for account in user_accounts)
                
                if usd_amount > total_fiat_balance:
                    raise forms.ValidationError('Insufficient fiat balance')
            except:
                raise forms.ValidationError('Unable to verify fiat balance')
        
        return amount
    
    def clean_wallet_address(self):
        address = self.cleaned_data.get('wallet_address')
        if not address:
            raise forms.ValidationError('Wallet address is required')
        
        # Basic Bitcoin address validation
        if not (address.startswith('1') or address.startswith('3') or address.startswith('bc1')):
            raise forms.ValidationError('Invalid Bitcoin address format')
        
        return address
