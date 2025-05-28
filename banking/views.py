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
            recipient_email = form.cleaned_data['recipient_email']
            from_account = form.cleaned_data['from_account']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            
            try:
                # Find recipient user and account
                recipient = CustomUser.objects.get(email=recipient_email)
                recipient_account = Account.objects.filter(user=recipient).first()
                
                if not recipient_account:
                    # Create a checking account for the recipient if they don't have one
                    recipient_account = Account.objects.create(
                        user=recipient,
                        account_number=f"CH{uuid.uuid4().hex[:16].upper()}",
                        account_type='checking',
                        balance=0
                    )
                
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
                        message=f"You sent ${amount} to {recipient.get_full_name()}",
                        related_transaction=new_transaction
                    )
                    
                    Notification.objects.create(
                        user=recipient,
                        notification_type='transaction',
                        title='Money Received',
                        message=f"You received ${amount} from {user.get_full_name()}",
                        related_transaction=new_transaction
                    )
                
                if request.htmx:
                    response = HttpResponse()
                    trigger_client_event(response, 'transactionComplete', {
                        'message': f"Successfully sent ${amount} to {recipient.get_full_name()}"
                    })
                    return response
                
                messages.success(request, f"Successfully sent ${amount} to {recipient.get_full_name()}")
                return redirect('dashboard:transactions')
                
            except CustomUser.DoesNotExist:
                if request.htmx:
                    response = HttpResponse("<div class='text-red-600'>Recipient not found</div>")
                    return response
                messages.error(request, 'Recipient not found')
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
    """Check if recipient exists (HTMX endpoint)"""
    recipient_email = request.GET.get('recipient_email', '')
    
    if recipient_email:
        try:
            recipient = CustomUser.objects.get(email=recipient_email)
            return HttpResponse(
                f"<div class='text-green-600'>Recipient found: {recipient.get_full_name()}</div>"
            )
        except CustomUser.DoesNotExist:
            return HttpResponse(
                "<div class='text-red-600'>Recipient not found</div>"
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
        form = DepositForm(request.POST, user=user)
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
