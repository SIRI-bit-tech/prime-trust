from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.models import UserProfile
from banking.models import Account, Transaction

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