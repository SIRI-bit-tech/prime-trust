from django import forms
from django.core.validators import MinValueValidator
from decimal import Decimal

from .models import Account, Transaction

class SendMoneyForm(forms.Form):
    """Form for sending money to another user"""
    recipient_email = forms.EmailField(
        label="Recipient Email",
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
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
            'class': 'form-select block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm'
        })
    )
    
    amount = forms.DecimalField(
        label="Amount",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-input block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
            'placeholder': 'Enter amount',
            'step': '0.01'
        })
    )
    
    description = forms.CharField(
        label="Description",
        required=False,
        max_length=200,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm',
            'placeholder': 'Enter a description (optional)',
            'rows': 3
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['from_account'].queryset = Account.objects.filter(user=user)
    
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        from_account = self.cleaned_data.get('from_account')
        
        if from_account and amount and amount > from_account.balance:
            raise forms.ValidationError(f"Insufficient funds. Your current balance is ${from_account.balance}")
        
        return amount
