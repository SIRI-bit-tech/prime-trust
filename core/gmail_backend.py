"""
Django Email Backend for Gmail API
Integrates Gmail API service with Django's email framework
"""
import logging
from typing import List
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage
from django.utils.html import strip_tags
from .gmail_service import get_gmail_service

logger = logging.getLogger(__name__)


class GmailBackend(BaseEmailBackend):
    """
    Django email backend using Gmail API
    """
    
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.gmail_service = None
        
    def open(self):
        """Initialize Gmail API service"""
        if self.gmail_service is None:
            try:
                self.gmail_service = get_gmail_service()
                return True
            except Exception as e:
                logger.error(f"Failed to initialize Gmail service: {str(e)}")
                if not self.fail_silently:
                    raise
                return False
        return True
    
    def close(self):
        """Close connection (no-op for Gmail API)"""
        pass
    
    def send_messages(self, email_messages: List[EmailMessage]) -> int:
        """
        Send a list of EmailMessage objects.
        Returns the number of successfully sent messages.
        """
        if not email_messages:
            return 0
            
        if not self.open():
            return 0
            
        num_sent = 0
        for message in email_messages:
            if self._send_message(message):
                num_sent += 1
                
        return num_sent
    
    def _send_message(self, message: EmailMessage) -> bool:
        """Send a single EmailMessage"""
        try:
            # Extract recipients
            to_emails = list(message.to)
            if message.cc:
                to_emails.extend(message.cc)
            if message.bcc:
                to_emails.extend(message.bcc)
                
            if not to_emails:
                logger.warning("No recipients found in email message")
                return False
            
            # Get content
            html_content = None
            text_content = message.body
            
            # Handle HTML content
            if hasattr(message, 'alternatives'):
                for content, content_type in message.alternatives:
                    if content_type == 'text/html':
                        html_content = content
                        break
            
            # If we have HTML but no text, create text version
            if html_content and not text_content:
                text_content = strip_tags(html_content)
            
            # Prepare attachments
            attachments = []
            if hasattr(message, 'attachments') and message.attachments:
                for attachment in message.attachments:
                    if len(attachment) == 3:
                        # (filename, content, mimetype)
                        filename, content, mimetype = attachment
                        attachments.append({
                            'filename': filename,
                            'content': content,
                            'content_type': mimetype or 'application/octet-stream'
                        })
                    elif len(attachment) == 2:
                        # (filename, content)
                        filename, content = attachment
                        attachments.append({
                            'filename': filename,
                            'content': content,
                            'content_type': 'application/octet-stream'
                        })
            
            # Prepare headers
            headers = {}
            if hasattr(message, 'extra_headers') and message.extra_headers:
                headers.update(message.extra_headers)
            
            # Send via Gmail API
            success, result = self.gmail_service.send_email(
                to_emails=to_emails,
                subject=message.subject,
                text_content=text_content,
                html_content=html_content,
                attachments=attachments if attachments else None,
                headers=headers if headers else None
            )
            
            if success:
                logger.info(f"Email sent successfully via Gmail API. Message ID: {result}")
                return True
            else:
                logger.error(f"Failed to send email via Gmail API: {result}")
                if not self.fail_silently:
                    raise Exception(f"Gmail API error: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}", exc_info=True)
            if not self.fail_silently:
                raise
            return False 