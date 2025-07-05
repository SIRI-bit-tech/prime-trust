from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
import requests
import uuid
from datetime import datetime
from .models import BitcoinWallet, Transaction, Account, Notification
from .forms import SendBitcoinForm
from .utils import send_transaction_notification

def update_btc_price():
    """Update Bitcoin price in cache"""
    try:
        response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd')
        if response.status_code == 200:
            btc_price = Decimal(str(response.json()['bitcoin']['usd']))
            cache.set('btc_price_usd', btc_price, timeout=300)  # Cache for 5 minutes
            return btc_price
    except Exception as e:
        print(f"Error fetching BTC price: {e}")
    return None

@login_required
@require_http_methods(["GET"])
def receive_bitcoin(request):
    """Display Bitcoin receiving address and QR code."""
    try:
        bitcoin_wallet = BitcoinWallet.objects.get(user=request.user)
        return render(request, 'banking/partials/receive_bitcoin.html', {
            'bitcoin_wallet': bitcoin_wallet
        })
    except BitcoinWallet.DoesNotExist:
        return render(request, 'banking/partials/receive_bitcoin.html', {
            'bitcoin_wallet': None
        })

@login_required
def send_bitcoin_page(request):
    """Display the Bitcoin sending page."""
    user = request.user
    
    # Get user's Bitcoin wallet and update price
    try:
        bitcoin_wallet = BitcoinWallet.objects.get(user=user)
        btc_price = update_btc_price() or bitcoin_wallet.btc_price_usd
        bitcoin_wallet.btc_price_usd = btc_price
        bitcoin_wallet.save()
    except BitcoinWallet.DoesNotExist:
        bitcoin_wallet = None
        btc_price = Decimal('0.00')
    
    # Get user's fiat accounts
    accounts = Account.objects.filter(user=user)
    total_fiat_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or Decimal('0.00')
    
    # Get current time for greeting
    current_hour = datetime.now().hour
    greeting = "Good Evening"
    if current_hour < 12:
        greeting = "Good Morning"
    elif current_hour < 18:
        greeting = "Good Afternoon"
    
    if request.method == 'POST':
        form = SendBitcoinForm(request.POST, user=user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Extract form data
                    balance_source = form.cleaned_data['balance_source']
                    amount = form.cleaned_data['amount']
                    wallet_address = form.cleaned_data['wallet_address']
                    
                    # Create transaction reference
                    transaction_ref = f"BTC{uuid.uuid4().hex[:8].upper()}"
                    
                    # Calculate amounts
                    if balance_source == 'bitcoin':
                        # Sending from Bitcoin balance
                        btc_amount = amount
                        usd_amount = amount * btc_price
                        
                        # Deduct from Bitcoin wallet
                        bitcoin_wallet.balance -= btc_amount
                        bitcoin_wallet.save()
                        
                        from_account = None
                        to_account = None
                        
                    else:  # fiat
                        # Sending from fiat balance (buying Bitcoin to send)
                        btc_amount = amount
                        usd_amount = amount * btc_price
                        
                        # Deduct from primary account
                        primary_account = accounts.filter(account_type='checking').first()
                        if primary_account and primary_account.balance >= usd_amount:
                            primary_account.balance -= usd_amount
                            primary_account.save()
                            from_account = primary_account
                            to_account = None
                        else:
                            raise ValueError("Insufficient fiat balance")
                    
                    # Create transaction record
                    new_transaction = Transaction.objects.create(
                        from_account=from_account,
                        to_account=to_account,
                        amount=usd_amount,
                        bitcoin_amount=btc_amount,
                        bitcoin_address=wallet_address,
                        transaction_type='bitcoin_send',
                        status='pending',
                        description=f"Bitcoin sent to {wallet_address}",
                        reference=transaction_ref,
                        balance_source=balance_source
                    )
                    
                    # Simulate Bitcoin API call (replace with real API)
                    bitcoin_tx_hash = simulate_bitcoin_send(wallet_address, btc_amount)
                    
                    if bitcoin_tx_hash:
                        # Update transaction with Bitcoin tx hash
                        new_transaction.bitcoin_tx_hash = bitcoin_tx_hash
                        new_transaction.status = 'completed'
                        new_transaction.save()
                        
                        # Create notification
                        Notification.objects.create(
                            user=user,
                            notification_type='transaction',
                            title='Bitcoin Sent Successfully',
                            message=f"You sent {btc_amount:.8f} BTC to {wallet_address}",
                            related_transaction=new_transaction
                        )
                        
                        messages.success(request, f"Successfully sent {btc_amount:.8f} BTC to {wallet_address}")
                        return redirect('dashboard:transactions')
                    else:
                        # Transaction failed
                        new_transaction.status = 'failed'
                        new_transaction.save()
                        
                        # Refund the amounts
                        if balance_source == 'bitcoin':
                            bitcoin_wallet.balance += btc_amount
                            bitcoin_wallet.save()
                        else:
                            primary_account.balance += usd_amount
                            primary_account.save()
                        
                        messages.error(request, 'Bitcoin transaction failed. Please try again.')
                        
            except Exception as e:
                messages.error(request, f'Transaction failed: {str(e)}')
    else:
        form = SendBitcoinForm(user=user)
    
    context = {
        'form': form,
        'bitcoin_wallet': bitcoin_wallet,
        'total_fiat_balance': total_fiat_balance,
        'btc_price': btc_price,
        'greeting': greeting,
    }
    
    return render(request, 'banking/send_bitcoin.html', context)


def simulate_bitcoin_send(wallet_address, amount):
    """Simulate Bitcoin API call - replace with real Bitcoin API integration."""
    # This would be replaced with actual Bitcoin API calls
    # For demonstration, we'll simulate a successful transaction
    try:
        # Simulate API call delay
        import time
        time.sleep(1)
        
        # Generate a fake transaction hash
        import hashlib
        tx_data = f"{wallet_address}{amount}{datetime.now().timestamp()}"
        tx_hash = hashlib.sha256(tx_data.encode()).hexdigest()
        
        return tx_hash
        
    except Exception as e:
        print(f"Bitcoin API error: {e}")
        return None


@login_required
@require_http_methods(["GET"])
def send_bitcoin(request):
    """Handle Bitcoin sending modal requests - redirect to page."""
    return redirect('banking:send_bitcoin_page')

@login_required
@require_http_methods(["GET", "POST"])
def swap_bitcoin(request):
    """Handle Bitcoin swap operations."""
    return HttpResponse(
        '<div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">'
        'Bitcoin swap feature coming soon!'
        '</div>'
    ) 