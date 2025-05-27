from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Q
from django_htmx.http import trigger_client_event

from accounts.models import CustomUser
from banking.models import Account, Transaction, VirtualCard, Notification

@login_required
def home(request):
    """Dashboard home view"""
    user = request.user
    
    # Get user's accounts
    accounts = Account.objects.filter(user=user)
    total_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or 0
    
    # Get recent transactions
    transactions = Transaction.objects.filter(
        Q(from_account__in=accounts) | Q(to_account__in=accounts)
    ).order_by('-created_at')[:5]
    
    # Get virtual cards
    virtual_cards = VirtualCard.objects.filter(user=user, is_active=True)
    
    # Get unread notifications
    notifications = Notification.objects.filter(user=user, is_read=False)[:5]
    
    context = {
        'accounts': accounts,
        'total_balance': total_balance,
        'transactions': transactions,
        'virtual_cards': virtual_cards,
        'notifications': notifications,
    }
    
    if request.htmx:
        if request.htmx.trigger == 'refresh-balance':
            return render(request, 'dashboard/partials/balance_card.html', context)
        elif request.htmx.trigger == 'refresh-transactions':
            return render(request, 'dashboard/partials/recent_transactions.html', context)
        elif request.htmx.trigger == 'refresh-notifications':
            return render(request, 'dashboard/partials/notifications.html', context)
    
    return render(request, 'dashboard/home.html', context)

@login_required
def transactions(request):
    """View all transactions"""
    user = request.user
    accounts = Account.objects.filter(user=user)
    
    # Get all transactions for user's accounts
    transactions = Transaction.objects.filter(
        Q(from_account__in=accounts) | Q(to_account__in=accounts)
    ).order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        transactions = transactions.filter(status=status_filter)
    
    # Filter by transaction type if provided
    type_filter = request.GET.get('type')
    if type_filter and type_filter != 'all':
        transactions = transactions.filter(transaction_type=type_filter)
    
    context = {
        'transactions': transactions,
        'status_filter': status_filter or 'all',
        'type_filter': type_filter or 'all',
    }
    
    if request.htmx:
        return render(request, 'dashboard/partials/transactions_list.html', context)
    
    return render(request, 'dashboard/transactions.html', context)

@login_required
def cards(request):
    """View virtual cards"""
    user = request.user
    virtual_cards = VirtualCard.objects.filter(user=user)
    
    context = {
        'virtual_cards': virtual_cards,
    }
    
    if request.htmx:
        return render(request, 'dashboard/partials/cards_list.html', context)
    
    return render(request, 'dashboard/cards.html', context)

@login_required
def card_details(request, card_id):
    """View details of a specific virtual card"""
    user = request.user
    card = get_object_or_404(VirtualCard, id=card_id, user=user)
    
    context = {
        'card': card,
    }
    
    if request.htmx:
        return render(request, 'dashboard/partials/card_details.html', context)
    
    return render(request, 'dashboard/card_details.html', context)

@login_required
def notifications(request):
    """View all notifications"""
    user = request.user
    notifications = Notification.objects.filter(user=user).order_by('-created_at')
    
    context = {
        'notifications': notifications,
    }
    
    if request.htmx:
        return render(request, 'dashboard/partials/notifications_list.html', context)
    
    return render(request, 'dashboard/notifications.html', context)

@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    user = request.user
    notification = get_object_or_404(Notification, id=notification_id, user=user)
    
    notification.is_read = True
    notification.save()
    
    response = HttpResponse()
    if request.htmx:
        trigger_client_event(response, 'notificationRead', {'id': notification_id})
    
    return response

@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    user = request.user
    Notification.objects.filter(user=user, is_read=False).update(is_read=True)
    
    response = HttpResponse()
    if request.htmx:
        trigger_client_event(response, 'allNotificationsRead')
    
    return response
