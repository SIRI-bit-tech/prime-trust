from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.core.cache import cache
from decimal import Decimal
import requests
from .models import BitcoinWallet

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
@require_http_methods(["GET", "POST"])
def send_bitcoin(request):
    """Handle Bitcoin sending form and submission."""
    try:
        bitcoin_wallet = BitcoinWallet.objects.get(user=request.user)
        
        if request.method == 'POST':
            recipient_address = request.POST.get('recipient_address')
            amount = Decimal(request.POST.get('amount', '0'))
            
            if not recipient_address or amount <= 0:
                return HttpResponse(
                    '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
                    'Please provide a valid recipient address and amount.'
                    '</div>'
                )
            
            if amount > bitcoin_wallet.balance:
                return HttpResponse(
                    '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">'
                    'Insufficient balance for this transaction.'
                    '</div>'
                )
            
            # Here you would integrate with your Bitcoin payment processor
            # For now, we'll just show a success message
            return HttpResponse(
                '<div class="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">'
                'Transaction initiated successfully! Please wait for confirmation.'
                '</div>'
            )
            
        return render(request, 'banking/partials/send_bitcoin.html', {
            'bitcoin_wallet': bitcoin_wallet
        })
    except BitcoinWallet.DoesNotExist:
        return render(request, 'banking/partials/send_bitcoin.html', {
            'bitcoin_wallet': None
        })

@login_required
@require_http_methods(["GET", "POST"])
def swap_bitcoin(request):
    """Handle Bitcoin swap operations."""
    return HttpResponse(
        '<div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">'
        'Bitcoin swap feature coming soon!'
        '</div>'
    ) 