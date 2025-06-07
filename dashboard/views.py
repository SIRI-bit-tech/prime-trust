from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Q
from django_htmx.http import trigger_client_event
from django.views.decorators.http import require_http_methods
from datetime import timedelta
from django.utils import timezone
from decimal import Decimal
from accounts.models import CustomUser
from banking.models import Account, Transaction, VirtualCard, Notification
from banking.models_bills import Biller, BillPayment, Payee, ScheduledPayment
from banking.models_loans import LoanApplication, LoanAccount, LoanPayment
from .views_investments_insurance import *
# from .views_loans import *

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

@login_required
def accounts(request):
    """View all accounts with details"""
    user = request.user
    
    # Get user's accounts with related data
    accounts = Account.objects.filter(user=user).select_related('user')
    total_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or 0
    
    context = {
        'active_tab': 'accounts',
        'accounts': accounts,
        'total_balance': total_balance,
    }
    
    if request.htmx:
        return render(request, 'dashboard/partials/accounts_content.html', context)
    
    return render(request, 'dashboard/accounts.html', context)

@login_required
def balance_update(request):
    """Update balance via HTMX"""
    user = request.user

    # Get user's accounts
    accounts = Account.objects.filter(user=user)
    total_balance = accounts.aggregate(Sum('balance'))['balance__sum'] or 0

    context = {
        'accounts': accounts,
        'total_balance': total_balance,
    }

    return render(request, 'dashboard/partials/balance_card.html', context)

@login_required
def transactions_update(request):
    """Update recent transactions via HTMX"""
    user = request.user

    # Get user's accounts
    accounts = Account.objects.filter(user=user)

    # Get recent transactions
    transactions = Transaction.objects.filter(
        Q(from_account__in=accounts) | Q(to_account__in=accounts)
    ).order_by('-created_at')[:5]

    context = {
        'transactions': transactions,
    }

    return render(request, 'dashboard/partials/recent_transactions.html', context)

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
        'active_tab': 'transactions',
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
        'active_tab': 'cards',
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
        'active_tab': 'cards',
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
    if request.htmx:
        notifications = Notification.objects.filter(user=request.user, is_read=False)
        notifications.update(is_read=True)
        return HttpResponse(status=200)
    return redirect('dashboard:home')

@login_required
def transfer_money(request):
    """Transfer money between accounts"""
    if request.method == 'POST':
        # Handle transfer logic here
        return JsonResponse({'status': 'success'})
    
    accounts = Account.objects.filter(user=request.user)
    context = {
        'active_tab': 'transfer',
        'accounts': accounts,
    }
    return render(request, 'dashboard/transfer.html', context)

@login_required
def pay_bills(request):
    """Pay bills view"""
    if request.method == 'POST':
        # Handle bill payment logic here
        return JsonResponse({'status': 'success'})
    
    # Get scheduled and recent bill payments
    scheduled_payments = ScheduledPayment.objects.filter(
        user=request.user, 
        status='active'
    ).select_related('payee', 'account')
    
    recent_payments = BillPayment.objects.filter(
        user=request.user
    ).order_by('-scheduled_date')[:10]
    
    # Get billers and payees
    billers = Biller.objects.filter(is_active=True)
    payees = Payee.objects.filter(user=request.user, is_favorite=True)
    
    # Get accounts that can be used for payments
    accounts = Account.objects.filter(
        user=request.user, 
        account_type__in=['checking', 'savings']
    )
    
    context = {
        'active_tab': 'pay-bills',
        'scheduled_payments': scheduled_payments,
        'recent_payments': recent_payments,
        'billers': billers,
        'payees': payees,
        'accounts': accounts,
    }
    return render(request, 'dashboard/pay_bills.html', context)

@login_required
def loans(request):
    """View and manage loans"""
    # Get active loan accounts
    active_loans = LoanAccount.objects.filter(
        application__user=request.user,
        status='active'
    ).select_related('application')
    
    # Get paid off loans
    paid_loans = LoanAccount.objects.filter(
        application__user=request.user,
        status='paid'
    ).select_related('application').order_by('-updated_at')[:5]
    
    # Get loan applications
    pending_applications = LoanApplication.objects.filter(
        user=request.user,
        status__in=['draft', 'submitted', 'under_review']
    ).order_by('-created_at')
    
    # Calculate total loan amount and monthly payment
    total_loan_amount = sum(loan.current_balance for loan in active_loans)
    total_monthly_payment = sum(loan.monthly_payment for loan in active_loans)
    
    # Get accounts for loan payments
    payment_methods = Account.objects.filter(
        user=request.user,
        account_type__in=['checking', 'savings']
    )
    
    # Prepare loan types and terms for the form
    loan_types = dict(LoanApplication.LOAN_TYPES)
    loan_terms = [12, 24, 36, 48, 60]
    
    context = {
        'active_tab': 'loans',
        'active_loans': active_loans,
        'paid_loans': paid_loans,
        'pending_applications': pending_applications,
        'total_loan_amount': total_loan_amount,
        'total_monthly_payment': total_monthly_payment,
        'payment_methods': payment_methods,
        'loan_types': loan_types,
        'loan_terms': loan_terms,
    }
    
    # If HTMX request, return only the loans list partial
    if request.headers.get('HX-Request') == 'true':
        return render(request, 'dashboard/partials/loans_list.html', context)
        
    return render(request, 'dashboard/loans.html', context)

@login_required
def new_loan(request):
    """Display the new loan application form"""
    # Prepare loan types and terms for the form
    loan_types = dict(LoanApplication.LOAN_TYPES)
    loan_terms = [12, 24, 36, 48, 60]
    
    context = {
        'loan_types': loan_types,
        'loan_terms': loan_terms,
    }
    
    return render(request, 'dashboard/partials/loan_application_form.html', context)

@require_http_methods(["POST"])
@login_required
def handle_loan_application(request):
    """Handle loan application form submission"""
    try:
        # Get form data
        amount = float(request.POST.get('amount', 0))
        loan_type = request.POST.get('loan_type')
        term = int(request.POST.get('term', 36))  # Default to 36 months
        employment_status = request.POST.get('employment_status')
        annual_income = float(request.POST.get('annual_income', 0)) if request.POST.get('annual_income') else 0
        
        # Basic validation
        if amount < 1000 or amount > 50000:
            return JsonResponse(
                {'error': 'Loan amount must be between $1,000 and $50,000'}, 
                status=400
            )
            
        if loan_type not in dict(LoanApplication.LOAN_TYPES):
            return JsonResponse(
                {'error': 'Invalid loan type'}, 
                status=400
            )
        
        if not employment_status:
            return JsonResponse(
                {'error': 'Please select your employment status'}, 
                status=400
            )
        
        # Calculate interest rate based on loan type, term, and credit score (simplified)
        base_rates = {
            'personal': 0.08,   # 8%
            'auto': 0.055,      # 5.5%
            'mortgage': 0.045,   # 4.5%
            'education': 0.037,  # 3.7%
            'business': 0.1,     # 10%
        }
        
        # Adjust rate based on term (longer terms have slightly higher rates)
        rate_adjustment = min(0.005 * (term // 12), 0.02)  # Up to 2% increase for longer terms
        interest_rate = base_rates.get(loan_type, 0.1) + rate_adjustment
        
        # Adjust rate based on income (simplified)
        if annual_income > 0:
            # Reduce rate by up to 1% for higher income
            income_adjustment = min(annual_income / 100000 * 0.005, 0.01)
            interest_rate = max(interest_rate - income_adjustment, 0.03)  # Minimum 3% APR
        
        # Calculate monthly payment
        monthly_payment = calculate_monthly_payment(amount, interest_rate, term)
        
        # Create loan application
        application = LoanApplication.objects.create(
            user=request.user,
            loan_type=loan_type,
            amount=amount,
            term_months=term,
            interest_rate=interest_rate,
            monthly_payment=monthly_payment,
            employment_status=employment_status,
            annual_income=annual_income if annual_income > 0 else None,
            status='submitted',
        )
        
        # In a real app, we would have an approval process
        # For demo, we'll auto-approve loans under $10,000
        if amount <= 10000:
            application.status = 'approved'
            application.approved_by = request.user
            application.approved_at = timezone.now()
            application.save()
            
            # Create loan account
            loan_account = LoanAccount.objects.create(
                application=application,
                loan_number=LoanAccount.generate_loan_number(),
                original_amount=amount,
                current_balance=amount,
                interest_rate=interest_rate,
                term_months=term,
                monthly_payment=monthly_payment,
                start_date=timezone.now().date(),
                next_payment_date=timezone.now().date() + timezone.timedelta(days=30),
                status='active',
            )
            
            # Create a notification for the user
            Notification.objects.create(
                user=request.user,
                notification_type='account',
                title='Loan Approved',
                message=f'Your {application.get_loan_type_display()} application for ${amount:,.2f} has been approved.',
            )
            
            message = 'Congratulations! Your loan application has been approved.'
        else:
            # For larger loans, require manual review
            message = 'Your loan application has been submitted for review. We will contact you shortly.'
        
        # Return success response
        return JsonResponse({
            'success': True,
            'message': message,
            'application_id': application.id,
            'approved': application.status == 'approved',
        }, status=201)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {'error': f'Error processing application: {str(e)}'}, 
            status=400
        )

def calculate_monthly_payment(principal, annual_rate, term_months):
    """
    Calculate monthly loan payment using the formula:
    P = (Pv*R*(1+R)^n) / ((1+R)^n - 1)
    Where:
    P = Monthly Payment
    Pv = Present Value (principal)
    R = Monthly Interest Rate (annual rate / 12)
    n = Number of Payments (term in months)
    """
    if annual_rate <= 0 or term_months <= 0 or principal <= 0:
        return 0
        
    monthly_rate = annual_rate / 12
    if monthly_rate == 0:  # Handle interest-free loans
        return principal / term_months
        
    # Calculate monthly payment
    monthly_payment = (principal * monthly_rate * (1 + monthly_rate) ** term_months) / \
                     ((1 + monthly_rate) ** term_months - 1)
    
    return round(monthly_payment, 2)
    if annual_rate == 0:
        return principal / term_months
    monthly_rate = annual_rate / 12
    return principal * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)

@login_required
@login_required
def loan_detail(request, loan_id):
    """View details of a specific loan"""
    try:
        # Get the loan account with related data
        loan = LoanAccount.objects.select_related('application').get(
            id=loan_id,
            application__user=request.user
        )
        
        # Get recent payments
        payments = LoanPayment.objects.filter(
            loan=loan
        ).order_by('-payment_date')[:5]
        
        # Calculate loan progress
        total_paid = LoanPayment.objects.filter(
            loan=loan,
            status='completed'
        ).aggregate(total=Sum('principal_amount'))['total'] or 0
        
        progress = (total_paid / loan.original_amount) * 100 if loan.original_amount > 0 else 0
        
        context = {
            'loan': loan,
            'payments': payments,
            'progress': min(progress, 100),  # Cap at 100%
        }
        
        return render(request, 'dashboard/partials/loan_detail_modal.html', context)
        
    except LoanAccount.DoesNotExist:
        return JsonResponse(
            {'error': 'Loan not found or access denied'}, 
            status=404
        )
    except Exception as e:
        return JsonResponse(
            {'error': f'Error retrieving loan details: {str(e)}'}, 
            status=500
        )

@require_http_methods(["GET", "POST"])
@login_required
def make_loan_payment(request, loan_id):
    """Handle loan payment"""
    try:
        # Get the loan account
        loan = LoanAccount.objects.select_related('application').get(
            id=loan_id,
            application__user=request.user,
            status='active'
        )
        
        # Get user's payment methods
        payment_methods = Account.objects.filter(
            user=request.user,
            account_type__in=['checking', 'savings']
        )
        
        if request.method == 'POST':
            # Process payment
            try:
                amount = Decimal(request.POST.get('amount', 0))
                payment_date = request.POST.get('payment_date')
                payment_method_id = request.POST.get('payment_method')
                is_recurring = request.POST.get('is_recurring') == 'on'
                
                # Validate amount
                if amount <= 0 or amount > loan.current_balance + 1000:  # Allow overpayment up to $1000
                    return JsonResponse(
                        {'error': 'Invalid payment amount'}, 
                        status=400
                    )
                
                # Get payment method
                try:
                    payment_account = Account.objects.get(
                        id=payment_method_id,
                        user=request.user
                    )
                except Account.DoesNotExist:
                    return JsonResponse(
                        {'error': 'Invalid payment method'}, 
                        status=400
                    )
                
                # Check if account has sufficient balance
                if payment_account.balance < amount:
                    return JsonResponse(
                        {'error': 'Insufficient funds in the selected account'}, 
                        status=400
                    )
                
                # Parse payment date
                from datetime import datetime
                try:
                    payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
                except (ValueError, TypeError):
                    payment_date = timezone.now().date()
                
                # Calculate principal and interest portions
                monthly_interest = (loan.current_balance * loan.interest_rate / 12)
                principal_amount = max(amount - monthly_interest, Decimal('0.01'))
                interest_amount = min(monthly_interest, amount - principal_amount)
                
                # Create payment record
                payment = LoanPayment.objects.create(
                    loan=loan,
                    amount=amount,
                    principal_amount=principal_amount,
                    interest_amount=interest_amount,
                    payment_date=payment_date,
                    due_date=loan.next_payment_date,
                    payment_method='bank_transfer',
                    status='completed',
                    processed_by=request.user,
                    processed_at=timezone.now()
                )
                
                # Update loan balance and next payment date
                loan.current_balance -= principal_amount
                
                # If this pays off the loan
                if loan.current_balance <= 0:
                    loan.status = 'paid'
                    loan.paid_off_date = timezone.now().date()
                    
                    # Create a notification for loan payoff
                    Notification.objects.create(
                        user=request.user,
                        notification_type='account',
                        title='Loan Paid Off',
                        message=f'Congratulations! Your {loan.application.get_loan_type_display()} has been fully paid off.',
                    )
                else:
                    # Update next payment date (30 days from last payment or due date, whichever is later)
                    next_payment = min(
                        payment_date + timezone.timedelta(days=30),
                        loan.next_payment_date + timezone.timedelta(days=30)
                    )
                    loan.next_payment_date = next_payment
                
                loan.save()
                
                # Deduct from payment account
                payment_account.balance -= amount
                payment_account.save()
                
                # Create transaction record
                transaction = Transaction.objects.create(
                    from_account=payment_account,
                    to_account=loan.account,
                    amount=amount,
                    transaction_type='payment',
                    description=f'Loan Payment - {loan.application.get_loan_type_display()}',
                    reference=f'LOANPMT-{payment.id}',
                    status='completed'
                )
                
                # Create notification
                Notification.objects.create(
                    user=request.user,
                    notification_type='transaction',
                    title='Loan Payment Processed',
                    message=f'Payment of ${amount:,.2f} for your {loan.application.get_loan_type_display()} has been processed.',
                    related_transaction=transaction
                )
                
                # If this is an HTMX request, return the updated loan details
                if request.headers.get('HX-Request') == 'true':
                    return loan_detail(request, loan_id)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Payment processed successfully',
                    'payment_id': payment.id
                }, status=201)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                return JsonResponse(
                    {'error': f'Error processing payment: {str(e)}'}, 
                    status=400
                )
        
        # GET request - show payment form
        context = {
            'loan': loan,
            'payment_methods': payment_methods,
            'min_payment': loan.monthly_payment,
            'max_payment': min(loan.current_balance + 1000, loan.current_balance * 1.1),  # Allow up to 10% overpayment
        }
        
        return render(request, 'dashboard/partials/loan_payment_form.html', context)
        
    except LoanAccount.DoesNotExist:
        return JsonResponse(
            {'error': 'Loan not found, already paid off, or access denied'}, 
            status=404
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {'error': f'Error processing request: {str(e)}'}, 
            status=500
        )

@login_required
def loan_detail(request, loan_id):
    """View details of a specific loan"""
    loan = get_object_or_404(
        LoanAccount.objects.select_related('application'),
        id=loan_id,
        application__user=request.user
    )
    
    # Get payment history
    payments = LoanPayment.objects.filter(
        loan_account=loan
    ).order_by('-payment_date')
    
    # Calculate loan progress
    progress = ((loan.original_amount - loan.current_balance) / loan.original_amount) * 100
    
    context = {
        'loan': loan,
        'payments': payments,
        'progress': progress,
    }
    
    if request.headers.get('HX-Request') == 'true':
        return render(request, 'dashboard/partials/loan_detail_modal.html', context)
        
    return render(request, 'dashboard/loan_detail.html', context)

@login_required
def make_loan_payment(request, loan_id):
    """Handle loan payment"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    loan = get_object_or_404(
        LoanAccount,
        id=loan_id,
        application__user=request.user,
        status='active'
    )
    
    try:
        amount = Decimal(request.POST.get('amount', 0))
        from_account_id = request.POST.get('from_account')
        
        # Validate amount
        if amount <= 0:
            return JsonResponse(
                {'error': 'Payment amount must be greater than zero'}, 
                status=400
            )
            
        # Get source account
        from_account = get_object_or_404(
            Account,
            id=from_account_id,
            user=request.user
        )
        
        # Check if account has sufficient balance
        if from_account.balance < amount:
            return JsonResponse(
                {'error': 'Insufficient funds'}, 
                status=400
            )
        
        # Process payment
        with transaction.atomic():
            # Deduct from account
            from_account.balance -= amount
            from_account.save()
            
            # Apply to loan
            interest_amount = min(amount, loan.current_balance * (loan.interest_rate / 12))
            principal_amount = amount - interest_amount
            
            loan.current_balance -= principal_amount
            loan.amount_paid = (loan.amount_paid or 0) + amount
            loan.next_payment_date = loan.next_payment_date + timedelta(days=30)
            
            # Mark as paid if balance is zero
            if loan.current_balance <= 0:
                loan.status = 'paid'
                loan.paid_date = timezone.now().date()
            
            loan.save()
            
            # Record transaction
            transaction = Transaction.objects.create(
                from_account=from_account,
                to_account=loan.account,
                amount=amount,
                transaction_type='loan_payment',
                description=f"Loan Payment - {loan.application.get_loan_type_display()}",
                status='completed'
            )
            
            # Record loan payment
            loan_payment = LoanPayment.objects.create(
                loan_account=loan,
                amount=amount,
                principal_amount=principal_amount,
                interest_amount=interest_amount,
                payment_date=timezone.now().date(),
                transaction=transaction
            )
            
            # Create notification
            Notification.objects.create(
                user=request.user,
                title="Loan Payment Processed",
                message=f"Your payment of ${amount:,.2f} has been applied to your {loan.application.get_loan_type_display()} loan.",
                notification_type='transaction',
                related_id=transaction.id
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Payment processed successfully',
                'new_balance': float(loan.current_balance),
                'next_payment': loan.next_payment_date.strftime('%Y-%m-%d')
            })
            
    except Exception as e:
        return JsonResponse(
            {'error': f'Error processing payment: {str(e)}'}, 
            status=400
        )

@login_required
def investments(request):
    """View investments"""
    # TODO: Implement investments functionality
    context = {
        'active_tab': 'investments',
        'investments': [],
    }
    return render(request, 'dashboard/investments.html', context)

@login_required
def insurance(request):
    """View insurance policies"""
    # TODO: Implement insurance functionality
    context = {
        'active_tab': 'insurance',
        'policies': [],
    }
    return render(request, 'dashboard/insurance.html', context)

@login_required
def services(request):
    """View additional banking services"""
    context = {
        'active_tab': 'services',
    }
    return render(request, 'dashboard/services.html', context)

@login_required
def metrics_update(request):
    """Update transaction metrics via HTMX"""
    user = request.user
    accounts = Account.objects.filter(user=user)
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
    context = {
        'transactions_count': transactions_count,
        'money_received': money_received,
        'money_spent': money_spent,
    }
    return render(request, 'dashboard/partials/transaction_metrics.html', context)
