"""
Gmail API Service for Production Email Delivery
Handles OAuth2 authentication and email sending via Gmail API
"""
import os
import json
import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class GmailAPIService:
    """Production Gmail API service with OAuth2 authentication"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly'  # Added for connection testing
    ]
    
    def __init__(self):
        self.service = None
        self.credentials_file = getattr(settings, 'GMAIL_OAUTH_CREDENTIALS_FILE', 'credentials/gmail-oauth.json')
        self.token_file = getattr(settings, 'GMAIL_TOKEN_FILE', 'credentials/token.json')
        self.sender_email = getattr(settings, 'GMAIL_SENDER_EMAIL', None)
        self.subject_prefix = getattr(settings, 'GMAIL_SUBJECT_PREFIX', '[PrimeTrust] ')
        
        if not self.sender_email:
            raise ValueError("GMAIL_SENDER_EMAIL must be set in environment variables")
        
        self._initialize_service()
    
    def _initialize_service(self) -> None:
        """Initialize Gmail API service with OAuth2 authentication"""
        try:
            creds = self._get_credentials()
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {str(e)}")
            raise
    
    def _get_credentials(self) -> Credentials:
        """Get valid OAuth2 credentials"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
                logger.debug("Loaded existing credentials from token file")
            except Exception as e:
                logger.warning(f"Failed to load token file: {str(e)}")
        
        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed expired credentials")
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {str(e)}")
                    creds = None
            
            if not creds:
                # Run OAuth flow for new credentials
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"OAuth credentials file not found: {self.credentials_file}\n"
                        "Please download your OAuth2 credentials from Google Cloud Console"
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("Obtained new OAuth2 credentials")
            
            # Save credentials for next run
            try:
                os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                logger.info("Saved credentials to token file")
            except Exception as e:
                logger.error(f"Failed to save credentials: {str(e)}")
        
        return creds
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        text_content: str,
        html_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Tuple[bool, str]:
        """
        Send email via Gmail API
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            text_content: Plain text content
            html_content: HTML content (optional)
            attachments: List of attachment dicts with 'filename' and 'content' keys
            headers: Additional email headers
            
        Returns:
            Tuple of (success: bool, message_id_or_error: str)
        """
        try:
            message = self._create_message(
                to_emails, subject, text_content, html_content, attachments, headers
            )
            
            result = self.service.users().messages().send(
                userId='me', 
                body=message
            ).execute()
            
            message_id = result.get('id')
            logger.info(f"Email sent successfully to {to_emails}. Message ID: {message_id}")
            return True, message_id
            
        except HttpError as error:
            error_msg = f"Gmail API error: {error}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as error:
            error_msg = f"Unexpected error sending email: {error}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
    
    def _create_message(
        self,
        to_emails: List[str],
        subject: str,
        text_content: str,
        html_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Create email message for Gmail API"""
        
        # Create message
        if html_content:
            message = MIMEMultipart('alternative')
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            message.attach(text_part)
            message.attach(html_part)
        else:
            message = MIMEText(text_content, 'plain', 'utf-8')
        
        # Set headers
        message['to'] = ', '.join(to_emails)
        message['from'] = self.sender_email
        message['subject'] = f"{self.subject_prefix}{subject}"
        
        # Add custom headers
        if headers:
            for key, value in headers.items():
                message[key] = value
        
        # Add default headers
        message['Date'] = timezone.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        message['Message-ID'] = f"<{timezone.now().timestamp()}@primetrust.gmail>"
        
        # Add attachments
        if attachments:
            if not isinstance(message, MIMEMultipart):
                # Convert to multipart if we have attachments
                original_message = message
                message = MIMEMultipart()
                message.attach(original_message)
                
                # Copy headers
                for key in ['to', 'from', 'subject', 'Date', 'Message-ID']:
                    if key in original_message:
                        message[key] = original_message[key]
            
            for attachment in attachments:
                self._add_attachment(message, attachment)
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode('utf-8')
        
        return {'raw': raw_message}
    
    def _add_attachment(self, message: MIMEMultipart, attachment: Dict[str, Any]) -> None:
        """Add attachment to email message"""
        try:
            filename = attachment['filename']
            content = attachment['content']
            content_type = attachment.get('content_type', 'application/octet-stream')
            
            part = MIMEBase(*content_type.split('/', 1))
            part.set_payload(content)
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {filename}',
            )
            message.attach(part)
            
        except Exception as e:
            logger.error(f"Failed to add attachment {attachment.get('filename')}: {str(e)}")
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test Gmail API connection using labels instead of profile"""
        try:
            # Try to get labels instead of profile (less sensitive permission)
            labels = self.service.users().labels().list(userId='me').execute()
            
            # If successful, we have a working connection
            return True, f"Connected successfully as {self.sender_email}"
                
        except Exception as e:
            return False, f"Connection test failed: {str(e)}"


# Global instance for Django integration
gmail_service = None

def get_gmail_service() -> GmailAPIService:
    """Get or create Gmail service instance"""
    global gmail_service
    
    if gmail_service is None:
        try:
            gmail_service = GmailAPIService()
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {str(e)}")
            raise
    
    return gmail_service


def send_gmail(
    to_emails: List[str],
    subject: str,
    text_content: str,
    html_content: Optional[str] = None,
    attachments: Optional[List[Dict[str, Any]]] = None,
    headers: Optional[Dict[str, str]] = None
) -> Tuple[bool, str]:
    """
    Convenient function to send email via Gmail API
    
    Args:
        to_emails: List of recipient email addresses  
        subject: Email subject
        text_content: Plain text content
        html_content: HTML content (optional)
        attachments: List of attachment dicts
        headers: Additional email headers
        
    Returns:
        Tuple of (success: bool, message_id_or_error: str)
    """
    try:
        service = get_gmail_service()
        return service.send_email(
            to_emails, subject, text_content, html_content, attachments, headers
        )
    except Exception as e:
        error_msg = f"Gmail service error: {str(e)}"
        logger.error(error_msg)
        return False, error_msg 