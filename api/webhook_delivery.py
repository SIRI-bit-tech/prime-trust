"""
Webhook Delivery Service for PrimeTrust Banking API

This module handles the delivery of webhooks to external endpoints with
proper retry logic, error handling, and logging.
"""

import requests
import json
import time
import hmac
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache

from .models import (
    WebhookEndpoint, WebhookEvent, WebhookDelivery, 
    WebhookSignature, WebhookTemplate, WebhookLog
)

logger = logging.getLogger(__name__)


class WebhookDeliveryService:
    """
    Enhanced webhook delivery service with email notifications
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PrimeTrust-Webhook/1.0'
        })
    
    def deliver_webhook(self, endpoint: WebhookEndpoint, event: WebhookEvent) -> Tuple[bool, Dict[str, Any]]:
        """
        Deliver webhook to endpoint and optionally send email notification
        """
        # Create delivery record
        delivery = WebhookDelivery.objects.create(
            webhook_endpoint=endpoint,
            webhook_event=event,
            status='pending',
            started_at=timezone.now()
        )
        
        # Update event delivery attempts
        event.delivery_attempts += 1
        
        start_time = time.time()
        
        try:
            # Prepare payload and headers
            payload = self._prepare_payload(endpoint, event)
            headers = self._prepare_headers(endpoint, event, payload)
            
            # Make the request
            response = self._make_request(endpoint, payload, headers)
            response_time = time.time() - start_time
            
            # Update delivery record
            delivery.status = 'success' if response.status_code < 400 else 'error'
            delivery.response_code = response.status_code
            delivery.response_body = response.text[:10000]  # Limit size
            delivery.response_time_ms = int(response_time * 1000)
            delivery.completed_at = timezone.now()
            delivery.save()
            
            # Update endpoint statistics
            endpoint.total_deliveries += 1
            if response.status_code >= 400:
                endpoint.failed_deliveries += 1
            endpoint.last_delivery_at = timezone.now()
            endpoint.save()
            
            # Log the delivery
            level = 'info' if response.status_code < 400 else 'warning'
            self._log_webhook_event(
                endpoint, event, delivery, level,
                f"Webhook delivered with status {response.status_code}"
            )
            
            # Send email notification if enabled and webhook was successful
            if response.status_code < 400 and endpoint.email_notifications_enabled:
                self._send_email_notification(endpoint, event)
            
            # Mark event as completed if successful
            if response.status_code < 400:
                event.status = 'completed'
                event.processed_at = timezone.now()
            else:
                # Handle as failure for retry logic
                return self._handle_delivery_failure(
                    endpoint, event, delivery,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    response_time
                )
            
            event.save()
            
            return True, {
                'status_code': response.status_code,
                'response_body': response.text[:1000],
                'response_time_ms': int(response_time * 1000),
                'delivery_id': str(delivery.id),
                'email_sent': endpoint.email_notifications_enabled
            }
            
        except requests.exceptions.Timeout:
            return self._handle_delivery_failure(
                endpoint, event, delivery if 'delivery' in locals() else None,
                "Request timeout", time.time() - start_time
            )
            
        except requests.exceptions.ConnectionError:
            return self._handle_delivery_failure(
                endpoint, event, delivery if 'delivery' in locals() else None,
                "Connection error", time.time() - start_time
            )
            
        except Exception as e:
            return self._handle_delivery_failure(
                endpoint, event, delivery if 'delivery' in locals() else None,
                f"Unexpected error: {str(e)}", time.time() - start_time
            )
    
    def _prepare_payload(self, endpoint: WebhookEndpoint, event: WebhookEvent) -> Dict[str, Any]:
        """Prepare the payload for webhook delivery"""
        
        # Try to use template if available
        try:
            template = WebhookTemplate.objects.get(
                event_type=event.event_type,
                is_active=True
            )
            
            context_data = {
                'event_id': str(event.id),
                'event_type': event.event_type,
                'timestamp': event.created_at.isoformat(),
                'user_id': event.user.id if event.user else None,
                **event.payload
            }
            
            return template.render_payload(context_data)
            
        except WebhookTemplate.DoesNotExist:
            # Use default payload structure
            return {
                'event': {
                    'id': str(event.id),
                    'type': event.event_type,
                    'created': event.created_at.isoformat(),
                    'data': event.payload
                },
                'user': {
                    'id': event.user.id if event.user else None,
                    'email': event.user.email if event.user else None
                } if event.user else None
            }
    
    def _prepare_headers(self, endpoint: WebhookEndpoint, event: WebhookEvent, payload: Dict[str, Any]) -> Dict[str, str]:
        """Prepare headers for webhook request"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'PrimeTrust-Webhook/1.0',
            'X-Webhook-ID': str(event.id),
            'X-Webhook-Timestamp': str(int(event.created_at.timestamp())),
            'X-Webhook-Event': event.event_type,
            'X-Webhook-Attempt': str(event.delivery_attempts)
        }
        
        # Add signature if endpoint has a secret
        if endpoint.secret:
            signature = self._generate_signature(endpoint, payload)
            headers['X-Webhook-Signature'] = signature
        
        # Add custom headers from template
        try:
            template = WebhookTemplate.objects.get(
                event_type=event.event_type,
                is_active=True
            )
            headers.update(template.headers_template)
        except WebhookTemplate.DoesNotExist:
            pass
        
        return headers
    
    def _generate_signature(self, endpoint: WebhookEndpoint, payload: Dict[str, Any]) -> str:
        """Generate HMAC signature for webhook"""
        payload_string = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        signature = hmac.new(
            endpoint.secret.encode('utf-8'),
            payload_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def _make_request(self, endpoint: WebhookEndpoint, payload: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
        """Make the actual HTTP request"""
        return self.session.post(
            endpoint.url,
            json=payload,
            headers=headers,
            timeout=endpoint.timeout_seconds,
            allow_redirects=False,
            verify=True  # Always verify SSL certificates
        )
    
    def _handle_delivery_failure(self, endpoint: WebhookEndpoint, event: WebhookEvent, 
                                delivery: Optional[WebhookDelivery], error_message: str,
                                response_time: float) -> Tuple[bool, Dict[str, Any]]:
        """Handle webhook delivery failure"""
        
        response_time_ms = int(response_time * 1000) if response_time else 0
        
        # Update delivery record if it exists
        if delivery:
            delivery.status = 'error'
            delivery.error_message = error_message
            delivery.response_time_ms = response_time_ms
            delivery.completed_at = timezone.now()
            delivery.save()
        
        # Update endpoint statistics
        endpoint.total_deliveries += 1
        endpoint.failed_deliveries += 1
        endpoint.save()
        
        # Log the failure
        self._log_webhook_event(
            endpoint, event, delivery, 'error',
            f"Webhook delivery failed: {error_message}"
        )
        
        # Determine if we should retry
        if event.delivery_attempts < endpoint.max_retries:
            # Schedule retry
            event.status = 'pending'
            event.schedule_retry(endpoint.retry_delay_seconds)
            
            self._log_webhook_event(
                endpoint, event, delivery, 'info',
                f"Webhook retry scheduled (attempt {event.delivery_attempts + 1}/{endpoint.max_retries})"
            )
        else:
            # Max retries exceeded
            event.status = 'failed'
            event.processed_at = timezone.now()
            
            self._log_webhook_event(
                endpoint, event, delivery, 'error',
                f"Webhook delivery failed permanently after {event.delivery_attempts} attempts"
            )
        
        event.save()
        
        return False, {
            'error': error_message,
            'attempts': event.delivery_attempts,
            'max_retries': endpoint.max_retries,
            'will_retry': event.delivery_attempts < endpoint.max_retries,
            'response_time_ms': response_time_ms,
            'delivery_id': str(delivery.id) if delivery else None
        }
    
    def _log_webhook_event(self, endpoint: WebhookEndpoint, event: WebhookEvent,
                          delivery: Optional[WebhookDelivery], level: str, message: str):
        """Log webhook event for debugging and monitoring"""
        
        WebhookLog.objects.create(
            webhook_endpoint=endpoint,
            webhook_event=event,
            webhook_delivery=delivery,
            level=level,
            message=message,
            details={
                'event_type': event.event_type,
                'attempt_number': event.delivery_attempts,
                'endpoint_url': endpoint.url,
                'user_id': event.user.id if event.user else None
            }
        )
        
        # Also log to Django logger
        getattr(logger, level, logger.info)(
            f"Webhook {event.event_type} to {endpoint.name}: {message}"
        )

    def _send_email_notification(self, endpoint: WebhookEndpoint, event: WebhookEvent):
        """Send email notification for webhook event via Gmail API"""
        try:
            # Import here to avoid circular imports
            from banking.utils import (
                send_transaction_notification, 
                send_security_alert, 
                send_welcome_email,
                send_account_locked_notification
            )
            
            user = event.user
            if not user or not user.email:
                return
            
            # Rate limit email notifications (max 5 per user per hour)
            cache_key = f"webhook_email_{user.id}"
            email_count = cache.get(cache_key, 0)
            if email_count >= 5:
                logger.warning(f"Email notification rate limit exceeded for user {user.id}")
                return
            
            cache.set(cache_key, email_count + 1, 3600)  # 1 hour
            
            # Route to appropriate email function based on event type
            event_type = event.event_type
            
            if event_type == 'user.created':
                # Send welcome email for new users
                send_welcome_email(user)
                logger.info(f"Welcome email sent for webhook event {event.id}")
                
            elif event_type == 'transaction.completed':
                # Extract transaction details from payload
                payload = event.payload
                transaction_data = {
                    'id': payload.get('transaction_id'),
                    'amount': float(payload.get('amount', 0)),
                    'transaction_type': payload.get('transaction_type'),
                    'description': payload.get('description', ''),
                    'reference': payload.get('reference', ''),
                    'created_at': datetime.fromisoformat(payload.get('created_at', timezone.now().isoformat()))
                }
                
                # Create mock transaction object for email template
                class MockTransaction:
                    def __init__(self, data):
                        for key, value in data.items():
                            setattr(self, key, value)
                        # Mock account objects
                        self.from_account = type('MockAccount', (), {
                            'user': user,
                            'account_number': payload.get('from_account', 'XXXX1234')
                        })()
                        self.to_account = type('MockAccount', (), {
                            'user': user,
                            'account_number': payload.get('to_account', 'XXXX5678')
                        })()
                
                mock_transaction = MockTransaction(transaction_data)
                send_transaction_notification(user, mock_transaction, is_sender=True)
                logger.info(f"Transaction email sent for webhook event {event.id}")
                
            elif event_type.startswith('security.'):
                # Send security alert
                alert_type = event_type.replace('security.', '').replace('_', ' ').title()
                details = event.payload.copy()
                details.pop('user_id', None)  # Remove redundant user_id
                
                send_security_alert(user, alert_type, details)
                logger.info(f"Security alert email sent for webhook event {event.id}")
                
            elif event_type == 'account.locked':
                # Send account locked notification
                payload = event.payload
                send_account_locked_notification(
                    user=user,
                    lock_reason=payload.get('reason', 'Suspicious activity detected'),
                    activity_details=payload.get('details', 'Multiple failed login attempts'),
                    unlock_url=f"{getattr(settings, 'SITE_URL', 'https://primetrust.com')}/accounts/unlock/"
                )
                logger.info(f"Account locked email sent for webhook event {event.id}")
                
            else:
                # Generic webhook notification email
                self._send_generic_webhook_email(user, endpoint, event)
                
        except Exception as e:
            logger.error(f"Failed to send email notification for webhook {event.id}: {str(e)}")
    
    def _send_generic_webhook_email(self, user, endpoint: WebhookEndpoint, event: WebhookEvent):
        """Send generic webhook notification email"""
        try:
            from core.gmail_service import send_gmail
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            
            subject = f"Webhook Event: {event.event_type.replace('_', ' ').title()}"
            
            # Create email context
            context = {
                'user_name': user.get_full_name(),
                'event_type': event.event_type.replace('_', ' ').title(),
                'endpoint_name': endpoint.name,
                'timestamp': event.created_at.strftime('%B %d, %Y at %I:%M %p'),
                'payload': event.payload,
                'dashboard_url': f"{getattr(settings, 'SITE_URL', 'https://primetrust.com')}/dashboard/"
            }
            
            # Simple HTML template for generic webhook notifications
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <h2 style="color: #007bff;">🔔 Webhook Event Notification</h2>
                    
                    <p><strong>Hello {context['user_name']},</strong></p>
                    
                    <p>A webhook event has been triggered for your PrimeTrust account:</p>
                    
                    <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h4 style="margin-top: 0;">Event Details:</h4>
                        <ul>
                            <li><strong>Event Type:</strong> {context['event_type']}</li>
                            <li><strong>Endpoint:</strong> {context['endpoint_name']}</li>
                            <li><strong>Time:</strong> {context['timestamp']}</li>
                        </ul>
                    </div>
                    
                    <p>You can view more details in your <a href="{context['dashboard_url']}" style="color: #007bff;">account dashboard</a>.</p>
                    
                    <hr style="margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        This notification was sent because you have email notifications enabled for webhook events.
                        You can manage your notification preferences in your account settings.
                    </p>
                </div>
            </body>
            </html>
            """
            
            text_content = strip_tags(html_content)
            
            # Send via Gmail API
            if not settings.DEBUG and hasattr(settings, 'GMAIL_SENDER_EMAIL') and settings.GMAIL_SENDER_EMAIL:
                success, result = send_gmail(
                    to_emails=[user.email],
                    subject=subject,
                    text_content=text_content,
                    html_content=html_content,
                    headers={'X-Webhook-Event': event.event_type}
                )
                
                if success:
                    logger.info(f"Generic webhook email sent for event {event.id}")
                else:
                    logger.error(f"Failed to send generic webhook email: {result}")
                    
        except Exception as e:
            logger.error(f"Error sending generic webhook email: {str(e)}")


class WebhookEventTrigger:
    """
    Service for triggering webhook events based on system events
    """
    
    @staticmethod
    def trigger_event(event_type: str, user, data: Dict[str, Any], delay_seconds: int = 0):
        """
        Trigger a webhook event
        
        Args:
            event_type: The type of event (e.g., 'user.created', 'transaction.completed')
            user: The user associated with the event
            data: The event data payload
            delay_seconds: Delay before processing (for batching)
        """
        # Create the webhook event
        event = WebhookEvent.objects.create(
            event_type=event_type,
            user=user,
            payload=data,
            status='pending'
        )
        
        if delay_seconds > 0:
            event.next_retry_at = timezone.now() + timedelta(seconds=delay_seconds)
            event.save()
        
        # Find all endpoints subscribed to this event type
        endpoints = WebhookEndpoint.objects.filter(
            user=user,
            is_active=True,
            events__contains=[event_type]
        )
        
        if not endpoints.exists():
            # No endpoints subscribed, mark as completed
            event.status = 'completed'
            event.processed_at = timezone.now()
            event.save()
            return event
        
        # Schedule delivery to all subscribed endpoints
        WebhookProcessor.process_event_async(event.id)
        
        return event


class WebhookProcessor:
    """
    Background processor for webhook events
    """
    
    @staticmethod
    def process_pending_events():
        """Process all pending webhook events"""
        pending_events = WebhookEvent.objects.filter(
            status='pending',
            next_retry_at__lte=timezone.now()
        ).order_by('created_at')
        
        delivery_service = WebhookDeliveryService()
        
        for event in pending_events[:100]:  # Process in batches
            WebhookProcessor.process_event(event, delivery_service)
    
    @staticmethod
    def process_event(event: WebhookEvent, delivery_service: Optional[WebhookDeliveryService] = None):
        """Process a single webhook event"""
        if not delivery_service:
            delivery_service = WebhookDeliveryService()
        
        # Find all active endpoints subscribed to this event type
        endpoints = WebhookEndpoint.objects.filter(
            user=event.user,
            is_active=True,
            events__contains=[event.event_type]
        )
        
        if not endpoints.exists():
            event.status = 'completed'
            event.processed_at = timezone.now()
            event.save()
            return
        
        # Deliver to all endpoints
        for endpoint in endpoints:
            try:
                delivery_service.deliver_webhook(endpoint, event)
            except Exception as e:
                logger.error(f"Failed to deliver webhook {event.id} to {endpoint.name}: {e}")
    
    @staticmethod
    def process_event_async(event_id: str):
        """
        Process event asynchronously (placeholder for Celery task)
        In production, this would be a Celery task
        """
        try:
            event = WebhookEvent.objects.get(id=event_id)
            WebhookProcessor.process_event(event)
        except WebhookEvent.DoesNotExist:
            logger.error(f"Webhook event {event_id} not found")


# Convenience functions for triggering common events
def trigger_user_created(user):
    """Trigger user.created webhook event"""
    WebhookEventTrigger.trigger_event(
        'user.created',
        user,
        {
            'user_id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined.isoformat()
        }
    )


def trigger_transaction_completed(transaction):
    """Trigger transaction.completed webhook event"""
    WebhookEventTrigger.trigger_event(
        'transaction.completed',
        transaction.user,
        {
            'transaction_id': transaction.id,
            'amount': str(transaction.amount),
            'transaction_type': transaction.transaction_type,
            'description': transaction.description,
            'reference': transaction.reference,
            'from_account': transaction.from_account.account_number if transaction.from_account else None,
            'to_account': transaction.to_account.account_number if transaction.to_account else None,
            'created_at': transaction.created_at.isoformat()
        }
    )


def trigger_account_created(account):
    """Trigger account.created webhook event"""
    WebhookEventTrigger.trigger_event(
        'account.created',
        account.user,
        {
            'account_id': account.id,
            'account_number': account.account_number,
            'account_type': account.account_type,
            'routing_number': account.routing_number,
            'created_at': account.created_at.isoformat()
        }
    )


def trigger_security_event(user, event_type: str, details: Dict[str, Any]):
    """Trigger security-related webhook events"""
    WebhookEventTrigger.trigger_event(
        event_type,
        user,
        {
            'user_id': user.id,
            'timestamp': timezone.now().isoformat(),
            **details
        }
    ) 