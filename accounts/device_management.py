"""
Production-Grade Device Management System for PrimeTrust Banking
"""

import hashlib
import json
import logging
import user_agents
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Q, Count
from django.contrib.gis.geoip2 import GeoIP2
from django.core.exceptions import ValidationError
from accounts.models_security import UserDevice, SecurityEvent
from accounts.utils import generate_secure_token

# Configure logging
logger = logging.getLogger(__name__)

class DeviceManager:
    """Production-grade device management with fingerprinting and trust levels"""
    
    def __init__(self, user):
        self.user = user
        self.geoip = self.get_geoip_instance()
    
    def get_geoip_instance(self):
        """Get GeoIP2 instance for geographic lookups"""
        try:
            return GeoIP2()
        except Exception as e:
            logger.warning(f"GeoIP2 not available: {str(e)}")
            return None
    
    def create_device_fingerprint(self, request) -> Dict[str, Any]:
        """Create comprehensive device fingerprint"""
        
        # Extract basic information
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Parse user agent
        ua_parsed = user_agents.parse(user_agent)
        
        # Create device info
        device_info = {
            'ip_address': ip_address,
            'user_agent': user_agent,
            'browser': {
                'family': ua_parsed.browser.family,
                'version': ua_parsed.browser.version_string,
            },
            'os': {
                'family': ua_parsed.os.family,
                'version': ua_parsed.os.version_string,
            },
            'device': {
                'family': ua_parsed.device.family,
                'brand': ua_parsed.device.brand,
                'model': ua_parsed.device.model,
            },
            'is_mobile': ua_parsed.is_mobile,
            'is_tablet': ua_parsed.is_tablet,
            'is_pc': ua_parsed.is_pc,
            'is_bot': ua_parsed.is_bot,
        }
        
        # Add headers for fingerprinting
        fingerprint_headers = [
            'HTTP_ACCEPT',
            'HTTP_ACCEPT_ENCODING',
            'HTTP_ACCEPT_LANGUAGE',
            'HTTP_DNT',
            'HTTP_UPGRADE_INSECURE_REQUESTS',
            'HTTP_SEC_FETCH_SITE',
            'HTTP_SEC_FETCH_MODE',
            'HTTP_SEC_FETCH_USER',
            'HTTP_SEC_FETCH_DEST',
        ]
        
        headers = {}
        for header in fingerprint_headers:
            if header in request.META:
                headers[header] = request.META[header]
        
        device_info['headers'] = headers
        
        # Add geographic information
        if self.geoip and ip_address != '127.0.0.1':
            try:
                geo_info = self.get_geographic_info(ip_address)
                device_info['geographic'] = geo_info
            except Exception as e:
                logger.warning(f"Geographic lookup failed: {str(e)}")
                device_info['geographic'] = {}
        
        # Create device hash
        device_hash = self.generate_device_hash(device_info)
        device_info['device_hash'] = device_hash
        
        return device_info
    
    def generate_device_hash(self, device_info: Dict[str, Any]) -> str:
        """Generate unique device hash from device information"""
        
        # Core fingerprint components
        fingerprint_data = {
            'browser_family': device_info.get('browser', {}).get('family', ''),
            'browser_version': device_info.get('browser', {}).get('version', ''),
            'os_family': device_info.get('os', {}).get('family', ''),
            'os_version': device_info.get('os', {}).get('version', ''),
            'device_family': device_info.get('device', {}).get('family', ''),
            'is_mobile': device_info.get('is_mobile', False),
            'is_tablet': device_info.get('is_tablet', False),
            'headers': device_info.get('headers', {}),
        }
        
        # Create consistent hash
        fingerprint_json = json.dumps(fingerprint_data, sort_keys=True)
        return hashlib.sha256(fingerprint_json.encode('utf-8')).hexdigest()
    
    def get_geographic_info(self, ip_address: str) -> Dict[str, Any]:
        """Get geographic information for IP address"""
        if not self.geoip:
            return {}
        
        try:
            city = self.geoip.city(ip_address)
            country = self.geoip.country(ip_address)
            
            return {
                'city': city.get('city', ''),
                'region': city.get('region', ''),
                'country': country.get('country_name', ''),
                'country_code': country.get('country_code', ''),
                'postal_code': city.get('postal_code', ''),
                'latitude': float(city.get('latitude', 0)),
                'longitude': float(city.get('longitude', 0)),
                'timezone': city.get('time_zone', ''),
            }
        except Exception as e:
            logger.warning(f"GeoIP lookup failed for {ip_address}: {str(e)}")
            return {}
    
    def register_device(self, request, trust_level: str = 'new') -> UserDevice:
        """Register a new device or update existing one"""
        
        try:
            # Create device fingerprint
            device_info = self.create_device_fingerprint(request)
            device_hash = device_info['device_hash']
            
            # Check if device already exists
            device, created = UserDevice.objects.get_or_create(
                user=self.user,
                browser_fingerprint=device_hash,
                defaults={
                    'device_name': self.generate_device_name(device_info),
                    'device_type': self.detect_device_type(device_info),
                    'ip_address': device_info['ip_address'],
                    'user_agent': device_info['user_agent'],
                    'trust_level': trust_level,
                    'is_active': True,
                }
            )
            
            if not created:
                # Update existing device
                device.last_used = timezone.now()
                device.ip_address = device_info['ip_address']
                device.save()
                
                # Log device activity
                self.log_device_event(device, 'DEVICE_ACCESSED')
            else:
                # Log new device registration
                self.log_device_event(device, 'DEVICE_REGISTERED')
            
            return device
            
        except Exception as e:
            logger.error(f"Error registering device: {str(e)}")
            raise

    def detect_device_type(self, device_info: Dict[str, Any]) -> str:
        """Detect device type from device information"""
        
        # Check if it's mobile or tablet first
        if device_info.get('is_mobile'):
            return 'mobile'
        elif device_info.get('is_tablet'):
            return 'tablet'
        else:
            # Check user agent for more specific detection
            user_agent = device_info.get('user_agent', '').lower()
            
            # Check for mobile indicators
            mobile_indicators = ['mobile', 'android', 'iphone', 'ipod', 'blackberry', 'nokia', 'opera mini']
            if any(indicator in user_agent for indicator in mobile_indicators):
                return 'mobile'
            
            # Check for tablet indicators  
            tablet_indicators = ['tablet', 'ipad', 'kindle', 'playbook', 'silk']
            if any(indicator in user_agent for indicator in tablet_indicators):
                return 'tablet'
            
            # Default to web browser for desktop/laptop
            return 'web'
    
    def generate_device_name(self, device_info: Dict[str, Any]) -> str:
        """Generate human-readable device name"""
        
        browser = device_info.get('browser', {})
        os = device_info.get('os', {})
        device = device_info.get('device', {})
        
        # Create device name components
        parts = []
        
        # Add device type
        if device_info.get('is_mobile'):
            parts.append('Mobile')
        elif device_info.get('is_tablet'):
            parts.append('Tablet')
        else:
            parts.append('Desktop')
        
        # Add browser
        if browser.get('family'):
            parts.append(browser['family'])
        
        # Add OS
        if os.get('family'):
            parts.append(f"on {os['family']}")
        
        # Add device brand/model if available
        if device.get('brand') and device.get('model'):
            parts.append(f"({device['brand']} {device['model']})")
        
        return ' '.join(parts)
    
    def get_device_trust_level(self, device: UserDevice) -> str:
        """Calculate device trust level based on various factors"""
        
        current_time = timezone.now()
        
        # Age of device (how long it's been known)
        age_days = (current_time - device.first_seen).days
        
        # Login frequency
        login_frequency = device.login_count / max(age_days, 1)
        
        # Recent activity
        days_since_last_use = (current_time - device.last_used).days
        
        # Geographic consistency
        geo_consistency = self.check_geographic_consistency(device)
        
        # Security events
        security_events = self.get_device_security_events(device)
        
        # Calculate trust score
        trust_score = 0
        
        # Age factor (older devices are more trusted)
        if age_days >= 30:
            trust_score += 30
        elif age_days >= 7:
            trust_score += 20
        elif age_days >= 1:
            trust_score += 10
        
        # Frequency factor (regularly used devices are more trusted)
        if login_frequency >= 1:  # Daily use
            trust_score += 25
        elif login_frequency >= 0.5:  # Every other day
            trust_score += 15
        elif login_frequency >= 0.1:  # Weekly use
            trust_score += 10
        
        # Recent use factor
        if days_since_last_use <= 1:
            trust_score += 20
        elif days_since_last_use <= 7:
            trust_score += 15
        elif days_since_last_use <= 30:
            trust_score += 10
        
        # Geographic consistency factor
        if geo_consistency:
            trust_score += 15
        
        # Security events factor (negative impact)
        trust_score -= len(security_events) * 5
        
        # Determine trust level
        if trust_score >= 80:
            return 'trusted'
        elif trust_score >= 60:
            return 'recognized'
        elif trust_score >= 40:
            return 'new'
        elif trust_score >= 20:
            return 'suspicious'
        else:
            return 'blocked'
    
    def check_geographic_consistency(self, device: UserDevice) -> bool:
        """Check if device access patterns are geographically consistent"""
        
        try:
            # Get recent security events for this user (not device-specific since SecurityEvent doesn't have device_hash field)
            recent_events = SecurityEvent.objects.filter(
                user=self.user,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).values('ip_address').distinct()
            
            # If we have geographic data, check consistency
            if len(recent_events) > 1:
                countries = set()
                for event in recent_events:
                    if event['ip_address'] and self.geoip:
                        try:
                            country = self.geoip.country(event['ip_address'])
                            countries.add(country.get('country_code', ''))
                        except:
                            pass
                
                # If accessed from multiple countries, it's inconsistent
                return len(countries) <= 1
            
            return True
            
        except Exception as e:
            logger.warning(f"Geographic consistency check failed: {str(e)}")
            return True
    
    def get_device_security_events(self, device: UserDevice) -> List[Dict[str, Any]]:
        """Get security events related to this device"""
        
        try:
            events = SecurityEvent.objects.filter(
                user=self.user,
                risk_level__in=['medium', 'high'],
                created_at__gte=timezone.now() - timedelta(days=30)
            ).order_by('-created_at')
            
            return [
                {
                    'event_type': event.event_type,
                    'risk_level': event.risk_level,
                    'created_at': event.created_at,
                    'description': event.description,
                }
                for event in events[:10]  # Limit to 10 recent events
            ]
            
        except Exception as e:
            logger.warning(f"Error getting device security events: {str(e)}")
            return []
    
    def update_device_trust_level(self, device: UserDevice, new_trust_level: str = None) -> str:
        """Update device trust level"""
        
        try:
            # Calculate trust level if not provided
            if new_trust_level is None:
                new_trust_level = self.get_device_trust_level(device)
            
            # Update if changed
            if device.trust_level != new_trust_level:
                old_trust_level = device.trust_level
                device.trust_level = new_trust_level
                device.save()
                
                # Log trust level change
                self.log_device_event(
                    device,
                    'TRUST_LEVEL_CHANGED',
                    f"Changed from {old_trust_level} to {new_trust_level}"
                )
            
            return new_trust_level
            
        except Exception as e:
            logger.error(f"Error updating device trust level: {str(e)}")
            return device.trust_level
    
    def revoke_device(self, device_id: int) -> bool:
        """Revoke access for a specific device"""
        
        try:
            device = UserDevice.objects.get(id=device_id, user=self.user)
            device.is_active = False
            device.trust_level = 'blocked'
            device.save()
            
            # Log device revocation
            self.log_device_event(device, 'DEVICE_REVOKED')
            
            return True
            
        except UserDevice.DoesNotExist:
            logger.warning(f"Device {device_id} not found for user {self.user.id}")
            return False
        except Exception as e:
            logger.error(f"Error revoking device: {str(e)}")
            return False
    
    def get_user_devices(self) -> List[Dict[str, Any]]:
        """Get all devices for the user"""
        
        try:
            devices = UserDevice.objects.filter(user=self.user).order_by('-last_used')
            
            device_list = []
            for device in devices:
                # Update trust level
                current_trust_level = self.update_device_trust_level(device)
                
                device_data = {
                    'id': device.id,
                    'device_name': device.device_name,
                    'trust_level': current_trust_level,
                    'first_seen': device.first_seen,
                    'last_used': device.last_used,
                    'is_active': device.is_active,
                    'ip_address': device.ip_address,
                    'location': self.get_device_location(device),
                    'is_current': self.is_current_device(device),
                    'security_events': len(self.get_device_security_events(device)),
                }
                
                device_list.append(device_data)
            
            return device_list
            
        except Exception as e:
            logger.error(f"Error getting user devices: {str(e)}")
            return []
    
    def get_device_location(self, device: UserDevice) -> str:
        """Get device location string"""
        
        try:
            if device.ip_address and self.geoip:
                geo_info = self.get_geographic_info(device.ip_address)
                
                parts = []
                if geo_info.get('city'):
                    parts.append(geo_info['city'])
                if geo_info.get('region'):
                    parts.append(geo_info['region'])
                if geo_info.get('country'):
                    parts.append(geo_info['country'])
                
                return ', '.join(parts) if parts else 'Unknown'
            
            return 'Unknown'
            
        except Exception as e:
            logger.warning(f"Error getting device location: {str(e)}")
            return 'Unknown'
    
    def is_current_device(self, device: UserDevice) -> bool:
        """Check if this is the current device"""
        
        # This would need to be implemented based on the current request
        # For now, we'll check if it was used recently
        return (timezone.now() - device.last_used).seconds < 300  # 5 minutes
    
    def log_device_event(self, device: UserDevice, event_type: str, details: str = None):
        """Log device-related security event"""
        
        try:
            SecurityEvent.objects.create(
                user=self.user,
                event_type=event_type,
                risk_level='low',
                description=details or "",
                ip_address=device.ip_address,
                user_agent=device.user_agent,
            )
            
        except Exception as e:
            logger.error(f"Error logging device event: {str(e)}")
    
    def get_client_ip(self, request) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or '127.0.0.1'
    
    def cleanup_old_devices(self, days: int = 90):
        """Clean up old inactive devices"""
        
        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            
            old_devices = UserDevice.objects.filter(
                user=self.user,
                last_used__lt=cutoff_date,
                is_active=True
            )
            
            count = old_devices.count()
            old_devices.update(is_active=False)
            
            logger.info(f"Cleaned up {count} old devices for user {self.user.id}")
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up old devices: {str(e)}")
            return 0


def is_device_trusted(user, device_hash: str) -> bool:
    """Check if a device is trusted"""
    
    try:
        device = UserDevice.objects.get(
            user=user,
            browser_fingerprint=device_hash,
            is_active=True
        )
        
        return device.trust_level in ['trusted', 'recognized']
        
    except UserDevice.DoesNotExist:
        return False
    except Exception as e:
        logger.error(f"Error checking device trust: {str(e)}")
        return False


def get_device_risk_score(user, device_hash: str) -> int:
    """Get risk score for a device (0-100, higher is riskier)"""
    
    try:
        device = UserDevice.objects.get(
            user=user,
            browser_fingerprint=device_hash,
            is_active=True
        )
        
        device_manager = DeviceManager(user)
        trust_level = device_manager.get_device_trust_level(device)
        
        # Convert trust level to risk score
        risk_mapping = {
            'trusted': 10,
            'recognized': 25,
            'new': 50,
            'suspicious': 80,
            'blocked': 100,
        }
        
        return risk_mapping.get(trust_level, 50)
        
    except UserDevice.DoesNotExist:
        return 75  # New device is moderately risky
    except Exception as e:
        logger.error(f"Error getting device risk score: {str(e)}")
        return 50 