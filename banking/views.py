from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal
import uuid

from accounts.models import CustomUser
from .models import Account, Transaction, Notification
from .forms import SendMoneyForm, DepositForm
from django_htmx.http import trigger_client_event
from .utils import send_transaction_notification

@login_required
def payment_fields(request):
    """Return payment fields for HTMX requests"""
    return render(request, 'banking/partials/payment_fields.html')

@login_required
def send_money(request):
    """Send money to another user"""
    user = request.user
    
    # Get user's accounts for the form
    accounts = Account.objects.filter(user=user)
    
    if request.method == 'POST':
        form = SendMoneyForm(request.POST, user=user)
        if form.is_valid():
            recipient_account_number = form.cleaned_data['recipient_account_number']
            from_account = form.cleaned_data['from_account']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            
            try:
                # Find recipient account
                recipient_account = Account.objects.get(account_number=recipient_account_number)
                recipient = recipient_account.user
                
                # Prevent sending money to own account
                if recipient_account.user == user:
                    if request.htmx:
                        response = HttpResponse("<div class='text-red-600'>Cannot send money to your own account</div>")
                        return response
                    messages.error(request, 'Cannot send money to your own account')
                    return redirect('dashboard:home')
                
                # Create the transaction
                with transaction.atomic():
                    # Check if user has sufficient funds
                    if from_account.balance < amount:
                        if request.htmx:
                            response = HttpResponse("<div class='text-red-600'>Insufficient funds</div>")
                            return response
                        messages.error(request, 'Insufficient funds')
                        return redirect('dashboard:home')
                    
                    # Create transaction record with real-time processing
                    transaction_ref = f"TRF{uuid.uuid4().hex[:8].upper()}"
                    new_transaction = Transaction.objects.create(
                        user=user,
                        from_account=from_account,
                        to_account=recipient_account,
                        amount=amount,
                        transaction_type='transfer',
                        status='completed',
                        description=description,
                        reference=transaction_ref
                    )
                    
                    # Update account balances
                    from_account.balance -= amount
                    from_account.save()
                    
                    recipient_account.balance += amount
                    recipient_account.save()
                    
                    # Create notifications
                    Notification.objects.create(
                        user=user,
                        notification_type='transaction',
                        title='Money Sent',
                        message=f"You sent ${amount} to account ending in {recipient_account_number[-4:]}",
                        related_transaction=new_transaction
                    )
                    
                    Notification.objects.create(
                        user=recipient,
                        notification_type='transaction',
                        title='Money Received',
                        message=f"You received ${amount} from {user.get_full_name()}",
                        related_transaction=new_transaction
                    )
                    
                    # Send email notifications
                    send_transaction_notification(user, new_transaction, is_sender=True)
                    send_transaction_notification(recipient, new_transaction, is_sender=False)
                
                if request.htmx:
                    # Create receipt context
                    receipt_context = {
                        'amount': amount,
                        'transaction_date': new_transaction.created_at.strftime('%B %d, %Y at %I:%M %p'),
                        'from_account_number': from_account.account_number,
                        'from_account_type': from_account.get_account_type_display(),
                        'to_account_number': recipient_account_number,
                        'recipient_name': recipient.get_full_name(),
                        'description': description,
                        'reference': transaction_ref,
                    }
                    
                    # Return receipt modal
                    return render(request, 'banking/partials/money_transfer_receipt.html', receipt_context)
                
                messages.success(request, f"Successfully sent ${amount} to account ending in {recipient_account_number[-4:]}")
                return redirect('dashboard:transactions')
                
            except Account.DoesNotExist:
                if request.htmx:
                    response = HttpResponse("<div class='text-red-600'>Account number not found</div>")
                    return response
                messages.error(request, 'Account number not found')
                return redirect('dashboard:home')
    else:
        form = SendMoneyForm(user=user)
    
    # Get current time for greeting
    from datetime import datetime
    current_hour = datetime.now().hour
    greeting = "Good Evening"
    if current_hour < 12:
        greeting = "Good Morning"
    elif current_hour < 18:
        greeting = "Good Afternoon"
    
    context = {
        'greeting': greeting,
        'form': form,
        'active_tab': 'send_money'
    }
    
    if request.htmx:
        return render(request, 'banking/partials/send_money_form.html', context)
    return render(request, 'banking/send_money.html', context)

@login_required
def check_recipient(request):
    """Check if recipient account exists (HTMX endpoint)"""
    account_number = request.GET.get('recipient_account_number', '')
    
    if account_number:
        try:
            account = Account.objects.get(account_number=account_number)
            # Don't show account holder name for privacy/security
            return HttpResponse(
                f"<div class='text-green-600'>Account found</div>"
            )
        except Account.DoesNotExist:
            return HttpResponse(
                "<div class='text-red-600'>Account not found</div>"
            )
    
    return HttpResponse("")

@login_required
def get_transaction_details(request, transaction_id):
    """Get details of a specific transaction"""
    # Allow viewing transactions where the user is either sender or recipient
    user_filter = Q(from_account__user=request.user) | Q(to_account__user=request.user)
    transaction = get_object_or_404(Transaction.objects.filter(user_filter), id=transaction_id)
    
    context = {
        'transaction': transaction
    }
    
    return render(request, 'banking/partials/transaction_details.html', context)

@login_required
def deposit(request):
    """Deposit money into an account"""
    user = request.user
    
    if request.method == 'POST':
        form = DepositForm(data=request.POST, user=user)
        if form.is_valid():
            to_account = form.cleaned_data['to_account']
            amount = form.cleaned_data['amount']
            payment_method = form.cleaned_data['payment_method']
            
            # Process the payment in real-time
            
            # Create the transaction
            with transaction.atomic():
                # Generate a reference number
                transaction_ref = f"DEP{uuid.uuid4().hex[:8].upper()}"
                
                # Create transaction record with real-time processing
                new_transaction = Transaction.objects.create(
                    to_account=to_account,
                    amount=amount,
                    transaction_type='deposit',
                    status='completed',
                    description=f"Deposit via {dict(form.fields['payment_method'].choices)[payment_method]}",
                    reference=transaction_ref
                )
                
                # Update account balance
                to_account.balance += amount
                to_account.save()
                
                # Create notification
                Notification.objects.create(
                    user=user,
                    notification_type='transaction',
                    title='Deposit Successful',
                    message=f"You deposited ${amount} into your {to_account.get_account_type_display()} account",
                    related_transaction=new_transaction
                )
            
            if request.htmx:
                response = HttpResponse()
                trigger_client_event(response, 'depositComplete', {
                    'message': f"Successfully deposited ${amount} into your account"
                })
                return response
            
            messages.success(request, f"Successfully deposited ${amount} into your account")
            return redirect('dashboard:home')
    else:
        form = DepositForm(user=user)
    
    # Get current time for greeting
    from datetime import datetime
    current_hour = datetime.now().hour
    greeting = "Good Evening"
    if current_hour < 12:
        greeting = "Good Morning"
    elif current_hour < 18:
        greeting = "Good Afternoon"
    
    context = {
        'greeting': greeting,
        'form': form,
        'active_tab': 'deposit'
    }
    
    if request.htmx:
        return render(request, 'banking/partials/deposit_form.html', context)
    return render(request, 'banking/deposit.html', context)

@login_required
def payment_fields(request):
    """Return the appropriate payment fields based on the selected payment method"""
    payment_method = request.GET.get('payment_method', 'credit_card')
    
    context = {
        'payment_method': payment_method
    }
    
    return render(request, 'banking/partials/payment_fields.html', context)
