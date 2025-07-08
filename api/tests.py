"""
Comprehensive Test Suite for PrimeTrust Banking API

This test suite covers all API endpoints, authentication, banking operations,
webhooks, and security features to ensure production readiness.
"""

import json
import uuid
from decimal import Decimal
from unittest.mock import patch, Mock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import UserProfile
from banking.models import Account, Transaction, BitcoinWallet, VirtualCard
from banking.models_loans import LoanApplication, LoanAccount
from banking.models_investments_insurance import InvestmentAccount, Investment, InsurancePolicy
from banking.models_bills import Biller, BillPayment, Payee
from dashboard.models import Notification
from .models import (
    WebhookEndpoint, WebhookEvent, WebhookDelivery, 
    WebhookTemplate, WebhookLog
)
from .webhook_delivery import WebhookDeliveryService, WebhookEventTrigger

User = get_user_model()


class BaseAPITestCase(APITestCase):
    """Base test case with common setup for API tests"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )
        
        # Create user profile
        self.profile = UserProfile.objects.create(
            user=self.user,
            phone_number='+1234567890',
            address='123 Test St',
            city='Test City',
            state='TS',
            zip_code='12345',
            date_of_birth='1990-01-01'
        )
        
        # Create test accounts
        self.checking_account = Account.objects.create(
            user=self.user,
            account_type='checking',
            balance=1000.00
        )
        
        self.savings_account = Account.objects.create(
            user=self.user,
            account_type='savings',
            balance=5000.00
        )
        
        # Get JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        # Setup API client with authentication
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def create_test_user(self, email, password='TestPassword123!'):
        """Helper method to create additional test users"""
        return User.objects.create_user(
            email=email,
            password=password,
            first_name='Test',
            last_name='User2'
        )


class AuthenticationAPITestCase(BaseAPITestCase):
    """Test authentication endpoints"""
    
    def test_login_success(self):
        """Test successful login"""
        url = reverse('api:token_obtain_pair')
        data = {
            'email': 'testuser@example.com',
            'password': 'TestPassword123!'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        url = reverse('api:token_obtain_pair')
        data = {
            'email': 'testuser@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_refresh(self):
        """Test token refresh"""
        refresh = RefreshToken.for_user(self.user)
        url = reverse('api:token_refresh')
        data = {'refresh': str(refresh)}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
    
    def test_profile_api(self):
        """Test profile retrieval"""
        url = reverse('api:profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
    
    def test_change_password(self):
        """Test password change"""
        url = reverse('api:change_password')
        data = {
            'old_password': 'TestPassword123!',
            'new_password': 'NewTestPassword123!',
            'confirm_password': 'NewTestPassword123!'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify old password no longer works
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password('TestPassword123!'))
        self.assertTrue(self.user.check_password('NewTestPassword123!'))


class AccountAPITestCase(BaseAPITestCase):
    """Test account-related endpoints"""
    
    def test_list_accounts(self):
        """Test listing user accounts"""
        url = reverse('api:account-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_account_detail(self):
        """Test account detail view"""
        url = reverse('api:account-detail', kwargs={'pk': self.checking_account.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['account_type'], 'checking')
        self.assertEqual(Decimal(response.data['balance']), Decimal('1000.00'))
    
    def test_account_balance(self):
        """Test account balance endpoint"""
        url = reverse('api:account-balance', kwargs={'pk': self.checking_account.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['balance']), Decimal('1000.00'))
    
    def test_account_deposit(self):
        """Test account deposit"""
        url = reverse('api:account-deposit', kwargs={'pk': self.checking_account.pk})
        data = {
            'amount': '500.00',
            'description': 'Test deposit'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify balance updated
        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.balance, Decimal('1500.00'))
    
    def test_account_transfer(self):
        """Test money transfer between accounts"""
        url = reverse('api:account-transfer', kwargs={'pk': self.checking_account.pk})
        data = {
            'to_account': self.savings_account.account_number,
            'amount': '200.00',
            'description': 'Test transfer'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify balances updated
        self.checking_account.refresh_from_db()
        self.savings_account.refresh_from_db()
        self.assertEqual(self.checking_account.balance, Decimal('800.00'))
        self.assertEqual(self.savings_account.balance, Decimal('5200.00'))


class TransactionAPITestCase(BaseAPITestCase):
    """Test transaction-related endpoints"""
    
    def setUp(self):
        super().setUp()
        
        # Create test transactions
        self.transaction1 = Transaction.objects.create(
            user=self.user,
            from_account=self.checking_account,
            to_account=self.savings_account,
            amount=100.00,
            transaction_type='transfer',
            description='Test transfer',
            status='completed'
        )
        
        self.transaction2 = Transaction.objects.create(
            user=self.user,
            from_account=self.checking_account,
            amount=50.00,
            transaction_type='withdrawal',
            description='ATM withdrawal',
            status='completed'
        )
    
    def test_list_transactions(self):
        """Test listing user transactions"""
        url = reverse('api:transaction-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_transaction_detail(self):
        """Test transaction detail view"""
        url = reverse('api:transaction-detail', kwargs={'pk': self.transaction1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['transaction_type'], 'transfer')
        self.assertEqual(Decimal(response.data['amount']), Decimal('100.00'))
    
    def test_recent_transactions(self):
        """Test recent transactions endpoint"""
        url = reverse('api:transaction-recent')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) <= 10)  # Should limit to 10


class BitcoinAPITestCase(BaseAPITestCase):
    """Test Bitcoin wallet endpoints"""
    
    def setUp(self):
        super().setUp()
        
        # Create Bitcoin wallet
        self.bitcoin_wallet = BitcoinWallet.objects.create(
            user=self.user,
            address='1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2',
            balance=0.005,
            btc_price_usd=50000.00
        )
    
    def test_wallet_info(self):
        """Test Bitcoin wallet info"""
        url = reverse('api:bitcoin-wallet-info')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['address'], '1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2')
    
    @patch('api.viewsets.requests.get')
    def test_send_bitcoin(self, mock_get):
        """Test Bitcoin sending"""
        # Mock Bitcoin price API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'bitcoin': {'usd': 50000}}
        mock_get.return_value = mock_response
        
        url = reverse('api:bitcoin-send-bitcoin')
        data = {
            'wallet_address': '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
            'amount': '0.001',
            'balance_source': 'bitcoin'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify balance updated
        self.bitcoin_wallet.refresh_from_db()
        self.assertEqual(self.bitcoin_wallet.balance, Decimal('0.004'))


class LoanAPITestCase(BaseAPITestCase):
    """Test loan-related endpoints"""
    
    def test_create_loan_application(self):
        """Test creating loan application"""
        url = reverse('api:loan-application-list')
        data = {
            'loan_type': 'personal',
            'amount': '10000.00',
            'term_months': 24,
            'purpose': 'debt_consolidation',
            'reason_for_loan': 'Consolidate credit cards',
            'employment_status': 'employed',
            'annual_income': '60000.00',
            'employer_name': 'Test Company',
            'job_title': 'Software Engineer',
            'years_employed': 3
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['loan_type'], 'personal')
        self.assertEqual(Decimal(response.data['amount']), Decimal('10000.00'))
    
    def test_list_loan_applications(self):
        """Test listing loan applications"""
        # Create a loan application first
        LoanApplication.objects.create(
            user=self.user,
            loan_type='personal',
            amount=5000.00,
            term_months=12,
            purpose='home_improvement'
        )
        
        url = reverse('api:loan-application-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class InvestmentAPITestCase(BaseAPITestCase):
    """Test investment-related endpoints"""
    
    def setUp(self):
        super().setUp()
        
        # Create investment account
        self.investment_account = InvestmentAccount.objects.create(
            user=self.user,
            account_type='brokerage',
            balance=10000.00
        )
    
    def test_create_investment_account(self):
        """Test creating investment account"""
        url = reverse('api:investment-account-list')
        data = {
            'account_type': 'ira',
            'balance': '5000.00'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['account_type'], 'ira')
    
    def test_buy_investment(self):
        """Test buying investment"""
        url = reverse('api:investment-account-buy-investment', kwargs={'pk': self.investment_account.pk})
        data = {
            'investment_type': 'stock',
            'name': 'Apple Inc.',
            'symbol': 'AAPL',
            'quantity': '10',
            'purchase_price': '150.00'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify investment created
        investment = Investment.objects.get(symbol='AAPL')
        self.assertEqual(investment.quantity, 10)
        self.assertEqual(investment.purchase_price, Decimal('150.00'))


class WebhookAPITestCase(BaseAPITestCase):
    """Test webhook system endpoints"""
    
    def setUp(self):
        super().setUp()
        
        # Create webhook endpoint
        self.webhook_endpoint = WebhookEndpoint.objects.create(
            user=self.user,
            name='Test Webhook',
            url='https://example.com/webhook',
            events=['user.created', 'transaction.completed'],
            secret='test-secret'
        )
        
        # Create webhook template
        self.webhook_template = WebhookTemplate.objects.create(
            event_type='user.created',
            name='User Created Template',
            payload_template={
                'event': '{{event_type}}',
                'user_id': '{{user_id}}',
                'timestamp': '{{timestamp}}'
            }
        )
    
    def test_list_webhook_endpoints(self):
        """Test listing webhook endpoints"""
        url = reverse('api:webhook-endpoint-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Webhook')
    
    def test_create_webhook_endpoint(self):
        """Test creating webhook endpoint"""
        url = reverse('api:webhook-endpoint-list')
        data = {
            'name': 'New Webhook',
            'url': 'https://example.com/new-webhook',
            'events': ['transaction.completed'],
            'timeout_seconds': 30,
            'max_retries': 3
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Webhook')
        self.assertIn('secret', response.data)  # Auto-generated secret
    
    @patch('api.webhook_delivery.requests.Session.post')
    def test_webhook_delivery(self, mock_post):
        """Test webhook delivery"""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = 'OK'
        mock_post.return_value = mock_response
        
        # Create webhook event
        event = WebhookEvent.objects.create(
            event_type='user.created',
            user=self.user,
            payload={'user_id': self.user.id, 'email': self.user.email}
        )
        
        # Test delivery
        delivery_service = WebhookDeliveryService()
        success, response_data = delivery_service.deliver_webhook(self.webhook_endpoint, event)
        
        self.assertTrue(success)
        self.assertEqual(response_data['status_code'], 200)
        
        # Verify delivery record created
        delivery = WebhookDelivery.objects.filter(
            webhook_endpoint=self.webhook_endpoint,
            webhook_event=event
        ).first()
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery.status, 'success')
    
    def test_webhook_event_trigger(self):
        """Test webhook event triggering"""
        # Trigger user.created event
        WebhookEventTrigger.trigger_event(
            'user.created',
            self.user,
            {'user_id': self.user.id, 'email': self.user.email}
        )
        
        # Verify event created
        event = WebhookEvent.objects.filter(
            event_type='user.created',
            user=self.user
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.payload['user_id'], self.user.id)
    
    def test_webhook_template_preview(self):
        """Test webhook template preview"""
        url = reverse('api:webhook-template-preview', kwargs={'pk': self.webhook_template.pk})
        data = {
            'context': {
                'user_id': self.user.id,
                'event_type': 'user.created',
                'timestamp': '2023-01-01T00:00:00Z'
            }
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['rendered_payload']['event'], 'user.created')
        self.assertEqual(response.data['rendered_payload']['user_id'], self.user.id)


class SecurityAPITestCase(BaseAPITestCase):
    """Test security-related endpoints"""
    
    def test_security_summary(self):
        """Test security summary endpoint"""
        url = reverse('api:security_summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('two_factor_enabled', response.data)
        self.assertIn('active_sessions', response.data)
    
    def test_enable_2fa(self):
        """Test enabling 2FA"""
        url = reverse('api:enable_2fa')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('qr_code', response.data)
        self.assertIn('secret', response.data)
    
    def test_user_devices(self):
        """Test user devices endpoint"""
        url = reverse('api:user_devices')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


class PerformanceTestCase(TransactionTestCase):
    """Test API performance and load handling"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='perftest@example.com',
            password='TestPassword123!'
        )
        
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_bulk_transaction_creation(self):
        """Test creating multiple transactions efficiently"""
        # Create account
        account = Account.objects.create(
            user=self.user,
            account_type='checking',
            balance=10000.00
        )
        
        # Test bulk creation performance
        start_time = timezone.now()
        
        for i in range(100):
            Transaction.objects.create(
                user=self.user,
                from_account=account,
                amount=10.00,
                transaction_type='withdrawal',
                description=f'Test transaction {i}',
                status='completed'
            )
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should complete within reasonable time
        self.assertLess(duration, 5.0)  # 5 seconds max
        
        # Verify all transactions created
        count = Transaction.objects.filter(user=self.user).count()
        self.assertEqual(count, 100)
    
    def test_api_response_time(self):
        """Test API response times"""
        # Create some test data
        account = Account.objects.create(
            user=self.user,
            account_type='checking',
            balance=1000.00
        )
        
        for i in range(50):
            Transaction.objects.create(
                user=self.user,
                from_account=account,
                amount=10.00,
                transaction_type='deposit',
                description=f'Test transaction {i}',
                status='completed'
            )
        
        # Test transaction list endpoint performance
        start_time = timezone.now()
        
        url = reverse('api:transaction-list')
        response = self.client.get(url)
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(duration, 2.0)  # 2 seconds max


class IntegrationTestCase(BaseAPITestCase):
    """Integration tests for complete user workflows"""
    
    def test_complete_user_journey(self):
        """Test complete user journey from registration to banking operations"""
        
        # 1. Check user profile
        url = reverse('api:profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 2. List accounts
        url = reverse('api:account-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 3. Make a deposit
        url = reverse('api:account-deposit', kwargs={'pk': self.checking_account.pk})
        data = {'amount': '500.00', 'description': 'Salary deposit'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 4. Transfer money
        url = reverse('api:account-transfer', kwargs={'pk': self.checking_account.pk})
        data = {
            'to_account': self.savings_account.account_number,
            'amount': '200.00',
            'description': 'Savings transfer'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 5. Check transaction history
        url = reverse('api:transaction-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)
        
        # 6. Apply for loan
        url = reverse('api:loan-application-list')
        data = {
            'loan_type': 'personal',
            'amount': '5000.00',
            'term_months': 12,
            'purpose': 'home_improvement',
            'employment_status': 'employed',
            'annual_income': '50000.00'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 7. Check analytics
        url = reverse('api:analytics-account-summary')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_webhook_integration_flow(self):
        """Test complete webhook integration workflow"""
        
        # 1. Create webhook endpoint
        url = reverse('api:webhook-endpoint-list')
        data = {
            'name': 'Integration Test Webhook',
            'url': 'https://httpbin.org/post',
            'events': ['transaction.completed', 'account.created']
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        endpoint_id = response.data['id']
        
        # 2. Test webhook endpoint
        url = reverse('api:webhook-endpoint-test', kwargs={'pk': endpoint_id})
        test_data = {
            'payload': {'test': True, 'message': 'Integration test'},
            'timeout': 30
        }
        response = self.client.post(url, test_data, format='json')
        # Note: This might fail if httpbin.org is not accessible, but test structure is correct
        
        # 3. Trigger an event that should send webhook
        deposit_url = reverse('api:account-deposit', kwargs={'pk': self.checking_account.pk})
        data = {'amount': '100.00', 'description': 'Webhook test deposit'}
        response = self.client.post(deposit_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 4. Check webhook events
        events_url = reverse('api:webhook-event-list')
        response = self.client.get(events_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# Test runner utilities
class APITestRunner:
    """Utility class for running API tests with reporting"""
    
    @staticmethod
    def run_performance_tests():
        """Run performance-specific tests"""
        from django.test.utils import get_runner
        from django.conf import settings
        
        TestRunner = get_runner(settings)
        test_runner = TestRunner()
        
        # Run only performance tests
        failures = test_runner.run_tests(['api.tests.PerformanceTestCase'])
        
        return failures == 0
    
    @staticmethod
    def run_integration_tests():
        """Run integration tests"""
        from django.test.utils import get_runner
        from django.conf import settings
        
        TestRunner = get_runner(settings)
        test_runner = TestRunner()
        
        # Run only integration tests
        failures = test_runner.run_tests(['api.tests.IntegrationTestCase'])
        
        return failures == 0
    
    @staticmethod
    def generate_test_report():
        """Generate comprehensive test report"""
        import io
        import sys
        from django.test.utils import get_runner
        from django.conf import settings
        
        # Capture test output
        output = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = output
        
        try:
            TestRunner = get_runner(settings)
            test_runner = TestRunner(verbosity=2)
            
            # Run all API tests
            failures = test_runner.run_tests(['api.tests'])
            
            test_output = output.getvalue()
            
            return {
                'success': failures == 0,
                'output': test_output,
                'failure_count': failures
            }
            
        finally:
            sys.stdout = old_stdout
