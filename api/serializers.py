from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.models import UserProfile
from banking.models import (
    Account, Transaction, BitcoinWallet, VirtualCard, Notification
)
from banking.models_loans import LoanApplication, LoanAccount, LoanPayment
from banking.models_investments_insurance import InvestmentAccount, Investment, InsurancePolicy, InsuranceClaim
from banking.models_bills import Biller, BillPayment, Payee, ScheduledPayment
from .models import (
    WebhookEndpoint, WebhookEvent, WebhookDelivery, 
    WebhookSignature, WebhookTemplate, WebhookLog
)
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from decimal import Decimal

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with basic information."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model."""
    
    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'address', 'city', 'state', 'zip_code', 
            'date_of_birth', 'company', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for User model including profile information."""
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'date_joined', 'profile'
        ]
        read_only_fields = ['id', 'date_joined']


class AccountSerializer(serializers.ModelSerializer):
    """Serializer for Account model."""
    balance = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = Account
        fields = [
            'id', 'account_number', 'account_type', 'balance', 
            'routing_number', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'account_number', 'routing_number', 'created_at', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model."""
    from_account = AccountSerializer(read_only=True)
    to_account = AccountSerializer(read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'from_account', 'to_account', 'transaction_type', 'amount', 'description',
            'reference', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reference', 'created_at', 'updated_at']


class TransactionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transactions."""
    
    class Meta:
        model = Transaction
        fields = ['transaction_type', 'amount', 'description']
        
    def validate_amount(self, value):
        """Validate that amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs


class MoneyTransferSerializer(serializers.Serializer):
    """Serializer for money transfer operations."""
    recipient_account = serializers.CharField(max_length=20)
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    description = serializers.CharField(max_length=255, required=False)
    transaction_pin = serializers.CharField(min_length=4, max_length=4)
    
    def validate_amount(self, value):
        """Validate that amount is positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be positive.")
        if value > 10000:  # Daily limit
            raise serializers.ValidationError("Amount exceeds daily limit of $10,000.")
        return value
    
    def validate_transaction_pin(self, value):
        """Validate transaction PIN format."""
        if not value.isdigit():
            raise serializers.ValidationError("Transaction PIN must be 4 digits.")
        return value


# ====== BITCOIN/CRYPTOCURRENCY SERIALIZERS ======

class BitcoinWalletSerializer(serializers.ModelSerializer):
    balance_usd = serializers.SerializerMethodField()
    
    class Meta:
        model = BitcoinWallet
        fields = ['id', 'address', 'balance', 'balance_usd', 'btc_price_usd', 'qr_code', 'is_active', 'created_at']
        read_only_fields = ['id', 'address', 'qr_code', 'created_at']
    
    def get_balance_usd(self, obj):
        return obj.balance * obj.btc_price_usd if obj.btc_price_usd else 0


class BitcoinSendSerializer(serializers.Serializer):
    wallet_address = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(max_digits=15, decimal_places=8)
    balance_source = serializers.ChoiceField(choices=['bitcoin', 'fiat'])
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    
    def validate_wallet_address(self, value):
        # Basic Bitcoin address validation
        if not value or len(value) < 26:
            raise serializers.ValidationError("Invalid Bitcoin address")
        return value


class BitcoinSwapSerializer(serializers.Serializer):
    swap_type = serializers.ChoiceField(choices=['buy', 'sell'])
    amount = serializers.DecimalField(max_digits=15, decimal_places=8)
    account_id = serializers.IntegerField()
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


# ====== LOAN MANAGEMENT SERIALIZERS ======

class LoanApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanApplication
        fields = [
            'id', 'application_number', 'loan_type', 'amount', 'term_months', 
            'purpose', 'status', 'interest_rate', 'monthly_payment', 'reason_for_loan',
            'employment_status', 'annual_income', 'employer_name', 'job_title',
            'years_employed', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'application_number', 'status', 'interest_rate', 'monthly_payment', 'created_at', 'updated_at']


class LoanAccountSerializer(serializers.ModelSerializer):
    application = LoanApplicationSerializer(read_only=True)
    
    class Meta:
        model = LoanAccount
        fields = [
            'id', 'loan_number', 'application', 'original_amount', 'current_balance',
            'interest_rate', 'term_months', 'monthly_payment', 'start_date',
            'next_payment_date', 'status', 'collateral_description', 'collateral_value',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'loan_number', 'created_at', 'updated_at']


class LoanPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanPayment
        fields = [
            'id', 'payment_number', 'loan', 'amount', 'principal_amount', 'interest_amount',
            'fees', 'payment_date', 'due_date', 'payment_method', 'status',
            'reference_number', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'payment_number', 'created_at']


class LoanPaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanPayment
        fields = ['loan', 'amount', 'payment_method', 'notes']
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0")
        return value


# ====== INVESTMENT MANAGEMENT SERIALIZERS ======

class InvestmentAccountSerializer(serializers.ModelSerializer):
    total_investments = serializers.SerializerMethodField()
    
    class Meta:
        model = InvestmentAccount
        fields = [
            'id', 'account_type', 'account_number', 'balance', 'total_investments',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'account_number', 'created_at', 'updated_at']
    
    def get_total_investments(self, obj):
        return obj.investments.count()


class InvestmentSerializer(serializers.ModelSerializer):
    current_value = serializers.SerializerMethodField()
    profit_loss = serializers.SerializerMethodField()
    profit_loss_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Investment
        fields = [
            'id', 'account', 'investment_type', 'name', 'symbol', 'quantity',
            'purchase_price', 'current_price', 'purchase_date', 'current_value',
            'profit_loss', 'profit_loss_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_current_value(self, obj):
        return obj.current_value()
    
    def get_profit_loss(self, obj):
        return obj.profit_loss()
    
    def get_profit_loss_percentage(self, obj):
        if obj.purchase_price:
            return ((obj.current_price or obj.purchase_price) - obj.purchase_price) / obj.purchase_price * 100
        return 0


class InvestmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Investment
        fields = [
            'account', 'investment_type', 'name', 'symbol', 'quantity',
            'purchase_price', 'purchase_date'
        ]
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0")
        return value


# ====== INSURANCE SERIALIZERS ======

class InsurancePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = InsurancePolicy
        fields = [
            'id', 'policy_type', 'policy_number', 'provider', 'coverage_amount',
            'monthly_premium', 'start_date', 'end_date', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'policy_number', 'created_at', 'updated_at']


class InsuranceClaimSerializer(serializers.ModelSerializer):
    policy = InsurancePolicySerializer(read_only=True)
    
    class Meta:
        model = InsuranceClaim
        fields = [
            'id', 'policy', 'claim_number', 'claim_amount', 'description',
            'incident_date', 'claim_date', 'status', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'claim_number', 'created_at', 'updated_at']


class InsuranceClaimCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceClaim
        fields = ['policy', 'claim_amount', 'description', 'incident_date']
    
    def validate_claim_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Claim amount must be greater than 0")
        return value


# ====== BILL PAYMENT SERIALIZERS ======

class BillerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Biller
        fields = [
            'id', 'name', 'biller_type', 'description', 'logo', 'website',
            'customer_service_phone', 'is_active'
        ]
        read_only_fields = ['id']


class BillPaymentSerializer(serializers.ModelSerializer):
    biller = BillerSerializer(read_only=True)
    total_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = BillPayment
        fields = [
            'id', 'biller', 'account', 'payment_method', 'amount', 'fee',
            'total_amount', 'reference_number', 'account_number', 'status',
            'scheduled_date', 'processed_date', 'confirmation_number',
            'notes', 'is_recurring', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reference_number', 'confirmation_number', 'created_at', 'updated_at']
    
    def get_total_amount(self, obj):
        return obj.amount + obj.fee


class BillPaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillPayment
        fields = [
            'biller', 'account', 'payment_method', 'amount', 'account_number',
            'scheduled_date', 'notes', 'is_recurring'
        ]
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0")
        return value


class PayeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payee
        fields = [
            'id', 'name', 'account_number', 'description', 'is_business',
            'email', 'phone', 'address_line1', 'address_line2', 'city',
            'state', 'postal_code', 'country', 'is_favorite',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ScheduledPaymentSerializer(serializers.ModelSerializer):
    payee = PayeeSerializer(read_only=True)
    
    class Meta:
        model = ScheduledPayment
        fields = [
            'id', 'payee', 'account', 'amount', 'frequency', 'start_date',
            'end_date', 'next_payment_date', 'status', 'reference',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'reference', 'created_at', 'updated_at']


class ScheduledPaymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledPayment
        fields = [
            'payee', 'account', 'amount', 'frequency', 'start_date',
            'end_date', 'notes'
        ]
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0")
        return value


# ====== NOTIFICATION SERIALIZERS ======

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'is_read',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


# ====== ANALYTICS & REPORTING SERIALIZERS ======

class AccountSummarySerializer(serializers.Serializer):
    total_checking = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_savings = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_bitcoin = serializers.DecimalField(max_digits=15, decimal_places=8)
    bitcoin_value_usd = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_investments = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_loans = serializers.DecimalField(max_digits=15, decimal_places=2)


class TransactionAnalyticsSerializer(serializers.Serializer):
    total_transactions = serializers.IntegerField()
    total_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_cash_flow = serializers.DecimalField(max_digits=15, decimal_places=2)
    categories = serializers.DictField()
    monthly_trends = serializers.ListField()


# ====== VIRTUAL CARD SERIALIZERS ======

class VirtualCardSerializer(serializers.ModelSerializer):
    card_number_masked = serializers.SerializerMethodField()
    
    class Meta:
        model = VirtualCard
        fields = [
            'id', 'card_number', 'card_number_masked', 'card_type', 'expiry_date',
            'cvv', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'card_number', 'created_at', 'updated_at']
    
    def get_card_number_masked(self, obj):
        """Return masked card number for security"""
        return f"**** **** **** {obj.card_number[-4:]}"


class VirtualCardCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualCard
        fields = ['card_type']
    
    def validate_card_type(self, value):
        if value not in ['visa', 'mastercard']:
            raise serializers.ValidationError("Card type must be 'visa' or 'mastercard'")
        return value


class CardTransactionSerializer(serializers.Serializer):
    """Serializer for card-based transactions"""
    card_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=15, decimal_places=2)
    merchant_name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=255, required=False)
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value


# ====== WEBHOOK SERIALIZERS ======

class WebhookEndpointSerializer(serializers.ModelSerializer):
    """Serializer for webhook endpoints"""
    
    success_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = WebhookEndpoint
        fields = [
            'id', 'name', 'url', 'events', 'secret', 'is_active',
            'timeout_seconds', 'max_retries', 'retry_delay_seconds', 'email_notifications_enabled',
            'created_at', 'updated_at', 'last_used_at',
            'total_deliveries', 'successful_deliveries', 'failed_deliveries', 'success_rate'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_used_at', 
                           'total_deliveries', 'successful_deliveries', 'failed_deliveries']
        extra_kwargs = {
            'secret': {'write_only': True, 'required': False}
        }

    def validate_events(self, value):
        """Validate that all events are valid choices"""
        valid_events = [choice[0] for choice in WebhookEndpoint.WEBHOOK_EVENTS]
        for event in value:
            if event not in valid_events:
                raise serializers.ValidationError(f"Invalid event type: {event}")
        return value

    def validate_url(self, value):
        """Validate webhook URL"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value


class WebhookEndpointCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating webhook endpoints"""
    
    class Meta:
        model = WebhookEndpoint
        fields = [
            'name', 'url', 'events', 'secret', 'is_active',
            'timeout_seconds', 'max_retries', 'retry_delay_seconds', 'email_notifications_enabled'
        ]
        extra_kwargs = {
            'secret': {'write_only': True, 'required': False}
        }

    def validate_events(self, value):
        """Validate that all events are valid choices"""
        valid_events = [choice[0] for choice in WebhookEndpoint.WEBHOOK_EVENTS]
        for event in value:
            if event not in valid_events:
                raise serializers.ValidationError(f"Invalid event type: {event}")
        return value

    def create(self, validated_data):
        # Set the user from request
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = [
            'id', 'event_type', 'status', 'payload', 'user',
            'delivery_attempts', 'next_retry_at', 'created_at', 'processed_at'
        ]
        read_only_fields = ['id', 'created_at', 'processed_at']


class WebhookEventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = ['event_type', 'payload', 'user']

    def validate_payload(self, value):
        if not value:
            raise serializers.ValidationError("Payload cannot be empty")
        return value


class WebhookDeliverySerializer(serializers.ModelSerializer):
    webhook_endpoint_name = serializers.CharField(source='webhook_endpoint.name', read_only=True)
    webhook_event_type = serializers.CharField(source='webhook_event.event_type', read_only=True)
    is_successful = serializers.ReadOnlyField()
    
    class Meta:
        model = WebhookDelivery
        fields = [
            'id', 'webhook_endpoint', 'webhook_endpoint_name', 'webhook_event',
            'webhook_event_type', 'status', 'http_status_code', 'response_body',
            'error_message', 'response_time_ms', 'attempt_number', 'is_retry',
            'is_successful', 'attempted_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'webhook_endpoint_name', 'webhook_event_type', 'is_successful',
            'attempted_at', 'completed_at'
        ]


class WebhookSignatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookSignature
        fields = [
            'id', 'webhook_endpoint', 'method', 'secret_key', 'algorithm',
            'issuer', 'audience', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'secret_key': {'write_only': True}
        }


class WebhookTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookTemplate
        fields = [
            'id', 'event_type', 'name', 'description', 'payload_template',
            'headers_template', 'is_active', 'version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_payload_template(self, value):
        if not value:
            raise serializers.ValidationError("Payload template cannot be empty")
        return value


class WebhookLogSerializer(serializers.ModelSerializer):
    webhook_endpoint_name = serializers.CharField(source='webhook_endpoint.name', read_only=True)
    webhook_event_type = serializers.CharField(source='webhook_event.event_type', read_only=True)
    
    class Meta:
        model = WebhookLog
        fields = [
            'id', 'webhook_endpoint', 'webhook_endpoint_name', 'webhook_event',
            'webhook_event_type', 'webhook_delivery', 'level', 'message',
            'details', 'created_at'
        ]
        read_only_fields = ['id', 'webhook_endpoint_name', 'webhook_event_type', 'created_at']


class WebhookTestSerializer(serializers.Serializer):
    """Serializer for testing webhook endpoints"""
    url = serializers.URLField()
    payload = serializers.JSONField()
    headers = serializers.JSONField(required=False, default=dict)
    timeout = serializers.IntegerField(default=30, min_value=1, max_value=300)

    def validate_payload(self, value):
        if not value:
            raise serializers.ValidationError("Test payload cannot be empty")
        return value


class WebhookStatsSerializer(serializers.Serializer):
    """Serializer for webhook statistics"""
    total_endpoints = serializers.IntegerField()
    active_endpoints = serializers.IntegerField()
    total_events = serializers.IntegerField()
    pending_events = serializers.IntegerField()
    failed_events = serializers.IntegerField()
    total_deliveries = serializers.IntegerField()
    successful_deliveries = serializers.IntegerField()
    failed_deliveries = serializers.IntegerField()
    average_response_time = serializers.FloatField()
    success_rate = serializers.FloatField()


class WebhookRetrySerializer(serializers.Serializer):
    """Serializer for retrying failed webhook events"""
    event_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )
    delay_seconds = serializers.IntegerField(default=60, min_value=1, max_value=3600)

    def validate_event_ids(self, value):
        if len(value) > 100:
            raise serializers.ValidationError("Cannot retry more than 100 events at once")
        return value 