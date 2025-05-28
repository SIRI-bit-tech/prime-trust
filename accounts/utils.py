"""
Utility functions for the accounts app
"""
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings

def send_email_with_brevo(to_email, subject, html_content, text_content=None):
    """
    Send an email using Brevo API
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html_content (str): HTML content of the email
        text_content (str, optional): Plain text content of the email. Defaults to None.
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Debug information
    logger.info(f"Attempting to send email to {to_email} with subject: {subject}")
    logger.info(f"Using Brevo API Key: {settings.BREVO_API_KEY[:5]}...{settings.BREVO_API_KEY[-5:] if settings.BREVO_API_KEY else ''}")
    
    # Configure API key authorization
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY
    
    # Create an instance of the API class
    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
    
    # Hardcode the sender information to use Brevo email directly
    sender_name = 'PrimeTrust'
    sender_email = '8e12f3001@smtp-brevo.com'  # Your Brevo SMTP user
        
    # Log the sender information
    logger.info(f"Using sender: {sender_name} <{sender_email}>")
    
    # Set up the sender
    sender = {"name": sender_name, "email": sender_email}
    
    # Set up the recipient
    to = [{"email": to_email}]
    
    # If text_content is not provided, use html_content with tags removed
    if text_content is None:
        from django.utils.html import strip_tags
        text_content = strip_tags(html_content)
    
    try:
        # Create a SendSmtpEmail object
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to,
            html_content=html_content,
            sender=sender,
            subject=subject,
            text_content=text_content
        )
        
        # Log the email details
        logger.info(f"Email details: To: {to}, From: {sender}, Subject: {subject}")
        
        # Send the email
        api_response = api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Email sent successfully. Response: {api_response}")
        return True
    except ApiException as e:
        logger.error(f"Brevo API Exception: {e}")
        logger.error(f"Status code: {e.status}, Reason: {e.reason}")
        logger.error(f"Response body: {e.body}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email: {str(e)}")
        return False
