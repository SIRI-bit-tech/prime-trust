"""
Comprehensive Audit Logging System for PrimeTrust Banking
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.db.models import Q
from django.core.serializers.json import DjangoJSONEncoder
from accounts.models_security import SecurityEvent
from accounts.models import CustomUser
from django.contrib.gis.geoip2 import GeoIP2

# Configure logging
logger = logging.getLogger(__name__)

class AuditLogger:
    """Production-grade audit logging system"""
    
    # Event categories
    AUTHENTICATION_EVENTS = [
        'LOGIN_ATTEMPT', 'LOGIN_SUCCESS', 'LOGIN_FAILED', 'LOGIN_2FA_SUCCESS',
        'LOGIN_2FA_FAILED', 'LOGOUT', 'PASSWORD_CHANGED', 'ACCOUNT_LOCKED',
        'ACCOUNT_UNLOCKED', 'SESSION_EXPIRED'
    ]
    
    FINANCIAL_EVENTS = [
        'TRANSACTION_INITIATED', 'TRANSACTION_COMPLETED', 'TRANSACTION_FAILED',
        'DEPOSIT_INITIATED', 'DEPOSIT_COMPLETED', 'WITHDRAWAL_INITIATED',
        'WITHDRAWAL_COMPLETED', 'TRANSFER_INITIATED', 'TRANSFER_COMPLETED',
        'PAYMENT_INITIATED', 'PAYMENT_COMPLETED', 'LOAN_APPLIED', 'LOAN_APPROVED',
        'LOAN_PAYMENT', 'INVESTMENT_PURCHASE', 'INVESTMENT_SALE', 'BITCOIN_PURCHASE',
        'BITCOIN_SALE', 'CARD_TRANSACTION', 'BILL_PAYMENT'
    ]
    
    SECURITY_EVENTS = [
        '2FA_ENABLED', '2FA_DISABLED', '2FA_SUCCESS', '2FA_FAILED',
        'DEVICE_REGISTERED', 'DEVICE_TRUSTED', 'DEVICE_REVOKED',
        'SUSPICIOUS_ACTIVITY', 'FRAUD_DETECTED', 'SECURITY_ALERT',
        'PASSWORD_RESET', 'EMAIL_CHANGED', 'PHONE_CHANGED'
    ]
    
    ADMINISTRATIVE_EVENTS = [
        'PROFILE_UPDATED', 'SETTINGS_CHANGED', 'PREFERENCES_UPDATED',
        'ACCOUNT_CREATED', 'ACCOUNT_DELETED', 'ACCOUNT_SUSPENDED',
        'PERMISSIONS_CHANGED', 'ROLE_CHANGED', 'API_KEY_CREATED',
        'API_KEY_REVOKED', 'DATA_EXPORT', 'DATA_IMPORT'
    ]
    
    def __init__(self, user: Optional[CustomUser] = None, request=None):
        self.user = user
        self.request = request
        self.session_id = self.get_session_id()
        self.ip_address = self.get_client_ip() if request else None
        self.user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
    
    def get_session_id(self) -> str:
        """Get session ID from request"""
        if self.request and hasattr(self.request, 'session'):
            return self.request.session.session_key or 'anonymous'
        return 'system'
    
    def get_client_ip(self) -> str:
        """Get client IP address"""
        if not self.request:
            return '127.0.0.1'
        
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip or '127.0.0.1'
    
    def log_event(self, event_type: str, severity: str = 'info', 
                  details: str = '', metadata: Dict[str, Any] = None,
                  affected_object: Any = None, affected_object_id: str = None) -> SecurityEvent:
        """Log audit event with comprehensive information"""
        
        try:
            # Map severity to risk_level
            severity_to_risk_map = {
                'info': 'low',
                'warning': 'medium', 
                'error': 'high',
                'critical': 'critical'
            }
            risk_level = severity_to_risk_map.get(severity, 'low')

            # Validate event_type
            valid_event_types = [et[0] for et in SecurityEvent.EVENT_TYPES]
            if event_type not in valid_event_types:
                event_type = 'other'

            # Prepare metadata - store as additional_data since SecurityEvent uses JSONField
            audit_metadata = {
                'session_id': self.session_id,
                'timestamp': timezone.now().isoformat(),
                'user_id': self.user.id if self.user else None,
                'user_email': self.user.email if self.user else None,
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'event_category': self.get_event_category(event_type),
                'affected_object_type': affected_object.__class__.__name__ if affected_object else None,
                'affected_object_id': affected_object_id or (str(affected_object.id) if affected_object and hasattr(affected_object, 'id') else None),
            }
            # Add custom metadata
            if metadata:
                audit_metadata.update(metadata)

            # GeoIP2 lookup for city/country
            city = ''
            country = ''
            if self.ip_address and self.ip_address != '127.0.0.1':
                try:
                    geoip = GeoIP2()
                    geo = geoip.city(self.ip_address)
                    city = geo.get('city', '')
                    country = geo.get('country_name', '')
                except Exception:
                    pass

            # Create security event with correct field names
            security_event = SecurityEvent.objects.create(
                user=self.user,
                event_type=event_type,
                risk_level=risk_level,
                description=details,
                ip_address=self.ip_address,
                user_agent=self.user_agent,
                city=city,
                country=country,
                additional_data=audit_metadata,  # Use additional_data instead of metadata
            )
            
            # Log to system logger for external monitoring
            self.log_to_system(event_type, severity, details, audit_metadata)
            
            return security_event
            
        except Exception as e:
            logger.error(f"Error logging audit event: {str(e)}")
            return None
    
    def log_to_system(self, event_type: str, severity: str, details: str, metadata: Dict[str, Any]):
        """Log to system logger for external monitoring tools"""
        
        log_entry = {
            'audit_event': event_type,
            'severity': severity,
            'details': details,
            'metadata': metadata,
            'timestamp': timezone.now().isoformat()
        }
        
        # Use appropriate log level
        if severity == 'error':
            logger.error(f"AUDIT: {json.dumps(log_entry, cls=DjangoJSONEncoder)}")
        elif severity == 'warning':
            logger.warning(f"AUDIT: {json.dumps(log_entry, cls=DjangoJSONEncoder)}")
        elif severity == 'critical':
            logger.critical(f"AUDIT: {json.dumps(log_entry, cls=DjangoJSONEncoder)}")
        else:
            logger.info(f"AUDIT: {json.dumps(log_entry, cls=DjangoJSONEncoder)}")
    
    def get_event_category(self, event_type: str) -> str:
        """Get event category based on event type"""
        if event_type in self.AUTHENTICATION_EVENTS:
            return 'authentication'
        elif event_type in self.FINANCIAL_EVENTS:
            return 'financial'
        elif event_type in self.SECURITY_EVENTS:
            return 'security'
        elif event_type in self.ADMINISTRATIVE_EVENTS:
            return 'administrative'
        else:
            return 'other'
    
    # Convenience methods for common events
    
    def log_login_attempt(self, success: bool, method: str = 'password'):
        """Log login attempt"""
        event_type = 'LOGIN_SUCCESS' if success else 'LOGIN_FAILED'
        severity = 'info' if success else 'warning'
        details = f"Login attempt with {method}"
        
        metadata = {
            'login_method': method,
            'success': success,
            'attempt_time': timezone.now().isoformat()
        }
        
        return self.log_event(event_type, severity, details, metadata)
    
    def log_financial_transaction(self, transaction_type: str, amount: float, 
                                currency: str = 'USD', account_id: str = None,
                                reference: str = None, status: str = 'completed'):
        """Log financial transaction"""
        event_type = f"{transaction_type.upper()}_{'COMPLETED' if status == 'completed' else 'INITIATED'}"
        severity = 'info' if status == 'completed' else 'warning'
        details = f"{transaction_type} of {amount} {currency}"
        
        metadata = {
            'transaction_type': transaction_type,
            'amount': amount,
            'currency': currency,
            'account_id': account_id,
            'reference': reference,
            'status': status,
            'transaction_time': timezone.now().isoformat()
        }
        
        return self.log_event(event_type, severity, details, metadata)
    
    def log_security_event(self, event_type: str, details: str = '', 
                          risk_level: str = 'low', action_taken: str = None):
        """Log security event"""
        severity_map = {
            'low': 'info',
            'medium': 'warning',
            'high': 'error',
            'critical': 'critical'
        }
        
        severity = severity_map.get(risk_level, 'info')
        
        metadata = {
            'risk_level': risk_level,
            'action_taken': action_taken,
            'security_event_time': timezone.now().isoformat()
        }
        
        return self.log_event(event_type, severity, details, metadata)
    
    def log_administrative_action(self, action: str, target_object: Any = None,
                                changes: Dict[str, Any] = None):
        """Log administrative action"""
        event_type = action.upper().replace(' ', '_')
        details = f"Administrative action: {action}"
        
        metadata = {
            'action': action,
            'changes': changes or {},
            'admin_action_time': timezone.now().isoformat()
        }
        
        return self.log_event(event_type, 'info', details, metadata, target_object)
    
    def log_data_access(self, resource: str, action: str, data_type: str = None):
        """Log data access"""
        event_type = f"DATA_{action.upper()}"
        details = f"Data access: {action} on {resource}"
        
        metadata = {
            'resource': resource,
            'action': action,
            'data_type': data_type,
            'access_time': timezone.now().isoformat()
        }
        
        return self.log_event(event_type, 'info', details, metadata)
    
    def log_api_access(self, endpoint: str, method: str, status_code: int,
                      response_time: float = None):
        """Log API access"""
        event_type = 'API_ACCESS'
        details = f"API access: {method} {endpoint} -> {status_code}"
        
        metadata = {
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'response_time': response_time,
            'api_access_time': timezone.now().isoformat()
        }
        
        severity = 'warning' if status_code >= 400 else 'info'
        return self.log_event(event_type, severity, details, metadata)


class AuditQueryManager:
    """Manager for querying audit logs with advanced filtering"""
    
    def __init__(self, user: CustomUser = None):
        self.user = user
    
    def get_events(self, start_date: datetime = None, end_date: datetime = None,
                   event_types: List[str] = None, severity: str = None,
                   category: str = None, limit: int = 100) -> List[SecurityEvent]:
        """Get audit events with filtering"""
        
        queryset = SecurityEvent.objects.all()
        
        # Filter by user
        if self.user:
            queryset = queryset.filter(user=self.user)
        
        # Filter by date range
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        # Filter by event types
        if event_types:
            queryset = queryset.filter(event_type__in=event_types)
        
        # Filter by severity (map to risk_level)
        if severity:
            # Map old severity names to risk_level
            severity_to_risk_map = {
                'info': 'low',
                'warning': 'medium',
                'error': 'high',
                'critical': 'critical'
            }
            risk_level = severity_to_risk_map.get(severity, severity)
            queryset = queryset.filter(risk_level=risk_level)
        
        # Filter by category
        if category:
            category_events = getattr(AuditLogger, f"{category.upper()}_EVENTS", [])
            if category_events:
                queryset = queryset.filter(event_type__in=category_events)
        
        return queryset.order_by('-created_at')[:limit]
    
    def get_financial_events(self, start_date: datetime = None, end_date: datetime = None,
                           transaction_types: List[str] = None) -> List[SecurityEvent]:
        """Get financial audit events"""
        
        return self.get_events(
            start_date=start_date,
            end_date=end_date,
            event_types=transaction_types,
            category='financial'
        )
    
    def get_security_events(self, start_date: datetime = None, end_date: datetime = None,
                           risk_levels: List[str] = None) -> List[SecurityEvent]:
        """Get security audit events"""
        
        events = self.get_events(
            start_date=start_date,
            end_date=end_date,
            category='security'
        )
        
        if risk_levels:
            events = [e for e in events if e.additional_data.get('risk_level') in risk_levels]
        
        return events
    
    def get_event_summary(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Get audit event summary"""
        
        events = self.get_events(start_date=start_date, end_date=end_date, limit=10000)
        
        # Count by category
        category_counts = {}
        severity_counts = {}
        daily_counts = {}
        
        for event in events:
            # Category count
            category = AuditLogger().get_event_category(event.event_type)
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Severity count (use risk_level)
            severity_counts[event.risk_level] = severity_counts.get(event.risk_level, 0) + 1
            
            # Daily count
            date_key = event.created_at.strftime('%Y-%m-%d')
            daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
        
        return {
            'total_events': len(events),
            'category_breakdown': category_counts,
            'severity_breakdown': severity_counts,
            'daily_breakdown': daily_counts,
            'date_range': {
                'start': start_date.isoformat() if start_date else None,
                'end': end_date.isoformat() if end_date else None
            }
        }
    
    def detect_suspicious_patterns(self, days: int = 7) -> List[Dict[str, Any]]:
        """Detect suspicious patterns in audit logs"""
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        suspicious_patterns = []
        
        # Multiple failed login attempts
        failed_logins = SecurityEvent.objects.filter(
            user=self.user,
            event_type='LOGIN_FAILED',
            created_at__gte=start_date
        ).count()
        
        if failed_logins > 5:
            suspicious_patterns.append({
                'pattern': 'multiple_failed_logins',
                'description': f'{failed_logins} failed login attempts in {days} days',
                'severity': 'high' if failed_logins > 10 else 'medium',
                'count': failed_logins
            })
        
        # Unusual access times
        recent_events = SecurityEvent.objects.filter(
            user=self.user,
            event_type__in=['LOGIN_SUCCESS', 'API_ACCESS'],
            created_at__gte=start_date
        )
        
        unusual_hours = []
        for event in recent_events:
            hour = event.created_at.hour
            if hour < 6 or hour > 22:  # Outside normal hours
                unusual_hours.append(hour)
        
        if len(unusual_hours) > 3:
            suspicious_patterns.append({
                'pattern': 'unusual_access_times',
                'description': f'Access during unusual hours: {set(unusual_hours)}',
                'severity': 'medium',
                'count': len(unusual_hours)
            })
        
        # Multiple IP addresses
        ip_addresses = SecurityEvent.objects.filter(
            user=self.user,
            created_at__gte=start_date
        ).values_list('ip_address', flat=True).distinct()
        
        if len(ip_addresses) > 5:
            suspicious_patterns.append({
                'pattern': 'multiple_ip_addresses',
                'description': f'Access from {len(ip_addresses)} different IP addresses',
                'severity': 'medium',
                'count': len(ip_addresses)
            })
        
        return suspicious_patterns


# Middleware for automatic audit logging
class AuditMiddleware:
    """Middleware to automatically log API requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process request
        start_time = timezone.now()
        response = self.get_response(request)
        end_time = timezone.now()
        
        # Log API access
        if request.path.startswith('/api/'):
            user = request.user if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) else None
            
            audit_logger = AuditLogger(user=user, request=request)
            response_time = (end_time - start_time).total_seconds()
            
            audit_logger.log_api_access(
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                response_time=response_time
            )
        
        return response


# Utility functions for easy audit logging
def log_user_action(user: CustomUser, action: str, details: str = '', 
                   request=None, metadata: Dict[str, Any] = None):
    """Utility function to log user actions"""
    audit_logger = AuditLogger(user=user, request=request)
    return audit_logger.log_administrative_action(action, changes=metadata)


def log_transaction(user: CustomUser, transaction_type: str, amount: float,
                   currency: str = 'USD', reference: str = None, 
                   status: str = 'completed', request=None):
    """Utility function to log financial transactions"""
    audit_logger = AuditLogger(user=user, request=request)
    return audit_logger.log_financial_transaction(
        transaction_type, amount, currency, reference=reference, status=status
    )


def log_security_incident(user: CustomUser, incident_type: str, details: str = '',
                         risk_level: str = 'medium', action_taken: str = None,
                         request=None):
    """Utility function to log security incidents"""
    audit_logger = AuditLogger(user=user, request=request)
    return audit_logger.log_security_event(
        incident_type, details, risk_level, action_taken
    ) 