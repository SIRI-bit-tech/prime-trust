from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from banking.models import Account, Transaction, Notification, BitcoinWallet, VirtualCard
from banking.models_loans import LoanApplication, LoanAccount, LoanPayment
from banking.models_investments_insurance import InvestmentAccount, Investment, InsurancePolicy, InsuranceClaim
from banking.models_bills import Biller, BillPayment, Payee, ScheduledPayment
from .models import WebhookEndpoint, WebhookEvent, WebhookDelivery, WebhookTemplate, WebhookLog
from .serializers import (
    AccountSerializer, TransactionSerializer, MoneyTransferSerializer,
    TransactionCreateSerializer, BitcoinWalletSerializer, BitcoinSendSerializer,
    BitcoinSwapSerializer, LoanApplicationSerializer, LoanAccountSerializer,
    LoanPaymentSerializer, LoanPaymentCreateSerializer, InvestmentAccountSerializer,
    InvestmentSerializer, InvestmentCreateSerializer, InsurancePolicySerializer,
    InsuranceClaimSerializer, InsuranceClaimCreateSerializer, BillerSerializer,
    BillPaymentSerializer, BillPaymentCreateSerializer, PayeeSerializer,
    ScheduledPaymentSerializer, ScheduledPaymentCreateSerializer, NotificationSerializer,
    AccountSummarySerializer, TransactionAnalyticsSerializer, VirtualCardCreateSerializer,
    VirtualCardSerializer, CardTransactionSerializer, WebhookEndpointSerializer,
    WebhookEndpointCreateSerializer, WebhookEventSerializer, WebhookDeliverySerializer,
    WebhookTestSerializer, WebhookRetrySerializer, WebhookStatsSerializer,
    WebhookTemplateSerializer, WebhookLogSerializer
)
from banking.utils import generate_reference_number
import random
import string
from django.db import models
from django.db.models import Sum, Q, Count
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class AccountViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for bank accounts.
    Provides list and detail views for user's accounts.
    """
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return accounts for the current user only."""
        return Account.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def balance(self, request, pk=None):
        """Get account balance."""
        account = self.get_object()
        return Response({
            'account_number': account.account_number,
            'balance': account.balance,
            'last_updated': account.updated_at
        })
    
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get account transactions."""
        account = self.get_object()
        transactions = Transaction.objects.filter(
            models.Q(from_account=account) | models.Q(to_account=account)
        ).order_by('-created_at')
        
        # Add pagination
        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = TransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def deposit(self, request, pk=None):
        """Deposit money to account."""
        account = self.get_object()
        serializer = TransactionCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            amount = serializer.validated_data['amount']
            description = serializer.validated_data.get('description', 'Deposit')
            
            # Create deposit transaction
            with transaction.atomic():
                # Create the transaction record
                trans = Transaction.objects.create(
                    user=request.user,
                    to_account=account,
                    transaction_type='deposit',
                    amount=amount,
                    description=description,
                    reference=generate_reference_number('DEP'),
                    status='completed'
                )
                
                # Update account balance
                account.balance += amount
                account.save()
            
            return Response({
                'message': 'Deposit successful',
                'transaction': TransactionSerializer(trans).data,
                'new_balance': account.balance
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        """Transfer money from this account to another account."""
        sender_account = self.get_object()
        serializer = MoneyTransferSerializer(data=request.data)
        
        if serializer.is_valid():
            recipient_account_number = serializer.validated_data['recipient_account']
            amount = serializer.validated_data['amount']
            description = serializer.validated_data.get('description', 'Money Transfer')
            transaction_pin = serializer.validated_data['transaction_pin']
            
            # Verify transaction PIN
            user_profile = request.user.profile
            if not user_profile.check_transaction_pin(transaction_pin):
                return Response(
                    {'error': 'Invalid transaction PIN'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if sender has sufficient balance
            if sender_account.balance < amount:
                return Response(
                    {'error': 'Insufficient funds'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get recipient account
            try:
                recipient_account = Account.objects.get(
                    account_number=recipient_account_number
                )
            except Account.DoesNotExist:
                return Response(
                    {'error': 'Recipient account not found'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Prevent self-transfer
            if sender_account == recipient_account:
                return Response(
                    {'error': 'Cannot transfer to the same account'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Process the transfer
            with transaction.atomic():
                reference_number = generate_reference_number()
                
                # Create transaction record
                sender_transaction = Transaction.objects.create(
                    user=request.user,
                    from_account=sender_account,
                    to_account=recipient_account,
                    transaction_type='transfer',
                    amount=amount,
                    description=f"Transfer to {recipient_account.account_number}: {description}",
                    reference=reference_number,
                    status='completed'
                )
                
                # Update balances
                sender_account.balance -= amount
                recipient_account.balance += amount
                sender_account.save()
                recipient_account.save()
            
            return Response({
                'message': 'Transfer successful',
                'transaction': TransactionSerializer(sender_transaction).data,
                'new_balance': sender_account.balance,
                'recipient': {
                    'account_number': recipient_account.account_number,
                    'name': f"{recipient_account.user.first_name} {recipient_account.user.last_name}"
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for transactions.
    Provides list and detail views for user's transactions.
    """
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return transactions for the current user's accounts only."""
        user_accounts = Account.objects.filter(user=self.request.user)
        return Transaction.objects.filter(
            models.Q(from_account__in=user_accounts) | 
            models.Q(to_account__in=user_accounts) |
            models.Q(user=self.request.user)
        ).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent transactions (last 10)."""
        transactions = self.get_queryset()[:10]
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get transaction summary for the current month."""
        user_accounts = Account.objects.filter(user=request.user)
        current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        transactions = Transaction.objects.filter(
            models.Q(from_account__in=user_accounts) | 
            models.Q(to_account__in=user_accounts) |
            models.Q(user=request.user),
            created_at__gte=current_month
        )
        
        total_deposits = sum(
            t.amount for t in transactions if t.transaction_type == 'deposit'
        )
        total_withdrawals = sum(
            t.amount for t in transactions if t.transaction_type == 'withdrawal'
        )
        total_transfers_out = sum(
            t.amount for t in transactions if t.transaction_type == 'transfer' and t.from_account in user_accounts
        )
        total_transfers_in = sum(
            t.amount for t in transactions if t.transaction_type == 'transfer' and t.to_account in user_accounts
        )
        
        return Response({
            'period': f"{current_month.strftime('%B %Y')}",
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
            'total_transfers_out': total_transfers_out,
            'total_transfers_in': total_transfers_in,
            'net_change': total_deposits + total_transfers_in - total_withdrawals - total_transfers_out,
            'transaction_count': transactions.count()
        })


class BankingViewSet(viewsets.GenericViewSet):
    """
    ViewSet for general banking operations.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def account_info(self, request):
        """Get user's account information."""
        try:
            account = Account.objects.get(user=request.user)
            serializer = AccountSerializer(account)
            return Response(serializer.data)
        except Account.DoesNotExist:
            return Response(
                {'error': 'No account found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'], permission_classes=[])
    def verify_account(self, request):
        """Verify if an account number exists."""
        account_number = request.data.get('account_number')
        
        if not account_number:
            return Response(
                {'error': 'Account number is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            account = Account.objects.get(account_number=account_number)
            return Response({
                'valid': True,
                'account_holder': f"{account.user.first_name} {account.user.last_name}",
                'account_type': account.account_type
            })
        except Account.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'Account not found'
            })
    
    @action(detail=False, methods=['get'])
    def dashboard_data(self, request):
        """Get dashboard data for the user."""
        try:
            account = Account.objects.get(user=request.user)
            recent_transactions = Transaction.objects.filter(
                models.Q(from_account=account) | 
                models.Q(to_account=account) |
                models.Q(user=request.user)
            ).order_by('-created_at')[:5]
            
            return Response({
                'account': AccountSerializer(account).data,
                'recent_transactions': TransactionSerializer(recent_transactions, many=True).data,
                'account_holder': f"{request.user.first_name} {request.user.last_name}"
            })
        except Account.DoesNotExist:
            return Response(
                {'error': 'No account found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


# ====== BITCOIN/CRYPTOCURRENCY VIEWSETS ======

class BitcoinViewSet(viewsets.ModelViewSet):
    """Bitcoin wallet management and operations"""
    serializer_class = BitcoinWalletSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BitcoinWallet.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def wallet_info(self, request):
        """Get user's Bitcoin wallet information"""
        try:
            wallet = BitcoinWallet.objects.get(user=request.user)
            serializer = self.get_serializer(wallet)
            return Response(serializer.data)
        except BitcoinWallet.DoesNotExist:
            return Response(
                {'error': 'No Bitcoin wallet found. Create one first.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def send_bitcoin(self, request):
        """Send Bitcoin to another address"""
        serializer = BitcoinSendSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    wallet = BitcoinWallet.objects.get(user=request.user)
                    amount = serializer.validated_data['amount']
                    wallet_address = serializer.validated_data['wallet_address']
                    balance_source = serializer.validated_data['balance_source']
                    
                    # Update BTC price
                    from banking.views_bitcoin import update_btc_price
                    btc_price = update_btc_price() or wallet.btc_price_usd
                    wallet.btc_price_usd = btc_price
                    wallet.save()
                    
                    # Calculate USD amount
                    usd_amount = amount * btc_price
                    
                    # Validate sufficient balance
                    if balance_source == 'bitcoin':
                        if wallet.balance < amount:
                            return Response(
                                {'error': 'Insufficient Bitcoin balance'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        wallet.balance -= amount
                        wallet.save()
                        from_account = None
                    else:  # fiat
                        primary_account = Account.objects.filter(
                            user=request.user, 
                            account_type='checking'
                        ).first()
                        if not primary_account or primary_account.balance < usd_amount:
                            return Response(
                                {'error': 'Insufficient fiat balance'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        primary_account.balance -= usd_amount
                        primary_account.save()
                        from_account = primary_account
                    
                    # Create transaction record
                    tx = Transaction.objects.create(
                        user=request.user,
                        from_account=from_account,
                        amount=usd_amount,
                        bitcoin_amount=amount,
                        bitcoin_address=wallet_address,
                        transaction_type='bitcoin_send',
                        status='completed',
                        description=f"Bitcoin sent to {wallet_address}",
                        balance_source=balance_source
                    )
                    
                    return Response({
                        'message': 'Bitcoin sent successfully',
                        'transaction_id': tx.id,
                        'amount': amount,
                        'usd_amount': usd_amount,
                        'wallet_address': wallet_address
                    })
                    
            except BitcoinWallet.DoesNotExist:
                return Response(
                    {'error': 'Bitcoin wallet not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def swap_bitcoin(self, request):
        """Buy or sell Bitcoin"""
        serializer = BitcoinSwapSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    wallet = BitcoinWallet.objects.get(user=request.user)
                    swap_type = serializer.validated_data['swap_type']
                    amount = serializer.validated_data['amount']
                    account_id = serializer.validated_data['account_id']
                    
                    account = get_object_or_404(Account, id=account_id, user=request.user)
                    
                    # Update BTC price
                    from banking.views_bitcoin import update_btc_price
                    btc_price = update_btc_price() or wallet.btc_price_usd
                    wallet.btc_price_usd = btc_price
                    wallet.save()
                    
                    usd_amount = amount * btc_price
                    
                    if swap_type == 'buy':
                        # Buy Bitcoin with fiat
                        if account.balance < usd_amount:
                            return Response(
                                {'error': 'Insufficient fiat balance'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        account.balance -= usd_amount
                        wallet.balance += amount
                        description = f"Bought {amount} BTC"
                    else:  # sell
                        # Sell Bitcoin for fiat
                        if wallet.balance < amount:
                            return Response(
                                {'error': 'Insufficient Bitcoin balance'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        wallet.balance -= amount
                        account.balance += usd_amount
                        description = f"Sold {amount} BTC"
                    
                    account.save()
                    wallet.save()
                    
                    # Create transaction record
                    tx = Transaction.objects.create(
                        user=request.user,
                        from_account=account if swap_type == 'buy' else None,
                        to_account=account if swap_type == 'sell' else None,
                        amount=usd_amount,
                        bitcoin_amount=amount,
                        transaction_type=f'bitcoin_{swap_type}',
                        status='completed',
                        description=description
                    )
                    
                    return Response({
                        'message': f'Bitcoin {swap_type} completed successfully',
                        'transaction_id': tx.id,
                        'btc_amount': amount,
                        'usd_amount': usd_amount,
                        'new_btc_balance': wallet.balance,
                        'new_account_balance': account.balance
                    })
                    
            except BitcoinWallet.DoesNotExist:
                return Response(
                    {'error': 'Bitcoin wallet not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def price_info(self, request):
        """Get current Bitcoin price information"""
        try:
            from banking.views_bitcoin import update_btc_price
            btc_price = update_btc_price()
            if btc_price:
                return Response({
                    'btc_price_usd': btc_price,
                    'last_updated': timezone.now()
                })
            return Response(
                {'error': 'Unable to fetch Bitcoin price'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


# ====== LOAN MANAGEMENT VIEWSETS ======

class LoanApplicationViewSet(viewsets.ModelViewSet):
    """Loan application management"""
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return LoanApplication.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit loan application for review"""
        application = self.get_object()
        if application.status == 'draft':
            application.status = 'submitted'
            application.save()
            return Response({'message': 'Application submitted successfully'})
        return Response(
            {'error': 'Application cannot be submitted'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw loan application"""
        application = self.get_object()
        if application.status in ['submitted', 'under_review']:
            application.status = 'withdrawn'
            application.save()
            return Response({'message': 'Application withdrawn successfully'})
        return Response(
            {'error': 'Application cannot be withdrawn'},
            status=status.HTTP_400_BAD_REQUEST
        )


class LoanAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """Loan account management (read-only)"""
    serializer_class = LoanAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return LoanAccount.objects.filter(application__user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def payment_history(self, request, pk=None):
        """Get loan payment history"""
        loan = self.get_object()
        payments = LoanPayment.objects.filter(loan=loan)
        serializer = LoanPaymentSerializer(payments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def make_payment(self, request, pk=None):
        """Make a loan payment"""
        loan = self.get_object()
        serializer = LoanPaymentCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    payment_amount = serializer.validated_data['amount']
                    payment_method = serializer.validated_data['payment_method']
                    
                    # Validate payment amount
                    if payment_amount > loan.current_balance:
                        return Response(
                            {'error': 'Payment amount exceeds loan balance'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Calculate principal and interest
                    monthly_interest = loan.interest_rate / Decimal('1200')
                    interest_amount = loan.current_balance * monthly_interest
                    principal_amount = payment_amount - interest_amount
                    
                    if principal_amount < 0:
                        principal_amount = payment_amount
                        interest_amount = Decimal('0')
                    
                    # Create payment record
                    payment = LoanPayment.objects.create(
                        loan=loan,
                        amount=payment_amount,
                        principal_amount=principal_amount,
                        interest_amount=interest_amount,
                        payment_date=timezone.now().date(),
                        due_date=loan.next_payment_date,
                        payment_method=payment_method,
                        status='completed',
                        notes=serializer.validated_data.get('notes', '')
                    )
                    
                    # Update loan balance
                    loan.current_balance -= principal_amount
                    loan.next_payment_date = loan.next_payment_date + relativedelta(months=1)
                    loan.save()
                    
                    return Response({
                        'message': 'Payment processed successfully',
                        'payment_id': payment.id,
                        'remaining_balance': loan.current_balance
                    })
                    
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ====== INVESTMENT MANAGEMENT VIEWSETS ======

class InvestmentAccountViewSet(viewsets.ModelViewSet):
    """Investment account management"""
    serializer_class = InvestmentAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return InvestmentAccount.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def portfolio(self, request, pk=None):
        """Get investment portfolio for this account"""
        account = self.get_object()
        investments = Investment.objects.filter(account=account)
        serializer = InvestmentSerializer(investments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def buy_investment(self, request, pk=None):
        """Buy new investment"""
        account = self.get_object()
        serializer = InvestmentCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    investment_data = serializer.validated_data
                    total_cost = investment_data['quantity'] * investment_data['purchase_price']
                    
                    # Check account balance
                    if account.balance < total_cost:
                        return Response(
                            {'error': 'Insufficient account balance'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Create investment
                    investment = Investment.objects.create(
                        account=account,
                        **investment_data
                    )
                    
                    # Update account balance
                    account.balance -= total_cost
                    account.save()
                    
                    return Response({
                        'message': 'Investment purchased successfully',
                        'investment_id': investment.id,
                        'remaining_balance': account.balance
                    })
                    
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InvestmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Investment management (read-only)"""
    serializer_class = InvestmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Investment.objects.filter(account__user=self.request.user)


# ====== INSURANCE VIEWSETS ======

class InsurancePolicyViewSet(viewsets.ModelViewSet):
    """Insurance policy management"""
    serializer_class = InsurancePolicySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return InsurancePolicy.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['get'])
    def claims(self, request, pk=None):
        """Get claims for this policy"""
        policy = self.get_object()
        claims = InsuranceClaim.objects.filter(policy=policy)
        serializer = InsuranceClaimSerializer(claims, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def file_claim(self, request, pk=None):
        """File a new insurance claim"""
        policy = self.get_object()
        serializer = InsuranceClaimCreateSerializer(data=request.data)
        if serializer.is_valid():
            claim = serializer.save(policy=policy)
            return Response({
                'message': 'Claim filed successfully',
                'claim_id': claim.id,
                'claim_number': claim.claim_number
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class InsuranceClaimViewSet(viewsets.ReadOnlyModelViewSet):
    """Insurance claim management (read-only)"""
    serializer_class = InsuranceClaimSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return InsuranceClaim.objects.filter(policy__user=self.request.user)


# ====== BILL PAYMENT VIEWSETS ======

class BillerViewSet(viewsets.ReadOnlyModelViewSet):
    """Available billers (read-only)"""
    serializer_class = BillerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Biller.objects.filter(is_active=True)


class BillPaymentViewSet(viewsets.ModelViewSet):
    """Bill payment management"""
    serializer_class = BillPaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BillPayment.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BillPaymentCreateSerializer
        return BillPaymentSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a scheduled bill payment"""
        payment = self.get_object()
        if payment.status == 'scheduled':
            payment.status = 'cancelled'
            payment.save()
            return Response({'message': 'Payment cancelled successfully'})
        return Response(
            {'error': 'Payment cannot be cancelled'},
            status=status.HTTP_400_BAD_REQUEST
        )


class PayeeViewSet(viewsets.ModelViewSet):
    """Payee management"""
    serializer_class = PayeeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Payee.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """Toggle favorite status for payee"""
        payee = self.get_object()
        payee.is_favorite = not payee.is_favorite
        payee.save()
        return Response({
            'message': 'Favorite status updated',
            'is_favorite': payee.is_favorite
        })


class ScheduledPaymentViewSet(viewsets.ModelViewSet):
    """Scheduled payment management"""
    serializer_class = ScheduledPaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ScheduledPayment.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ScheduledPaymentCreateSerializer
        return ScheduledPaymentSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause scheduled payment"""
        payment = self.get_object()
        payment.status = 'paused'
        payment.save()
        return Response({'message': 'Payment paused successfully'})
    
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """Resume scheduled payment"""
        payment = self.get_object()
        payment.status = 'active'
        payment.save()
        return Response({'message': 'Payment resumed successfully'})


# ====== NOTIFICATION VIEWSETS ======

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Notification management"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'message': f'{count} notifications marked as read'})


# ====== ANALYTICS & REPORTING VIEWSETS ======

class AnalyticsViewSet(viewsets.ViewSet):
    """Advanced analytics and reporting"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def account_summary(self, request):
        """Get comprehensive account summary"""
        user = request.user
        
        # Get account balances
        accounts = Account.objects.filter(user=user)
        total_checking = accounts.filter(account_type='checking').aggregate(Sum('balance'))['balance__sum'] or 0
        total_savings = accounts.filter(account_type='savings').aggregate(Sum('balance'))['balance__sum'] or 0
        total_credit = accounts.filter(account_type='credit').aggregate(Sum('balance'))['balance__sum'] or 0
        total_balance = total_checking + total_savings + total_credit
        
        # Get Bitcoin information
        try:
            wallet = BitcoinWallet.objects.get(user=user)
            total_bitcoin = wallet.balance
            bitcoin_value_usd = wallet.balance * wallet.btc_price_usd
        except BitcoinWallet.DoesNotExist:
            total_bitcoin = 0
            bitcoin_value_usd = 0
        
        # Get investment information
        investment_accounts = InvestmentAccount.objects.filter(user=user)
        total_investments = investment_accounts.aggregate(Sum('balance'))['balance__sum'] or 0
        
        # Get loan information
        loan_accounts = LoanAccount.objects.filter(application__user=user)
        total_loans = loan_accounts.aggregate(Sum('current_balance'))['current_balance__sum'] or 0
        
        data = {
            'total_checking': total_checking,
            'total_savings': total_savings,
            'total_credit': total_credit,
            'total_balance': total_balance,
            'total_bitcoin': total_bitcoin,
            'bitcoin_value_usd': bitcoin_value_usd,
            'total_investments': total_investments,
            'total_loans': total_loans
        }
        
        serializer = AccountSummarySerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def transaction_analytics(self, request):
        """Get transaction analytics"""
        user = request.user
        
        # Get date range (default to last 30 days)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        if request.query_params.get('start_date'):
            start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d').date()
        if request.query_params.get('end_date'):
            end_date = datetime.strptime(request.query_params['end_date'], '%Y-%m-%d').date()
        
        # Get transactions
        transactions = Transaction.objects.filter(
            user=user,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        # Calculate totals
        total_transactions = transactions.count()
        total_income = transactions.filter(transaction_type='deposit').aggregate(Sum('amount'))['amount__sum'] or 0
        total_expenses = transactions.filter(transaction_type__in=['withdrawal', 'transfer', 'bill_payment']).aggregate(Sum('amount'))['amount__sum'] or 0
        net_cash_flow = total_income - total_expenses
        
        # Category breakdown
        categories = {}
        for tx in transactions:
            category = tx.transaction_type
            if category not in categories:
                categories[category] = 0
            categories[category] += float(tx.amount)
        
        # Monthly trends (simplified)
        monthly_trends = []
        current_date = start_date
        while current_date <= end_date:
            month_transactions = transactions.filter(
                created_at__date__month=current_date.month,
                created_at__date__year=current_date.year
            )
            monthly_trends.append({
                'month': current_date.strftime('%Y-%m'),
                'total_amount': float(month_transactions.aggregate(Sum('amount'))['amount__sum'] or 0),
                'transaction_count': month_transactions.count()
            })
            current_date = current_date + relativedelta(months=1)
        
        data = {
            'total_transactions': total_transactions,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_cash_flow': net_cash_flow,
            'categories': categories,
            'monthly_trends': monthly_trends
        }
        
        serializer = TransactionAnalyticsSerializer(data)
        return Response(serializer.data)


# ====== VIRTUAL CARD VIEWSETS ======

class VirtualCardViewSet(viewsets.ModelViewSet):
    """Virtual card management"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return VirtualCard.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return VirtualCardCreateSerializer
        return VirtualCardSerializer
    
    def perform_create(self, serializer):
        # Generate card details
        from datetime import date
        from dateutil.relativedelta import relativedelta
        import random
        
        card_type = serializer.validated_data.get('card_type', 'visa')
        
        # Generate card number
        prefix = '4' if card_type == 'visa' else '5'
        card_number = prefix + ''.join([str(random.randint(0, 9)) for _ in range(15)])
        
        # Generate expiry date (3 years from now)
        expiry_date = date.today() + relativedelta(years=3)
        
        # Generate CVV
        cvv = str(random.randint(100, 999))
        
        serializer.save(
            user=self.request.user,
            card_number=card_number,
            expiry_date=expiry_date,
            cvv=cvv
        )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a virtual card"""
        card = self.get_object()
        card.is_active = True
        card.save()
        return Response({'message': 'Card activated successfully'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a virtual card"""
        card = self.get_object()
        card.is_active = False
        card.save()
        return Response({'message': 'Card deactivated successfully'})
    
    @action(detail=True, methods=['post'])
    def transaction(self, request, pk=None):
        """Process a card transaction"""
        card = self.get_object()
        if not card.is_active:
            return Response(
                {'error': 'Card is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CardTransactionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    amount = serializer.validated_data['amount']
                    merchant_name = serializer.validated_data['merchant_name']
                    description = serializer.validated_data.get('description', '')
                    
                    # Get primary account for payment
                    primary_account = Account.objects.filter(
                        user=request.user,
                        account_type='checking'
                    ).first()
                    
                    if not primary_account:
                        return Response(
                            {'error': 'No primary account found'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Check balance
                    if primary_account.balance < amount:
                        return Response(
                            {'error': 'Insufficient funds'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    # Process transaction
                    primary_account.balance -= amount
                    primary_account.save()
                    
                    # Create transaction record
                    tx = Transaction.objects.create(
                        user=request.user,
                        from_account=primary_account,
                        amount=amount,
                        transaction_type='payment',
                        description=f"Card payment to {merchant_name}: {description}",
                        status='completed'
                    )
                    
                    return Response({
                        'message': 'Transaction successful',
                        'transaction_id': tx.id,
                        'amount': amount,
                        'merchant': merchant_name,
                        'remaining_balance': primary_account.balance
                    })
                    
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """Get card transaction history"""
        card = self.get_object()
        # Get transactions related to this card (simplified)
        transactions = Transaction.objects.filter(
            user=request.user,
            transaction_type='payment',
            description__icontains='Card payment'
        ).order_by('-created_at')[:20]
        
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)


# ====== WEBHOOK VIEWSETS ======

class WebhookEndpointViewSet(viewsets.ModelViewSet):
    """Webhook endpoint management"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WebhookEndpoint.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return WebhookEndpointCreateSerializer
        return WebhookEndpointSerializer
    
    def perform_create(self, serializer):
        # Generate secret if not provided
        import secrets
        if not serializer.validated_data.get('secret'):
            serializer.validated_data['secret'] = secrets.token_urlsafe(32)
        
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test webhook endpoint"""
        endpoint = self.get_object()
        
        serializer = WebhookTestSerializer(data=request.data)
        if serializer.is_valid():
            from .webhook_delivery import WebhookDeliveryService
            
            delivery_service = WebhookDeliveryService()
            test_payload = serializer.validated_data['payload']
            
            # Create a test event
            test_event = WebhookEvent.objects.create(
                event_type='system.test',
                payload=test_payload,
                user=request.user,
                status='processing'
            )
            
            # Attempt delivery
            success, response_data = delivery_service.deliver_webhook(endpoint, test_event)
            
            return Response({
                'success': success,
                'response_data': response_data,
                'test_event_id': test_event.id
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        """Get events for this endpoint"""
        endpoint = self.get_object()
        events = WebhookEvent.objects.filter(
            event_type__in=endpoint.events,
            user=request.user
        ).order_by('-created_at')[:50]
        
        serializer = WebhookEventSerializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def deliveries(self, request, pk=None):
        """Get delivery history for this endpoint"""
        endpoint = self.get_object()
        deliveries = WebhookDelivery.objects.filter(
            webhook_endpoint=endpoint
        ).order_by('-attempted_at')[:100]
        
        serializer = WebhookDeliverySerializer(deliveries, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def regenerate_secret(self, request, pk=None):
        """Regenerate webhook secret"""
        import secrets
        endpoint = self.get_object()
        endpoint.secret = secrets.token_urlsafe(32)
        endpoint.save()
        
        return Response({
            'message': 'Secret regenerated successfully',
            'new_secret': endpoint.secret
        })


class WebhookEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Webhook event monitoring"""
    serializer_class = WebhookEventSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WebhookEvent.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def retry_failed(self, request):
        """Retry failed webhook events"""
        serializer = WebhookRetrySerializer(data=request.data)
        if serializer.is_valid():
            event_ids = serializer.validated_data['event_ids']
            delay_seconds = serializer.validated_data['delay_seconds']
            
            events = WebhookEvent.objects.filter(
                id__in=event_ids,
                user=request.user,
                status='failed'
            )
            
            count = 0
            for event in events:
                event.status = 'pending'
                event.schedule_retry(delay_seconds)
                count += 1
            
            return Response({
                'message': f'{count} events scheduled for retry',
                'retried_events': count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get webhook event statistics"""
        user = request.user
        
        # Get date range (default to last 7 days)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        
        if request.query_params.get('start_date'):
            start_date = datetime.strptime(request.query_params['start_date'], '%Y-%m-%d')
        if request.query_params.get('end_date'):
            end_date = datetime.strptime(request.query_params['end_date'], '%Y-%m-%d')
        
        events = WebhookEvent.objects.filter(
            user=user,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        total_events = events.count()
        pending_events = events.filter(status='pending').count()
        failed_events = events.filter(status='failed').count()
        completed_events = events.filter(status='completed').count()
        
        # Event type breakdown
        event_types = {}
        for event in events:
            event_type = event.event_type
            if event_type not in event_types:
                event_types[event_type] = 0
            event_types[event_type] += 1
        
        return Response({
            'total_events': total_events,
            'pending_events': pending_events,
            'failed_events': failed_events,
            'completed_events': completed_events,
            'success_rate': (completed_events / total_events * 100) if total_events > 0 else 0,
            'event_types': event_types,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            }
        })


class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    """Webhook delivery monitoring"""
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WebhookDelivery.objects.filter(
            webhook_endpoint__user=self.request.user
        ).order_by('-attempted_at')
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get delivery statistics"""
        user = request.user
        
        deliveries = WebhookDelivery.objects.filter(
            webhook_endpoint__user=user
        )
        
        total_deliveries = deliveries.count()
        successful_deliveries = deliveries.filter(status='success').count()
        failed_deliveries = deliveries.filter(status='failed').count()
        
        # Average response time
        avg_response_time = deliveries.filter(
            response_time_ms__isnull=False
        ).aggregate(avg_time=models.Avg('response_time_ms'))['avg_time'] or 0
        
        # Success rate by endpoint
        endpoint_stats = {}
        for delivery in deliveries.select_related('webhook_endpoint'):
            endpoint_name = delivery.webhook_endpoint.name
            if endpoint_name not in endpoint_stats:
                endpoint_stats[endpoint_name] = {'total': 0, 'successful': 0}
            
            endpoint_stats[endpoint_name]['total'] += 1
            if delivery.is_successful:
                endpoint_stats[endpoint_name]['successful'] += 1
        
        # Calculate success rates
        for name, stats in endpoint_stats.items():
            stats['success_rate'] = (stats['successful'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        data = {
            'total_deliveries': total_deliveries,
            'successful_deliveries': successful_deliveries,
            'failed_deliveries': failed_deliveries,
            'success_rate': (successful_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0,
            'average_response_time': round(avg_response_time, 2),
            'endpoint_stats': endpoint_stats
        }
        
        serializer = WebhookStatsSerializer(data)
        return Response(serializer.data)


class WebhookTemplateViewSet(viewsets.ModelViewSet):
    """Webhook template management"""
    serializer_class = WebhookTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WebhookTemplate.objects.filter(is_active=True).order_by('event_type')
    
    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """Preview rendered template with sample data"""
        template = self.get_object()
        
        # Sample context data
        sample_data = {
            'user_id': request.user.id,
            'user_email': request.user.email,
            'timestamp': timezone.now().isoformat(),
            'event_id': 'sample-event-id',
            'amount': '100.00',
            'account_id': 'sample-account-id',
            'transaction_id': 'sample-transaction-id'
        }
        
        # Override with any provided context
        if request.data.get('context'):
            sample_data.update(request.data['context'])
        
        try:
            rendered_payload = template.render_payload(sample_data)
            return Response({
                'template_name': template.name,
                'event_type': template.event_type,
                'rendered_payload': rendered_payload,
                'context_used': sample_data
            })
        except Exception as e:
            return Response(
                {'error': f'Template rendering failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class WebhookLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Webhook log monitoring"""
    serializer_class = WebhookLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WebhookLog.objects.filter(
            webhook_endpoint__user=self.request.user
        ).order_by('-created_at')
    
    @action(detail=False, methods=['delete'])
    def clear_old_logs(self, request):
        """Clear logs older than specified days"""
        days = int(request.query_params.get('days', 30))
        
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count = WebhookLog.objects.filter(
            webhook_endpoint__user=request.user,
            created_at__lt=cutoff_date
        ).delete()[0]
        
        return Response({
            'message': f'Deleted {deleted_count} log entries older than {days} days'
        }) 