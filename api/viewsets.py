from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from banking.models import Account, Transaction
from .serializers import (
    AccountSerializer, TransactionSerializer, MoneyTransferSerializer,
    TransactionCreateSerializer
)
from banking.utils import generate_reference_number
import random
import string
from django.db import models


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