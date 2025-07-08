"""
Health Check and Monitoring Views for PrimeTrust Banking API

This module provides endpoints for monitoring system health, performance metrics,
and operational status without requiring external monitoring tools like Prometheus.
"""

import json
from datetime import timedelta
from django.http import JsonResponse
from django.utils import timezone
from django.db import models
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from .monitoring import (
    performance_monitor, PerformanceMetric, SystemHealth, 
    Alert, AlertRule
)


@require_http_methods(["GET"])
def health_check(request):
    """
    Basic health check endpoint
    Returns 200 if system is operational
    """
    try:
        health_data = performance_monitor.health_check()
        
        # Return appropriate HTTP status based on health
        if health_data['status'] == 'critical':
            return JsonResponse(health_data, status=503)
        elif health_data['status'] == 'warning':
            return JsonResponse(health_data, status=200)
        else:
            return JsonResponse(health_data, status=200)
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=500)


@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness check for load balancers
    Returns 200 if system is ready to serve traffic
    """
    try:
        # Quick checks for essential services
        from django.db import connection
        
        # Check database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check cache
        from django.core.cache import cache
        cache.set('readiness_test', 'ok', 10)
        
        return JsonResponse({
            'status': 'ready',
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=503)


@require_http_methods(["GET"])
def liveness_check(request):
    """
    Liveness check for Kubernetes/container orchestration
    Returns 200 if application is alive
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': timezone.now().isoformat()
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def system_metrics(request):
    """
    Get comprehensive system metrics
    Requires admin privileges
    """
    try:
        metrics = performance_monitor.get_system_metrics()
        return Response(metrics)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def performance_summary(request):
    """
    Get performance summary for specified time period
    """
    try:
        hours = int(request.query_params.get('hours', 24))
        if hours > 168:  # Limit to 1 week
            hours = 168
        
        summary = performance_monitor.get_performance_summary(hours)
        return Response(summary)
        
    except ValueError:
        return Response({
            'error': 'Invalid hours parameter'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def endpoint_performance(request):
    """
    Get performance metrics for a specific endpoint
    """
    endpoint = request.query_params.get('endpoint')
    if not endpoint:
        return Response({
            'error': 'endpoint parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        hours = int(request.query_params.get('hours', 24))
        metrics = performance_monitor.get_endpoint_performance(endpoint, hours)
        return Response(metrics)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def api_analytics(request):
    """
    Get API usage analytics
    """
    try:
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        
        # Get API metrics
        api_metrics = PerformanceMetric.objects.filter(
            metric_type='api_response_time',
            timestamp__gte=since
        )
        
        # Top endpoints by request count
        top_endpoints = (
            api_metrics.values('endpoint')
            .annotate(
                request_count=models.Count('id'),
                avg_response_time=models.Avg('value'),
                error_count=models.Count('id', filter=models.Q(status_code__gte=400))
            )
            .order_by('-request_count')[:10]
        )
        
        # Slowest endpoints
        slowest_endpoints = (
            api_metrics.values('endpoint')
            .annotate(
                avg_response_time=models.Avg('value'),
                request_count=models.Count('id')
            )
            .filter(request_count__gte=10)  # At least 10 requests
            .order_by('-avg_response_time')[:10]
        )
        
        # Error rates by endpoint
        error_endpoints = (
            api_metrics.values('endpoint')
            .annotate(
                total_requests=models.Count('id'),
                error_requests=models.Count('id', filter=models.Q(status_code__gte=400))
            )
            .filter(total_requests__gte=10)
            .annotate(
                error_rate=models.F('error_requests') * 100.0 / models.F('total_requests')
            )
            .order_by('-error_rate')[:10]
        )
        
        # Response time percentiles
        response_times = list(api_metrics.values_list('value', flat=True).order_by('value'))
        percentiles = {}
        if response_times:
            percentiles = {
                'p50': response_times[int(len(response_times) * 0.5)],
                'p75': response_times[int(len(response_times) * 0.75)],
                'p90': response_times[int(len(response_times) * 0.9)],
                'p95': response_times[int(len(response_times) * 0.95)],
                'p99': response_times[int(len(response_times) * 0.99)],
            }
        
        return Response({
            'period_hours': hours,
            'total_requests': api_metrics.count(),
            'top_endpoints': list(top_endpoints),
            'slowest_endpoints': list(slowest_endpoints),
            'highest_error_rates': list(error_endpoints),
            'response_time_percentiles': percentiles,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def system_health_history(request):
    """
    Get system health history
    """
    try:
        hours = int(request.query_params.get('hours', 24))
        since = timezone.now() - timedelta(hours=hours)
        
        health_records = SystemHealth.objects.filter(
            timestamp__gte=since
        ).order_by('-timestamp')
        
        # Group by service type
        health_by_service = {}
        for record in health_records:
            service = record.service_type
            if service not in health_by_service:
                health_by_service[service] = []
            
            health_by_service[service].append({
                'status': record.status,
                'response_time_ms': record.response_time_ms,
                'error_message': record.error_message,
                'timestamp': record.timestamp.isoformat()
            })
        
        # Calculate uptime percentages
        uptime_stats = {}
        for service, records in health_by_service.items():
            total = len(records)
            healthy = len([r for r in records if r['status'] == 'healthy'])
            uptime_stats[service] = {
                'uptime_percentage': (healthy / total * 100) if total > 0 else 100,
                'total_checks': total,
                'healthy_checks': healthy
            }
        
        return Response({
            'period_hours': hours,
            'health_by_service': health_by_service,
            'uptime_stats': uptime_stats,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def active_alerts(request):
    """
    Get active alerts
    """
    try:
        alerts = Alert.objects.filter(
            is_resolved=False
        ).select_related('rule').order_by('-created_at')
        
        alert_data = []
        for alert in alerts:
            alert_data.append({
                'id': alert.id,
                'rule_name': alert.rule.name,
                'alert_type': alert.rule.alert_type,
                'severity': alert.rule.severity,
                'message': alert.message,
                'current_value': alert.current_value,
                'threshold_value': alert.rule.threshold_value,
                'created_at': alert.created_at.isoformat()
            })
        
        return Response({
            'active_alerts': alert_data,
            'total_count': len(alert_data),
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def resolve_alert(request, alert_id):
    """
    Resolve an active alert
    """
    try:
        alert = Alert.objects.get(id=alert_id, is_resolved=False)
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        
        return Response({
            'message': 'Alert resolved successfully',
            'alert_id': alert_id
        })
        
    except Alert.DoesNotExist:
        return Response({
            'error': 'Alert not found or already resolved'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
@permission_classes([IsAdminUser])
def alert_rules(request):
    """
    Manage alert rules
    """
    if request.method == 'GET':
        rules = AlertRule.objects.all().order_by('-created_at')
        
        rule_data = []
        for rule in rules:
            rule_data.append({
                'id': rule.id,
                'name': rule.name,
                'alert_type': rule.alert_type,
                'threshold_value': rule.threshold_value,
                'severity': rule.severity,
                'is_active': rule.is_active,
                'email_notifications': rule.email_notifications,
                'webhook_notifications': rule.webhook_notifications,
                'created_at': rule.created_at.isoformat()
            })
        
        return Response({
            'alert_rules': rule_data,
            'total_count': len(rule_data)
        })
    
    elif request.method == 'POST':
        try:
            rule = AlertRule.objects.create(
                name=request.data['name'],
                alert_type=request.data['alert_type'],
                threshold_value=float(request.data['threshold_value']),
                severity=request.data['severity'],
                email_notifications=request.data.get('email_notifications', False),
                webhook_notifications=request.data.get('webhook_notifications', False)
            )
            
            return Response({
                'message': 'Alert rule created successfully',
                'rule_id': rule.id
            }, status=status.HTTP_201_CREATED)
            
        except KeyError as e:
            return Response({
                'error': f'Missing required field: {e}'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def database_metrics(request):
    """
    Get database performance metrics
    """
    try:
        from django.db import connection
        
        # Get database statistics
        with connection.cursor() as cursor:
            # Active connections
            cursor.execute("""
                SELECT COUNT(*) as active_connections,
                       COUNT(CASE WHEN state = 'active' THEN 1 END) as active_queries,
                       COUNT(CASE WHEN state = 'idle' THEN 1 END) as idle_connections
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)
            conn_stats = cursor.fetchone()
            
            # Database size
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                       pg_database_size(current_database()) as db_size_bytes
            """)
            size_stats = cursor.fetchone()
            
            # Recent query performance
            hours = int(request.query_params.get('hours', 1))
            since = timezone.now() - timedelta(hours=hours)
            
            db_metrics = PerformanceMetric.objects.filter(
                metric_type='database_query_time',
                timestamp__gte=since
            )
            
            query_stats = {
                'total_queries': db_metrics.count(),
                'avg_query_time': db_metrics.aggregate(avg=models.Avg('value'))['avg'] or 0,
                'max_query_time': db_metrics.aggregate(max=models.Max('value'))['max'] or 0,
                'min_query_time': db_metrics.aggregate(min=models.Min('value'))['min'] or 0
            }
        
        return Response({
            'connection_stats': {
                'active_connections': conn_stats[0],
                'active_queries': conn_stats[1],
                'idle_connections': conn_stats[2]
            },
            'database_size': {
                'human_readable': size_stats[0],
                'bytes': size_stats[1]
            },
            'query_performance': query_stats,
            'period_hours': hours,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@cache_page(60)  # Cache for 1 minute
@require_http_methods(["GET"])
def monitoring_dashboard_data(request):
    """
    Get comprehensive monitoring data for dashboard
    Cached for performance
    """
    try:
        # Get recent metrics
        since_1h = timezone.now() - timedelta(hours=1)
        since_24h = timezone.now() - timedelta(hours=24)
        
        # API metrics
        api_metrics_1h = PerformanceMetric.objects.filter(
            metric_type='api_response_time',
            timestamp__gte=since_1h
        )
        
        api_metrics_24h = PerformanceMetric.objects.filter(
            metric_type='api_response_time',
            timestamp__gte=since_24h
        )
        
        # System health
        latest_health = SystemHealth.objects.order_by('-timestamp')[:10]
        
        # Active alerts
        active_alerts_count = Alert.objects.filter(is_resolved=False).count()
        
        # System resources
        system_metrics = performance_monitor.get_system_metrics()
        
        dashboard_data = {
            'overview': {
                'requests_last_hour': api_metrics_1h.count(),
                'requests_last_24h': api_metrics_24h.count(),
                'avg_response_time_1h': api_metrics_1h.aggregate(avg=models.Avg('value'))['avg'] or 0,
                'avg_response_time_24h': api_metrics_24h.aggregate(avg=models.Avg('value'))['avg'] or 0,
                'error_rate_1h': performance_monitor._calculate_error_rate(api_metrics_1h),
                'error_rate_24h': performance_monitor._calculate_error_rate(api_metrics_24h),
                'active_alerts': active_alerts_count
            },
            'system_resources': system_metrics,
            'latest_health_checks': [
                {
                    'service': h.service_type,
                    'status': h.status,
                    'timestamp': h.timestamp.isoformat(),
                    'response_time': h.response_time_ms
                }
                for h in latest_health
            ],
            'timestamp': timezone.now().isoformat()
        }
        
        return JsonResponse(dashboard_data)
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500) 