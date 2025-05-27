from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django_htmx.http import trigger_client_event
import uuid

from accounts.models import CustomUser
from .models import Account, Transaction, VirtualCard, Notification
from .forms import SendMoneyForm

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
                    
                    # Create transaction record
                    transaction_ref = f"TRF{uuid.uuid4().hex[:8].upper()}"
                    new_transaction = Transaction.objects.create(
                        from_account=from_account,
                        to_account=recipient_account,
                        amount=amount,
                        transaction_type='transfer',
                        status='completed',  # Auto-approve for demo purposes
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
    
    context = {
        'form': form,
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
    user = request.user
    accounts = Account.objects.filter(user=user)
    
    # Use a filter expression with Q objects for OR condition
    filter_condition = Q(id=transaction_id) & (Q(from_account__in=accounts) | Q(to_account__in=accounts))
    transaction = get_object_or_404(Transaction, filter_condition)
    
    context = {
        'transaction': transaction,
    }
    
    return render(request, 'banking/partials/transaction_details.html', context)
