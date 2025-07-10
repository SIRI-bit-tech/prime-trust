"""
Management command to test webhook email notifications
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from api.webhook_delivery import WebhookEventTrigger
from api.models import WebhookEndpoint

User = get_user_model()


class Command(BaseCommand):
    help = 'Test webhook email notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='User ID to test webhook emails for'
        )
        parser.add_argument(
            '--event-type',
            type=str,
            default='user.created',
            help='Type of webhook event to trigger (default: user.created)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO('Testing webhook email notifications...'))
        
        # Get user
        user_id = options.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                raise CommandError(f'User with ID {user_id} not found')
        else:
            # Use first active user
            user = User.objects.filter(is_active=True).first()
            if not user:
                raise CommandError('No active users found')
        
        self.stdout.write(f'Using user: {user.email} (ID: {user.id})')
        
        # Create a test webhook endpoint with email notifications enabled
        endpoint, created = WebhookEndpoint.objects.get_or_create(
            user=user,
            name='Test Email Webhook',
            defaults={
                'url': 'https://httpbin.org/post',
                'events': [options['event_type']],
                'is_active': True,
                'email_notifications_enabled': True,
            }
        )
        
        if created:
            self.stdout.write(f'Created test webhook endpoint: {endpoint.name}')
        else:
            # Update to enable email notifications
            endpoint.email_notifications_enabled = True
            endpoint.events = [options['event_type']]
            endpoint.save()
            self.stdout.write(f'Updated existing webhook endpoint: {endpoint.name}')
        
        # Trigger webhook event
        event_type = options['event_type']
        self.stdout.write(f'Triggering webhook event: {event_type}')
        
        # Prepare test data based on event type
        if event_type == 'user.created':
            test_data = {
                'user_id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined.isoformat()
            }
        elif event_type == 'transaction.completed':
            test_data = {
                'transaction_id': 'test-123',
                'amount': '100.00',
                'transaction_type': 'transfer',
                'description': 'Test transaction',
                'reference': 'TEST-REF-123',
                'from_account': 'XXXX1234',
                'to_account': 'XXXX5678',
                'created_at': user.date_joined.isoformat()
            }
        elif event_type.startswith('security.'):
            test_data = {
                'user_id': user.id,
                'ip_address': '192.168.1.100',
                'user_agent': 'Mozilla/5.0 Test Browser',
                'details': 'Test security event'
            }
        else:
            test_data = {
                'user_id': user.id,
                'test_field': 'test_value',
                'timestamp': user.date_joined.isoformat()
            }
        
        # Trigger the webhook event
        try:
            event = WebhookEventTrigger.trigger_event(
                event_type=event_type,
                user=user,
                data=test_data
            )
            
            self.stdout.write(self.style.SUCCESS(f'✅ Webhook event triggered successfully!'))
            self.stdout.write(f'Event ID: {event.id}')
            self.stdout.write(f'Event Type: {event.event_type}')
            self.stdout.write(f'Status: {event.status}')
            
            if endpoint.email_notifications_enabled:
                self.stdout.write(self.style.WARNING('📧 Email notification should be sent (check logs and email)'))
            else:
                self.stdout.write(self.style.WARNING('📧 Email notifications are disabled for this endpoint'))
            
            # Check if event was processed
            import time
            time.sleep(2)  # Give it a moment to process
            
            event.refresh_from_db()
            self.stdout.write(f'Final status: {event.status}')
            
            # Show delivery results
            deliveries = event.deliveries.all()
            if deliveries:
                for delivery in deliveries:
                    self.stdout.write(f'Delivery to {delivery.webhook_endpoint.name}: {delivery.status}')
            else:
                self.stdout.write('No deliveries found')
                
        except Exception as e:
            raise CommandError(f'Failed to trigger webhook event: {str(e)}')
        
        self.stdout.write(self.style.SUCCESS('✅ Webhook email test completed!')) 