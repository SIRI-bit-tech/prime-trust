"""
Management command to test Gmail API setup
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.gmail_service import get_gmail_service, send_gmail
import os


class Command(BaseCommand):
    help = 'Test Gmail API setup and send test email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-email',
            type=str,
            help='Email address to send test email to'
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Only check configuration without sending email'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO('Testing Gmail API setup...'))
        
        # Check environment variables
        self.check_environment()
        
        # Check file existence
        self.check_files()
        
        # Test Gmail API connection
        self.test_connection()
        
        # Send test email if requested
        if options['test_email'] and not options['check_only']:
            self.send_test_email(options['test_email'])
        
        self.stdout.write(self.style.SUCCESS('Gmail API test completed!'))

    def check_environment(self):
        """Check required environment variables"""
        self.stdout.write('Checking environment variables...')
        
        required_vars = [
            'GMAIL_SENDER_EMAIL',
            'GMAIL_OAUTH_CREDENTIALS_FILE',
            'GMAIL_TOKEN_FILE',
        ]
        
        missing_vars = []
        for var in required_vars:
            value = getattr(settings, var, None)
            if not value:
                missing_vars.append(var)
            else:
                self.stdout.write(f'  ✓ {var}: {value}')
        
        if missing_vars:
            raise CommandError(f'Missing environment variables: {", ".join(missing_vars)}')

    def check_files(self):
        """Check required files exist"""
        self.stdout.write('Checking credential files...')
        
        credentials_file = settings.GMAIL_OAUTH_CREDENTIALS_FILE
        token_file = settings.GMAIL_TOKEN_FILE
        
        if not os.path.exists(credentials_file):
            self.stdout.write(
                self.style.WARNING(f'  ⚠ OAuth credentials file missing: {credentials_file}')
            )
            self.stdout.write(
                '    Download from Google Cloud Console and place in credentials/ folder'
            )
        else:
            self.stdout.write(f'  ✓ OAuth credentials file found: {credentials_file}')
        
        if not os.path.exists(token_file):
            self.stdout.write(
                self.style.WARNING(f'  ⚠ Token file missing: {token_file}')
            )
            self.stdout.write(
                '    Will be created automatically during first OAuth flow'
            )
        else:
            self.stdout.write(f'  ✓ Token file found: {token_file}')

    def test_connection(self):
        """Test Gmail API connection"""
        self.stdout.write('Testing Gmail API connection...')
        
        try:
            gmail_service = get_gmail_service()
            success, message = gmail_service.test_connection()
            
            if success:
                self.stdout.write(f'  ✓ {message}')
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ {message}'))
                raise CommandError('Gmail API connection failed')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Connection error: {str(e)}'))
            if 'credentials' in str(e).lower():
                self.stdout.write(
                    '    Please run the OAuth flow by trying to send an email first'
                )
            raise CommandError('Gmail API connection failed')

    def send_test_email(self, test_email):
        """Send a test email"""
        self.stdout.write(f'Sending test email to {test_email}...')
        
        try:
            subject = 'PrimeTrust Gmail API Test'
            text_content = """
This is a test email from PrimeTrust banking application.

If you received this email, the Gmail API integration is working correctly.

Best regards,
PrimeTrust Team
            """.strip()
            
            html_content = """
<html>
<body>
    <h2>PrimeTrust Gmail API Test</h2>
    <p>This is a test email from PrimeTrust banking application.</p>
    <p>If you received this email, the Gmail API integration is working correctly.</p>
    <hr>
    <p><strong>Best regards,</strong><br>PrimeTrust Team</p>
</body>
</html>
            """.strip()
            
            success, result = send_gmail(
                to_emails=[test_email],
                subject=subject,
                text_content=text_content,
                html_content=html_content,
                headers={'X-Test-Email': 'true'}
            )
            
            if success:
                self.stdout.write(f'  ✓ Test email sent successfully! Message ID: {result}')
            else:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed to send test email: {result}'))
                raise CommandError('Test email failed')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ Test email error: {str(e)}'))
            raise CommandError('Test email failed') 