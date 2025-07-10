"""
Production-Grade Authentication Views for PrimeTrust Banking API
"""

from rest_framework import status, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_post_parameters
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from accounts.models import CustomUser
from accounts.utils import (
    generate_verification_code, 
    send_verification_email, 
    TwoFactorAuth,
    is_suspicious_login,
    is_rate_limited,
    hash_device_fingerprint,
    generate_secure_token
)
from accounts.device_management import DeviceManager
from .serializers import (
    UserSerializer, 
    UserDetailSerializer, 
    PasswordChangeSerializer,
    UserProfileSerializer
)

# Configure logging
logger = logging.getLogger(__name__)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with enhanced security"""
    
    def validate(self, attrs):
        # Extract email and password
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError("Email and password are required")
        
        # Authenticate user
        user = authenticate(request=self.context.get('request'), email=email, password=password)
        
        if not user:
            logger.warning(f"Authentication failed for email: {email}")
            raise serializers.ValidationError("Invalid email or password")
        
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")
        
        # Get tokens
        refresh = RefreshToken.for_user(user)
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }

class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token view with production security features"""
    serializer_class = CustomTokenObtainPairSerializer
    
    @method_decorator(sensitive_post_parameters('password'))
    @method_decorator(never_cache)
    def post(self, request, *args, **kwargs):
        """Enhanced login with security checks"""
        
        # Get client information
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Extract credentials
        email = request.data.get('email')
        password = request.data.get('password')
        totp_token = request.data.get('totp_token')
        backup_code = request.data.get('backup_code')
        
        try:
            # Rate limiting check
            if is_rate_limited(0, f"login_attempt_{ip_address}", limit=5, window=900):  # 15 minutes
                return Response({
                    'error': 'Too many login attempts. Please try again later.',
                    'detail': 'Rate limit exceeded'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # Get user
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                self.log_security_event(None, 'LOGIN_FAILED', ip_address, user_agent, 'User not found')
                return Response({
                    'error': 'Invalid email or password'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Check if account is locked
            two_fa = TwoFactorAuth(user)
            if two_fa.security_settings.account_locked:
                self.log_security_event(user, 'LOGIN_BLOCKED', ip_address, user_agent, 'Account locked')
                return Response({
                    'error': 'Account is locked due to security reasons'
                }, status=status.HTTP_423_LOCKED)
            
            # Verify password
            if not check_password(password, user.password):
                self.handle_failed_login(user, ip_address, user_agent)
                return Response({
                    'error': 'Invalid email or password'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Check for suspicious login
            if is_suspicious_login(user, ip_address, user_agent):
                self.log_security_event(user, 'SUSPICIOUS_LOGIN', ip_address, user_agent)
                return Response({
                    'error': 'Suspicious login detected. Please verify your identity.',
                    'requires_verification': True
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Check if 2FA is enabled
            if two_fa.security_settings.two_factor_enabled:
                return self.handle_2fa_login(user, totp_token, backup_code, ip_address, user_agent)
            
            # Generate tokens for successful login
            tokens = self.generate_tokens(user)
            
            # Log successful login
            self.log_security_event(user, 'LOGIN_SUCCESS', ip_address, user_agent)
            
            # Update device information
            self.update_device_info(user, ip_address, user_agent)
            
            # Reset failed attempts
            two_fa.security_settings.failed_login_attempts = 0
            two_fa.security_settings.save()
            
            return Response({
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'user': UserSerializer(user).data,
                'requires_2fa': False
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response({
                'error': 'Login failed due to server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def handle_2fa_login(self, user, totp_token, backup_code, ip_address, user_agent):
        """Handle 2FA verification"""
        two_fa = TwoFactorAuth(user)
        
        # Check if 2FA token or backup code provided
        if not totp_token and not backup_code:
            return Response({
                'requires_2fa': True,
                'backup_codes_available': two_fa.get_backup_codes_status()['remaining'] > 0
            }, status=status.HTTP_200_OK)
        
        # Verify 2FA
        if totp_token:
            if two_fa.verify_totp(totp_token):
                return self.complete_2fa_login(user, ip_address, user_agent)
            else:
                return Response({
                    'error': 'Invalid 2FA token',
                    'requires_2fa': True
                }, status=status.HTTP_401_UNAUTHORIZED)
        
        elif backup_code:
            if two_fa.verify_backup_code(backup_code, request=None):
                return self.complete_2fa_login(user, ip_address, user_agent)
            else:
                return Response({
                    'error': 'Invalid backup code',
                    'requires_2fa': True
                }, status=status.HTTP_401_UNAUTHORIZED)
    
    def complete_2fa_login(self, user, ip_address, user_agent):
        """Complete login after successful 2FA"""
        tokens = self.generate_tokens(user)
        
        # Log successful 2FA login
        self.log_security_event(user, 'LOGIN_2FA_SUCCESS', ip_address, user_agent)
        
        # Update device information
        self.update_device_info(user, ip_address, user_agent)
        
        return Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'user': UserSerializer(user).data,
            'requires_2fa': False
        }, status=status.HTTP_200_OK)
    
    def handle_failed_login(self, user, ip_address, user_agent):
        """Handle failed login attempt"""
        two_fa = TwoFactorAuth(user)
        
        # Increment failed attempts
        two_fa.security_settings.failed_login_attempts += 1
        two_fa.security_settings.last_failed_login = timezone.now()
        
        # Lock account after 5 failed attempts
        if two_fa.security_settings.failed_login_attempts >= 5:
            two_fa.security_settings.account_locked = True
            two_fa.security_settings.save()
            
            # Log security event
            self.log_security_event(user, 'ACCOUNT_LOCKED', ip_address, user_agent, 'Too many failed attempts')
            
            # Send account locked notification email
            try:
                from banking.utils import send_account_locked_notification
                
                # Create unlock URL (can be customized)
                unlock_url = f"{getattr(settings, 'SITE_URL', 'https://primetrust.com')}/accounts/unlock"
                
                activity_details = {
                    'failed_attempts': two_fa.security_settings.failed_login_attempts,
                    'last_attempt_ip': ip_address,
                    'last_attempt_time': timezone.now().isoformat(),
                    'user_agent': user_agent
                }
                
                send_account_locked_notification(
                    user=user,
                    lock_reason='Too many failed login attempts',
                    activity_details=activity_details,
                    unlock_url=unlock_url
                )
                
            except Exception as email_error:
                # Don't break security flow if email fails
                logger.error(f"Failed to send account locked notification to {user.email}: {str(email_error)}")
        else:
            two_fa.security_settings.save()
            
        self.log_security_event(user, 'LOGIN_FAILED', ip_address, user_agent)
    
    def generate_tokens(self, user):
        """Generate JWT tokens"""
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }
    
    def update_device_info(self, user, ip_address, user_agent):
        """Update or create device information"""
        try:
            from accounts.models_security import UserDevice
            
            device_hash = hash_device_fingerprint(user_agent, ip_address)
            
            device, created = UserDevice.objects.get_or_create(
                user=user,
                device_hash=device_hash,
                defaults={
                    'device_name': self.extract_device_name(user_agent),
                    'device_type': self.detect_device_type(user_agent),
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'trust_level': 'new',
                    'first_seen': timezone.now(),
                    'last_seen': timezone.now(),
                    'is_active': True
                }
            )
            
            if not created:
                device.last_seen = timezone.now()
                device.ip_address = ip_address
                device.login_count += 1
                device.save()
                
        except Exception as e:
            logger.error(f"Error updating device info: {str(e)}")

    def detect_device_type(self, user_agent):
        """Detect device type from user agent"""
        user_agent_lower = user_agent.lower()
        
        # Check for mobile indicators
        mobile_indicators = ['mobile', 'android', 'iphone', 'ipod', 'blackberry', 'nokia', 'opera mini']
        if any(indicator in user_agent_lower for indicator in mobile_indicators):
            return 'mobile'
        
        # Check for tablet indicators  
        tablet_indicators = ['tablet', 'ipad', 'kindle', 'playbook', 'silk']
        if any(indicator in user_agent_lower for indicator in tablet_indicators):
            return 'tablet'
        
        # Check if it's likely an API client
        api_indicators = ['curl', 'wget', 'python', 'postman', 'insomnia', 'httpie']
        if any(indicator in user_agent_lower for indicator in api_indicators):
            return 'api'
        
        # Default to web browser for desktop/laptop
        return 'web'
    
    def extract_device_name(self, user_agent):
        """Extract device name from user agent"""
        if 'Mobile' in user_agent:
            return 'Mobile Device'
        elif 'Tablet' in user_agent:
            return 'Tablet'
        else:
            return 'Desktop'
    
    def log_security_event(self, user, event_type, ip_address, user_agent, details=None):
        """Log security event and send alert email for significant events"""
        try:
            from accounts.models_security import SecurityEvent
            
            # Determine severity based on event type
            severity = 'info' if 'SUCCESS' in event_type else 'warning'
            if event_type in ['ACCOUNT_LOCKED', 'SUSPICIOUS_LOGIN']:
                severity = 'critical'
            
            SecurityEvent.objects.create(
                user=user,
                event_type=event_type,
                severity=severity,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or "",
                timestamp=timezone.now()
            )
            
            # Send security alert emails for significant events
            security_alert_events = [
                'LOGIN_FAILED', 'ACCOUNT_LOCKED', 'SUSPICIOUS_LOGIN',
                'PASSWORD_CHANGED', 'DEVICE_REGISTERED'
            ]
            
            if event_type in security_alert_events or severity in ['warning', 'critical']:
                try:
                    from banking.utils import send_security_alert
                    
                    # Create alert details
                    alert_details = {
                        'event_type': event_type,
                        'severity': severity,
                        'description': details or f"Security event: {event_type}",
                        'timestamp': timezone.now().isoformat(),
                        'user_id': user.id,
                        'ip_address': ip_address,
                        'user_agent': user_agent
                    }
                    
                    # Send security alert email
                    send_security_alert(user, event_type, alert_details)
                    
                except Exception as email_error:
                    # Don't break security logging if email fails
                    logger.error(f"Failed to send security alert email for {event_type}: {str(email_error)}")
            
            # Trigger webhook events for security events
            security_webhook_events = [
                'ACCOUNT_LOCKED', 'PASSWORD_CHANGED', 'SUSPICIOUS_LOGIN',
                'DEVICE_REGISTERED', 'LOGIN_SUCCESS', 'LOGIN_2FA_SUCCESS'
            ]
            
            if event_type in security_webhook_events:
                try:
                    from api.webhook_delivery import trigger_security_event
                    
                    security_details = {
                        'event_type': event_type,
                        'severity': severity,
                        'description': details or f"Security event: {event_type}",
                        'timestamp': timezone.now().isoformat(),
                        'ip_address': ip_address,
                        'user_agent': user_agent
                    }
                    
                    trigger_security_event(user, f"security.{event_type.lower()}", security_details)
                    
                except Exception as webhook_error:
                    # Don't break security logging if webhook fails
                    logger.error(f"Failed to trigger security webhook for {event_type}: {str(webhook_error)}")
            
        except Exception as e:
            logger.error(f"Error logging security event: {str(e)}")
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or '127.0.0.1'

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_api(request):
    """Logout API endpoint"""
    try:
        # Get refresh token
        refresh_token = request.data.get('refresh_token')
        
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        # Log logout
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        from accounts.models_security import SecurityEvent
        SecurityEvent.objects.create(
            user=request.user,
            event_type='LOGOUT',
            severity='info',
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=timezone.now()
        )
        
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response({'error': 'Logout failed'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profile_api(request):
    """Get user profile"""
    try:
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Profile error: {str(e)}")
        return Response({'error': 'Failed to get profile'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_profile_api(request):
    """Update user profile"""
    try:
        serializer = UserProfileSerializer(request.user.profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        return Response({'error': 'Failed to update profile'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password_api(request):
    """Change user password"""
    try:
        serializer = PasswordChangeSerializer(data=request.data)
        
        if serializer.is_valid():
            # Verify current password
            current_password = serializer.validated_data['current_password']
            
            if not check_password(current_password, request.user.password):
                return Response({
                    'error': 'Current password is incorrect'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Set new password
            new_password = serializer.validated_data['new_password']
            request.user.set_password(new_password)
            request.user.save()
            
            # Update security settings
            two_fa = TwoFactorAuth(request.user)
            two_fa.security_settings.password_last_changed = timezone.now()
            two_fa.security_settings.save()
            
            # Log password change
            two_fa.log_security_event('PASSWORD_CHANGED', 'info')
            
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return Response({'error': 'Failed to change password'}, status=status.HTTP_400_BAD_REQUEST)

# 2FA Management Endpoints

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def enable_2fa_api(request):
    """Enable 2FA for user"""
    try:
        two_fa = TwoFactorAuth(request.user)
        
        if two_fa.security_settings.two_factor_enabled:
            return Response({
                'error': '2FA is already enabled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate secret and QR code
        secret_key, qr_code_url = two_fa.enable_2fa()
        qr_code_image = two_fa.generate_qr_code(qr_code_url)
        
        return Response({
            'secret_key': secret_key,
            'qr_code_url': qr_code_url,
            'qr_code_image': qr_code_image,
            'backup_codes_required': True
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Enable 2FA error: {str(e)}")
        return Response({'error': 'Failed to enable 2FA'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def disable_2fa_api(request):
    """Disable 2FA for user"""
    try:
        two_fa = TwoFactorAuth(request.user)
        
        if not two_fa.security_settings.two_factor_enabled:
            return Response({
                'error': '2FA is not enabled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify password or 2FA token
        password = request.data.get('password')
        totp_token = request.data.get('totp_token')
        
        if password:
            if not check_password(password, request.user.password):
                return Response({
                    'error': 'Invalid password'
                }, status=status.HTTP_400_BAD_REQUEST)
        elif totp_token:
            if not two_fa.verify_totp(totp_token):
                return Response({
                    'error': 'Invalid 2FA token'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({
                'error': 'Password or 2FA token required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Disable 2FA
        two_fa.disable_2fa()
        
        return Response({
            'message': '2FA disabled successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Disable 2FA error: {str(e)}")
        return Response({'error': 'Failed to disable 2FA'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_backup_codes_api(request):
    """Generate backup codes"""
    try:
        two_fa = TwoFactorAuth(request.user)
        
        if not two_fa.security_settings.two_factor_enabled:
            return Response({
                'error': '2FA must be enabled first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate backup codes
        backup_codes = two_fa.generate_backup_codes()
        
        return Response({
            'backup_codes': backup_codes,
            'message': 'Store these codes securely. They can only be used once.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Generate backup codes error: {str(e)}")
        return Response({'error': 'Failed to generate backup codes'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_2fa_status_api(request):
    """Get 2FA status"""
    try:
        two_fa = TwoFactorAuth(request.user)
        status_data = two_fa.get_2fa_status()
        
        return Response(status_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Get 2FA status error: {str(e)}")
        return Response({'error': 'Failed to get 2FA status'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_2fa_api(request):
    """Verify 2FA token"""
    try:
        two_fa = TwoFactorAuth(request.user)
        token = request.data.get('token')
        
        if not token:
            return Response({
                'error': 'Token is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        is_valid = two_fa.verify_totp(token)
        
        return Response({
            'valid': is_valid,
            'message': 'Token verified successfully' if is_valid else 'Invalid token'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Verify 2FA error: {str(e)}")
        return Response({'error': 'Failed to verify 2FA'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resend_login_code_api(request):
    """Resend login verification code"""
    try:
        # Generate new verification code
        code = generate_verification_code()
        
        # Store in cache for 10 minutes
        cache_key = f"login_code_{request.user.id}"
        cache.set(cache_key, code, 600)
        
        # Send email
        send_verification_email(request.user, code)
        
        return Response({
            'message': 'Verification code sent successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Resend login code error: {str(e)}")
        return Response({'error': 'Failed to send verification code'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def verify_login_api(request):
    """Verify login with code"""
    try:
        code = request.data.get('code')
        
        if not code:
            return Response({
                'error': 'Verification code is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check cached code
        cache_key = f"login_code_{request.user.id}"
        cached_code = cache.get(cache_key)
        
        if not cached_code or cached_code != code:
            return Response({
                'error': 'Invalid or expired verification code'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Clear the code
        cache.delete(cache_key)
        
        # Log successful verification
        two_fa = TwoFactorAuth(request.user)
        two_fa.log_security_event('LOGIN_VERIFIED', 'success')
        
        return Response({
            'message': 'Login verified successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Verify login error: {str(e)}")
        return Response({'error': 'Failed to verify login'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_devices_api(request):
    """Get user's devices"""
    try:
        device_manager = DeviceManager(request.user)
        devices = device_manager.get_user_devices()
        
        return Response({
            'devices': devices,
            'total': len(devices)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Get user devices error: {str(e)}")
        return Response({'error': 'Failed to get devices'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def revoke_device_api(request):
    """Revoke a device"""
    try:
        device_id = request.data.get('device_id')
        
        if not device_id:
            return Response({
                'error': 'Device ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        device_manager = DeviceManager(request.user)
        success = device_manager.revoke_device(device_id)
        
        if success:
            return Response({
                'message': 'Device revoked successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Failed to revoke device'
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Revoke device error: {str(e)}")
        return Response({'error': 'Failed to revoke device'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def security_summary_api(request):
    """Get security summary"""
    try:
        two_fa = TwoFactorAuth(request.user)
        device_manager = DeviceManager(request.user)
        
        # Get 2FA status
        fa_status = two_fa.get_2fa_status()
        
        # Get device count
        devices = device_manager.get_user_devices()
        active_devices = [d for d in devices if d['is_active']]
        
        # Get recent security events
        from accounts.models_security import SecurityEvent
        recent_events = SecurityEvent.objects.filter(
            user=request.user,
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).order_by('-timestamp')[:10]
        
        events_data = [
            {
                'event_type': event.event_type,
                'severity': event.severity,
                'timestamp': event.timestamp,
                'details': event.details,
                'ip_address': event.ip_address
            }
            for event in recent_events
        ]
        
        # Calculate security score
        security_score = two_fa.security_settings.security_score
        
        return Response({
            'security_score': security_score,
            'two_factor_enabled': fa_status['enabled'],
            'active_devices': len(active_devices),
            'total_devices': len(devices),
            'recent_events': events_data,
            'account_locked': two_fa.security_settings.account_locked,
            'password_last_changed': two_fa.security_settings.password_last_changed,
            'recommendations': get_security_recommendations(request.user)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Security summary error: {str(e)}")
        return Response({'error': 'Failed to get security summary'}, status=status.HTTP_400_BAD_REQUEST)

def get_security_recommendations(user):
    """Get security recommendations for user"""
    recommendations = []
    
    try:
        two_fa = TwoFactorAuth(user)
        
        # Check 2FA
        if not two_fa.security_settings.two_factor_enabled:
            recommendations.append({
                'type': 'enable_2fa',
                'priority': 'high',
                'title': 'Enable Two-Factor Authentication',
                'description': 'Secure your account with 2FA for better protection.'
            })
        
        # Check password age
        if two_fa.security_settings.password_last_changed:
            password_age = (timezone.now() - two_fa.security_settings.password_last_changed).days
            if password_age > 90:
                recommendations.append({
                    'type': 'change_password',
                    'priority': 'medium',
                    'title': 'Change Your Password',
                    'description': f'Your password is {password_age} days old. Consider changing it.'
                })
        
        # Check device count
        device_manager = DeviceManager(user)
        devices = device_manager.get_user_devices()
        active_devices = [d for d in devices if d['is_active']]
        
        if len(active_devices) > 10:
            recommendations.append({
                'type': 'cleanup_devices',
                'priority': 'low',
                'title': 'Clean Up Old Devices',
                'description': f'You have {len(active_devices)} active devices. Consider removing unused ones.'
            })
        
        # Check security score
        if two_fa.security_settings.security_score < 60:
            recommendations.append({
                'type': 'improve_security',
                'priority': 'high',
                'title': 'Improve Security Score',
                'description': 'Your security score is low. Follow security best practices.'
            })
        
    except Exception as e:
        logger.error(f"Error getting security recommendations: {str(e)}")
    
    return recommendations

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or '127.0.0.1' 