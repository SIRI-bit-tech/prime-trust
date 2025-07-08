"""
Performance Monitoring System for PrimeTrust Banking API

This module provides comprehensive monitoring capabilities including:
- Health checks
- Performance metrics
- System monitoring
- Alerting (without Prometheus)
"""

import time
import logging
from typing import Dict, List, Any, Optional
from datetime import timedelta, datetime
from django.db import models, connection
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Sum, F, Q, Max, Min

# Import psutil only when needed to avoid installation issues
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Import webhook models
from .models import WebhookDelivery

User = get_user_model()
logger = logging.getLogger(__name__)


class PerformanceMetric(models.Model):
    """Model to store performance metrics"""
    
    METRIC_TYPES = [
        ('api_response_time', 'API Response Time'),
        ('database_query_time', 'Database Query Time'),
        ('webhook_delivery_time', 'Webhook Delivery Time'),
        ('user_login_time', 'User Login Time'),
        ('transaction_processing_time', 'Transaction Processing Time'),
    ]
    
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    endpoint = models.CharField(max_length=200, null=True, blank=True)
    value = models.FloatField()  # Value in milliseconds
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Additional context
    http_method = models.CharField(max_length=10, null=True, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'api_performance_metrics'
        indexes = [
            models.Index(fields=['metric_type', 'timestamp']),
            models.Index(fields=['endpoint', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.metric_type}: {self.value}ms at {self.timestamp}"


class SystemHealth(models.Model):
    """Model to store system health status"""
    
    STATUS_CHOICES = [
        ('healthy', 'Healthy'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('down', 'Down'),
    ]
    
    SERVICE_TYPES = [
        ('database', 'Database'),
        ('cache', 'Cache'),
        ('external_api', 'External API'),
        ('webhook_delivery', 'Webhook Delivery'),
        ('email_service', 'Email Service'),
        ('bitcoin_service', 'Bitcoin Service'),
    ]
    
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    response_time_ms = models.FloatField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'api_system_health'
        indexes = [
            models.Index(fields=['service_type', 'timestamp']),
            models.Index(fields=['status', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.service_type}: {self.status} at {self.timestamp}"


class AlertRule(models.Model):
    """Model to define alerting rules"""
    
    ALERT_TYPES = [
        ('response_time', 'Response Time Threshold'),
        ('error_rate', 'Error Rate Threshold'),
        ('system_resource', 'System Resource Threshold'),
        ('webhook_failure', 'Webhook Failure Rate'),
        ('database_connection', 'Database Connection Issues'),
    ]
    
    SEVERITY_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]
    
    name = models.CharField(max_length=200)
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    threshold_value = models.FloatField()
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS)
    is_active = models.BooleanField(default=True)
    
    # Notification settings
    email_notifications = models.BooleanField(default=False)
    webhook_notifications = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'api_alert_rules'
    
    def __str__(self):
        return f"{self.name} ({self.alert_type})"


class Alert(models.Model):
    """Model to store triggered alerts"""
    
    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE)
    message = models.TextField()
    current_value = models.FloatField()
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'api_alerts'
        indexes = [
            models.Index(fields=['rule', 'created_at']),
            models.Index(fields=['is_resolved', 'created_at']),
        ]
    
    def __str__(self):
        return f"Alert: {self.rule.name} - {self.message}"


class PerformanceMonitor:
    """Main performance monitoring service"""
    
    def __init__(self):
        self.cache_prefix = 'perf_monitor:'
        self.cache_timeout = 300  # 5 minutes
    
    def record_api_response_time(self, endpoint: str, response_time_ms: float, 
                                request=None, response=None):
        """Record API response time metric"""
        
        metric = PerformanceMetric.objects.create(
            metric_type='api_response_time',
            endpoint=endpoint,
            value=response_time_ms,
            http_method=getattr(request, 'method', None) if request else None,
            status_code=getattr(response, 'status_code', None) if response else None,
            user=getattr(request, 'user', None) if request and hasattr(request, 'user') else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
            ip_address=self._get_client_ip(request) if request else None
        )
        
        # Check for alert conditions
        self._check_response_time_alerts(endpoint, response_time_ms)
        
        return metric
    
    def record_database_query_time(self, query_time_ms: float, query_type: str = ''):
        """Record database query time metric"""
        
        return PerformanceMetric.objects.create(
            metric_type='database_query_time',
            endpoint=query_type,
            value=query_time_ms
        )
    
    def record_webhook_delivery_time(self, delivery_time_ms: float, endpoint_url: str, success: bool):
        """Record webhook delivery time metric"""
        
        metric = PerformanceMetric.objects.create(
            metric_type='webhook_delivery_time',
            endpoint=endpoint_url,
            value=delivery_time_ms,
            status_code=200 if success else 500
        )
        
        # Check webhook failure rate
        self._check_webhook_failure_alerts()
        
        return metric
    
    def get_performance_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        
        since = timezone.now() - timedelta(hours=hours)
        
        # API performance
        api_metrics = PerformanceMetric.objects.filter(
            metric_type='api_response_time',
            timestamp__gte=since
        )
        
        api_summary = {
            'total_requests': api_metrics.count(),
            'avg_response_time': api_metrics.aggregate(avg=Avg('value'))['avg'] or 0,
            'max_response_time': api_metrics.aggregate(max=models.Max('value'))['max'] or 0,
            'error_rate': self._calculate_error_rate(api_metrics),
            'requests_per_hour': self._calculate_requests_per_hour(api_metrics, hours)
        }
        
        # Database performance
        db_metrics = PerformanceMetric.objects.filter(
            metric_type='database_query_time',
            timestamp__gte=since
        )
        
        db_summary = {
            'total_queries': db_metrics.count(),
            'avg_query_time': db_metrics.aggregate(avg=Avg('value'))['avg'] or 0,
            'max_query_time': db_metrics.aggregate(max=models.Max('value'))['max'] or 0
        }
        
        # Webhook performance
        webhook_metrics = PerformanceMetric.objects.filter(
            metric_type='webhook_delivery_time',
            timestamp__gte=since
        )
        
        webhook_summary = {
            'total_deliveries': webhook_metrics.count(),
            'avg_delivery_time': webhook_metrics.aggregate(avg=Avg('value'))['avg'] or 0,
            'success_rate': self._calculate_webhook_success_rate(webhook_metrics)
        }
        
        return {
            'api': api_summary,
            'database': db_summary,
            'webhooks': webhook_summary,
            'system': self.get_system_metrics(),
            'period_hours': hours
        }
    
    def get_endpoint_performance(self, endpoint: str, hours: int = 24) -> Dict[str, Any]:
        """Get performance metrics for a specific endpoint"""
        
        since = timezone.now() - timedelta(hours=hours)
        
        metrics = PerformanceMetric.objects.filter(
            metric_type='api_response_time',
            endpoint=endpoint,
            timestamp__gte=since
        )
        
        if not metrics.exists():
            return {'error': 'No data found for this endpoint'}
        
        return {
            'endpoint': endpoint,
            'total_requests': metrics.count(),
            'avg_response_time': metrics.aggregate(avg=Avg('value'))['avg'],
            'min_response_time': metrics.aggregate(min=models.Min('value'))['min'],
            'max_response_time': metrics.aggregate(max=models.Max('value'))['max'],
            'error_rate': self._calculate_error_rate(metrics),
            'status_codes': self._get_status_code_distribution(metrics),
            'hourly_stats': self._get_hourly_stats(metrics, hours)
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource metrics"""
        
        if not PSUTIL_AVAILABLE:
            return {
                'cpu_usage_percent': 0,
                'memory_usage_percent': 0,
                'disk_usage_percent': 0,
                'database_connections': self._get_database_connections(),
                'cache_status': self._check_cache_status(),
                'timestamp': timezone.now().isoformat(),
                'note': 'psutil not available - system metrics limited'
            }
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Database connections
            db_connections = self._get_database_connections()
            
            # Cache status
            cache_status = self._check_cache_status()
            
            return {
                'cpu_usage_percent': cpu_percent,
                'memory_usage_percent': memory_percent,
                'disk_usage_percent': disk_percent,
                'database_connections': db_connections,
                'cache_status': cache_status,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        
        health_status = {}
        overall_status = 'healthy'
        
        # Database health
        db_health = self._check_database_health()
        health_status['database'] = db_health
        if db_health['status'] != 'healthy':
            overall_status = 'warning'
        
        # Cache health
        cache_health = self._check_cache_health()
        health_status['cache'] = cache_health
        if cache_health['status'] != 'healthy':
            overall_status = 'warning'
        
        # External services health
        external_health = self._check_external_services()
        health_status['external_services'] = external_health
        
        # Webhook system health
        webhook_health = self._check_webhook_health()
        health_status['webhooks'] = webhook_health
        
        # System resources
        system_health = self._check_system_resources()
        health_status['system_resources'] = system_health
        if system_health['status'] == 'critical':
            overall_status = 'critical'
        
        return {
            'status': overall_status,
            'checks': health_status,
            'timestamp': timezone.now().isoformat()
        }
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _calculate_error_rate(self, metrics) -> float:
        """Calculate error rate from metrics"""
        total = metrics.count()
        if total == 0:
            return 0.0
        
        errors = metrics.filter(status_code__gte=400).count()
        return (errors / total) * 100
    
    def _calculate_requests_per_hour(self, metrics, hours: int) -> float:
        """Calculate requests per hour"""
        total = metrics.count()
        return total / hours if hours > 0 else 0
    
    def _calculate_webhook_success_rate(self, metrics) -> float:
        """Calculate webhook success rate"""
        total = metrics.count()
        if total == 0:
            return 100.0
        
        successful = metrics.filter(status_code=200).count()
        return (successful / total) * 100
    
    def _get_status_code_distribution(self, metrics) -> Dict[str, int]:
        """Get distribution of status codes"""
        return dict(
            metrics.values('status_code')
            .annotate(count=Count('id'))
            .values_list('status_code', 'count')
        )
    
    def _get_hourly_stats(self, metrics, hours: int) -> List[Dict[str, Any]]:
        """Get hourly statistics"""
        stats = []
        now = timezone.now()
        
        for i in range(hours):
            hour_start = now - timedelta(hours=i+1)
            hour_end = now - timedelta(hours=i)
            
            hour_metrics = metrics.filter(
                timestamp__gte=hour_start,
                timestamp__lt=hour_end
            )
            
            stats.append({
                'hour': hour_start.strftime('%Y-%m-%d %H:00'),
                'request_count': hour_metrics.count(),
                'avg_response_time': hour_metrics.aggregate(avg=Avg('value'))['avg'] or 0,
                'error_count': hour_metrics.filter(status_code__gte=400).count()
            })
        
        return list(reversed(stats))
    
    def _get_database_connections(self) -> int:
        """Get number of active database connections"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active'")
                return cursor.fetchone()[0]
        except Exception:
            return 0
    
    def _check_cache_status(self) -> Dict[str, Any]:
        """Check cache system status"""
        try:
            test_key = 'health_check_test'
            cache.set(test_key, 'test_value', 30)
            retrieved_value = cache.get(test_key)
            cache.delete(test_key)
            
            return {
                'status': 'healthy' if retrieved_value == 'test_value' else 'error',
                'response_time_ms': 1  # Cache is usually very fast
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            start_time = time.time()
            
            # Simple query to check database
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            response_time = (time.time() - start_time) * 1000
            
            # Record health status
            SystemHealth.objects.create(
                service_type='database',
                status='healthy',
                response_time_ms=response_time
            )
            
            return {
                'status': 'healthy',
                'response_time_ms': response_time
            }
            
        except Exception as e:
            SystemHealth.objects.create(
                service_type='database',
                status='critical',
                error_message=str(e)
            )
            
            return {
                'status': 'critical',
                'error': str(e)
            }
    
    def _check_cache_health(self) -> Dict[str, Any]:
        """Check cache health"""
        try:
            start_time = time.time()
            
            test_key = 'health_check'
            cache.set(test_key, 'test', 10)
            value = cache.get(test_key)
            cache.delete(test_key)
            
            response_time = (time.time() - start_time) * 1000
            
            status = 'healthy' if value == 'test' else 'warning'
            
            SystemHealth.objects.create(
                service_type='cache',
                status=status,
                response_time_ms=response_time
            )
            
            return {
                'status': status,
                'response_time_ms': response_time
            }
            
        except Exception as e:
            SystemHealth.objects.create(
                service_type='cache',
                status='critical',
                error_message=str(e)
            )
            
            return {
                'status': 'critical',
                'error': str(e)
            }
    
    def _check_external_services(self) -> Dict[str, Any]:
        """Check external services health"""
        services = {}
        
        # Check Bitcoin price API (example)
        try:
            import requests
            start_time = time.time()
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd',
                timeout=5
            )
            response_time = (time.time() - start_time) * 1000
            
            services['bitcoin_api'] = {
                'status': 'healthy' if response.status_code == 200 else 'warning',
                'response_time_ms': response_time
            }
            
        except Exception as e:
            services['bitcoin_api'] = {
                'status': 'error',
                'error': str(e)
            }
        
        return services
    
    def _check_webhook_health(self) -> Dict[str, Any]:
        """Check webhook system health"""
        # Check recent webhook delivery success rate
        since = timezone.now() - timedelta(hours=1)
        
        recent_deliveries = WebhookDelivery.objects.filter(
            attempted_at__gte=since
        )
        
        if not recent_deliveries.exists():
            return {
                'status': 'healthy',
                'message': 'No recent webhook deliveries'
            }
        
        total = recent_deliveries.count()
        successful = recent_deliveries.filter(status='success').count()
        success_rate = (successful / total) * 100 if total > 0 else 100
        
        status = 'healthy'
        if success_rate < 95:
            status = 'warning'
        if success_rate < 80:
            status = 'critical'
        
        return {
            'status': status,
            'success_rate': success_rate,
            'total_deliveries': total,
            'successful_deliveries': successful
        }
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        if not PSUTIL_AVAILABLE:
            return {
                'status': 'healthy',
                'note': 'psutil not available - system resource monitoring disabled'
            }
        
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status = 'healthy'
            issues = []
            
            if cpu_percent > 90:
                status = 'critical'
                issues.append(f'High CPU usage: {cpu_percent}%')
            elif cpu_percent > 70:
                status = 'warning'
                issues.append(f'Moderate CPU usage: {cpu_percent}%')
            
            if memory.percent > 90:
                status = 'critical'
                issues.append(f'High memory usage: {memory.percent}%')
            elif memory.percent > 70:
                status = 'warning'
                issues.append(f'Moderate memory usage: {memory.percent}%')
            
            if disk.percent > 90:
                status = 'critical'
                issues.append(f'High disk usage: {disk.percent}%')
            elif disk.percent > 80:
                status = 'warning'
                issues.append(f'Moderate disk usage: {disk.percent}%')
            
            return {
                'status': status,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'issues': issues
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _check_response_time_alerts(self, endpoint: str, response_time_ms: float):
        """Check if response time triggers any alerts"""
        rules = AlertRule.objects.filter(
            alert_type='response_time',
            is_active=True
        )
        
        for rule in rules:
            if response_time_ms > rule.threshold_value:
                # Check if alert already exists
                existing_alert = Alert.objects.filter(
                    rule=rule,
                    is_resolved=False,
                    created_at__gte=timezone.now() - timedelta(minutes=5)
                ).first()
                
                if not existing_alert:
                    Alert.objects.create(
                        rule=rule,
                        message=f"Response time {response_time_ms}ms exceeds threshold {rule.threshold_value}ms for {endpoint}",
                        current_value=response_time_ms
                    )
    
    def _check_webhook_failure_alerts(self):
        """Check webhook failure rate alerts"""
        rules = AlertRule.objects.filter(
            alert_type='webhook_failure',
            is_active=True
        )
        
        since = timezone.now() - timedelta(minutes=15)
        
        total_deliveries = WebhookDelivery.objects.filter(
            attempted_at__gte=since
        ).count()
        
        if total_deliveries < 10:  # Not enough data
            return
        
        failed_deliveries = WebhookDelivery.objects.filter(
            attempted_at__gte=since,
            status__in=['failed', 'error', 'timeout']
        ).count()
        
        failure_rate = (failed_deliveries / total_deliveries) * 100
        
        for rule in rules:
            if failure_rate > rule.threshold_value:
                existing_alert = Alert.objects.filter(
                    rule=rule,
                    is_resolved=False,
                    created_at__gte=timezone.now() - timedelta(minutes=10)
                ).first()
                
                if not existing_alert:
                    Alert.objects.create(
                        rule=rule,
                        message=f"Webhook failure rate {failure_rate:.1f}% exceeds threshold {rule.threshold_value}%",
                        current_value=failure_rate
                    )


# Global monitor instance
performance_monitor = PerformanceMonitor()


class PerformanceMiddleware:
    """Middleware to automatically track API performance"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.monitor = performance_monitor
    
    def __call__(self, request):
        # Start timing
        start_time = time.time()
        
        # Process request
        response = self.get_response(request)
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Record metric for API endpoints
        if request.path.startswith('/api/'):
            self.monitor.record_api_response_time(
                endpoint=request.path,
                response_time_ms=response_time_ms,
                request=request,
                response=response
            )
        
        # Add performance header
        response['X-Response-Time'] = f"{response_time_ms:.2f}ms"
        
        return response 