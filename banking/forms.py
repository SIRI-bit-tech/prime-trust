from django import forms
from django.core.validators import MinValueValidator
from decimal import Decimal

from .models import Account, Transaction

# Common form field styling
INPUT_CLASSES = 'block w-full px-4 py-3 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm'
SELECT_CLASSES = 'block w-full px-4 py-3 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm'
TEXTAREA_CLASSES = 'block w-full px-4 py-3 rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm'

class SendMoneyForm(forms.Form):
    """Form for sending money to another user"""
    recipient_email = forms.EmailField(
        label="Recipient Email",
        required=True,
        widget=forms.EmailInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Enter recipient email',
            'hx-get': '/banking/check-recipient/',
            'hx-target': '#recipient-check',
            'hx-trigger': 'keyup changed delay:500ms',
            'hx-swap': 'innerHTML'
        })
    )
    
    from_account = forms.ModelChoiceField(
        label="From Account",
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
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': INPUT_CLASSES,
            'placeholder': 'Enter amount',
            'step': '0.01'
        })
    )
    
    description = forms.CharField(
        label="Description",
        required=False,
        max_length=200,
        widget=forms.Textarea(attrs={
            'class': TEXTAREA_CLASSES,
            'placeholder': 'Enter a description (optional)',
            'rows': 3
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(SendMoneyForm, self).__init__(*args, **kwargs)
        
        if user:
            # Only show accounts belonging to the user
            self.fields['from_account'].queryset = Account.objects.filter(user=user)
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        from_account = self.cleaned_data.get('from_account')
        
        if from_account and amount and amount > from_account.balance:
            raise forms.ValidationError(f"Insufficient funds. Your current balance is ${from_account.balance}")
        
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
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(DepositForm, self).__init__(*args, **kwargs)
        
        if user:
            # Only show accounts belonging to the user
            self.fields['to_account'].queryset = Account.objects.filter(user=user)
    
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
