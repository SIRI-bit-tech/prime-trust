"""
Webhook Delivery Service for PrimeTrust Banking API

This module handles the delivery of webhooks to external endpoints with
proper retry logic, error handling, and logging.
"""

import requests
import hashlib
import hmac
import json
import time
import logging
from typing import Tuple, Dict, Any, Optional
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from .models import (
    WebhookEndpoint, WebhookEvent, WebhookDelivery, 
    WebhookSignature, WebhookTemplate, WebhookLog
)

logger = logging.getLogger(__name__)


class WebhookDeliveryService:
    """
    Service for delivering webhooks to external endpoints
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PrimeTrust-Webhook/1.0',
            'Content-Type': 'application/json'
        })
    
    def deliver_webhook(self, endpoint: WebhookEndpoint, event: WebhookEvent) -> Tuple[bool, Dict[str, Any]]:
        """
        Deliver a webhook event to an endpoint
        
        Args:
            endpoint: The webhook endpoint to deliver to
            event: The webhook event to deliver
            
        Returns:
            Tuple of (success: bool, response_data: dict)
        """
        start_time = time.time()
        
        try:
            # Update event status
            event.status = 'processing'
            event.delivery_attempts += 1
            event.save()
            
            # Prepare payload
            payload = self._prepare_payload(endpoint, event)
            headers = self._prepare_headers(endpoint, event, payload)
            
            # Create delivery record
            delivery = WebhookDelivery.objects.create(
                webhook_endpoint=endpoint,
                webhook_event=event,
                status='pending',
                request_headers=headers,
                request_body=payload,
                attempt_number=event.delivery_attempts,
                is_retry=event.delivery_attempts > 1
            )
            
            # Make the request
            response = self._make_request(endpoint, payload, headers)
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Update delivery record
            delivery.http_status_code = response.status_code
            delivery.response_body = response.text[:10000]  # Limit response body size
            delivery.response_time_ms = response_time_ms
            delivery.completed_at = timezone.now()
            
            # Check if delivery was successful
            if 200 <= response.status_code <= 299:
                delivery.status = 'success'
                event.status = 'completed'
                event.processed_at = timezone.now()
                
                # Update endpoint statistics
                endpoint.total_deliveries += 1
                endpoint.successful_deliveries += 1
                endpoint.last_used_at = timezone.now()
                endpoint.save()
                
                self._log_webhook_event(
                    endpoint, event, delivery, 'info',
                    f"Webhook delivered successfully (HTTP {response.status_code})"
                )
                
                delivery.save()
                event.save()
                
                return True, {
                    'status_code': response.status_code,
                    'response_time_ms': response_time_ms,
                    'delivery_id': str(delivery.id)
                }
            else:
                # Handle HTTP error
                delivery.status = 'failed'
                delivery.error_message = f"HTTP {response.status_code}: {response.text[:500]}"
                
                return self._handle_delivery_failure(
                    endpoint, event, delivery, 
                    f"HTTP {response.status_code} error",
                    response_time_ms
                )
                
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