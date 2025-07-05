from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q
from django_htmx.http import trigger_client_event
from django.views.decorators.http import require_http_methods
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal
from django.core.cache import cache
from accounts.models import CustomUser
from banking.models import Account, Transaction, VirtualCard, Notification, BitcoinWallet
from banking.models_bills import Biller, BillPayment, Payee, ScheduledPayment
from banking.models_loans import LoanApplication, LoanAccount, LoanPayment
from banking.views_bitcoin import update_btc_price
from .views_investments_insurance import *
from django.conf import settings

@login_required
def home(request):
    """Dashboard home view"""
    user = request.user

    # Get user's accounts
    accounts = Account.objects.filter(user=user)
    total_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')

    # Get Bitcoin wallet and update price
    try:
        bitcoin_wallet = BitcoinWallet.objects.get(user=user)
        btc_price = update_btc_price() or Decimal('0.00')
        bitcoin_balance_usd = bitcoin_wallet.balance * btc_price
        bitcoin_wallet.balance_usd = bitcoin_balance_usd  # Add USD value to the wallet object
    except BitcoinWallet.DoesNotExist:
        bitcoin_wallet = None
        bitcoin_balance_usd = Decimal('0.00')
        btc_price = Decimal('0.00')

    # Keep Bitcoin balance separate from fiat balance

    # Get recent transactions
    transactions = Transaction.objects.filter(
        Q(from_account__in=accounts) | Q(to_account__in=accounts)
    ).order_by('-created_at')[:5]

    # Get virtual cards
    virtual_cards = VirtualCard.objects.filter(user=user, is_active=True)

    # Get unread notifications
    notifications = Notification.objects.filter(user=user, is_read=False)[:5]

    # Transaction metrics
    transactions_count = Transaction.objects.filter(
        Q(from_account__in=accounts) | Q(to_account__in=accounts)
    ).count()
    money_received = Transaction.objects.filter(
        to_account__in=accounts,
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    money_spent = Transaction.objects.filter(
        from_account__in=accounts,
        status='completed'
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

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
        'active_tab': 'home',
        'accounts': accounts,
        'total_balance': total_balance,
        'bitcoin_wallet': bitcoin_wallet,
        'btc_price_usd': btc_price,
        'transactions': transactions,
        'virtual_cards': virtual_cards,
        'notifications': notifications,
        'transactions_count': transactions_count,
        'money_received': money_received,
        'money_spent': money_spent,
    }

    if request.htmx:
        if request.htmx.trigger == 'refresh-balance':
            return render(request, 'dashboard/partials/balance_card.html', context)
        elif request.htmx.trigger == 'refresh-transactions':
            return render(request, 'dashboard/partials/recent_transactions.html', context)
        elif request.htmx.trigger == 'refresh-notifications':
            return render(request, 'dashboard/partials/notifications.html', context)
        elif request.htmx.trigger == 'refresh-metrics':
            return render(request, 'dashboard/partials/transaction_metrics.html', context)

    return render(request, 'dashboard/home.html', context) 