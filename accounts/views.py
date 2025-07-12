from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django_htmx.http import trigger_client_event, HttpResponseClientRedirect
from datetime import datetime
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json


from .models import CustomUser, UserProfile
from .forms import (
    CustomUserCreationForm,
    ProfileUpdateForm,
    TransactionPinForm,
    VerificationForm,
    LoginForm,
    PasswordChangeForm,
    TransactionPINChangeForm,
    TransactionPINSetupForm
)
from .utils import (
    generate_verification_code, 
    send_verification_email, 
    verify_code,
    TwoFactorAuth,
    is_rate_limited
)
from .device_management import DeviceManager
from .audit_logging import AuditLogger
# Import email functions and webhook triggers
from banking.utils import send_welcome_email
from api.webhook_delivery import trigger_user_created
import logging
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.forms import SetPasswordForm
from .utils import send_password_reset_email

logger = logging.getLogger(__name__)

def register_view(request):
    """Enhanced registration with mandatory 2FA - Step 1: Basic Info"""
    
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create user but don't activate yet
                    user = form.save(commit=False)
                    user.is_active = False  # Will be activated after 2FA setup
                    user.save()
                    
                    # Create user profile
                    UserProfile.objects.get_or_create(user=user)
                    
                    # Send verification email
                    verification_code = generate_verification_code()
                    cache.set(f"email_verification_{user.id}", verification_code, 3600)  # 1 hour
                    send_verification_email(user, verification_code)
                    
                    # Log registration attempt
                    audit_logger = AuditLogger(user=user, request=request)
                    audit_logger.log_administrative_action(
                        'USER_REGISTRATION_STARTED',
                        changes={'email': user.email, 'step': '1_basic_info'}
                    )
                    
                    # Store user ID in session for next steps
                    request.session['registration_user_id'] = user.id
                    request.session['registration_step'] = 'email_verification'
                    
                    messages.success(request, 'Registration started! Please check your email to verify your account.')
                    return redirect('accounts:verify_email')
                    
            except Exception as e:
                messages.error(request, 'Registration failed. Please try again.')
        else:
            # Form validation errors
            messages.error(request, 'Please correct the errors below.')
                
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def verify_email_view(request):
    """Step 2: Email Verification"""
    
    user_id = request.session.get('registration_user_id')
    if not user_id:
        messages.error(request, 'Invalid registration session.')
        return redirect('accounts:register')
    
    try:
        user = CustomUser.objects.get(id=user_id, is_active=False)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Invalid registration session.')
        return redirect('accounts:register')
    
    if request.method == 'POST':
        verification_code = request.POST.get('verification_code')
        cached_code = cache.get(f"email_verification_{user.id}")
        
        if cached_code and cached_code == verification_code:
            # Clear verification code
            cache.delete(f"email_verification_{user.id}")
            
            # Update registration step
            request.session['registration_step'] = 'security_setup'
            
            # Log email verification
            audit_logger = AuditLogger(user=user, request=request)
            audit_logger.log_administrative_action(
                'EMAIL_VERIFIED',
                changes={'step': '2_email_verification'}
            )
            
            messages.success(request, 'Email verified successfully!')
            
            # Handle HTMX redirect
            if request.headers.get('HX-Request'):
                response = HttpResponse()
                response['HX-Redirect'] = '/accounts/setup-2fa/'
                return response
            else:
                return redirect('accounts:setup_2fa')
        else:
            messages.error(request, 'Invalid or expired verification code.')
    
    return render(request, 'accounts/verify_email.html', {'user': user})

def setup_2fa_view(request):
    """Step 3: Mandatory 2FA Setup"""
    
    user_id = request.session.get('registration_user_id')
    registration_step = request.session.get('registration_step')
    
    # Allow both security_setup and 2fa_verification steps
    if not user_id or registration_step not in ['security_setup', '2fa_verification']:
        messages.error(request, 'Invalid registration session.')
        return redirect('accounts:register')
    
    try:
        user = CustomUser.objects.get(id=user_id, is_active=False)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Invalid registration session.')
        return redirect('accounts:register')
    
    # Initialize 2FA
    two_fa = TwoFactorAuth(user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'enable_2fa':
            try:
                # Enable 2FA and get QR code
                secret_key, qr_code_url = two_fa.enable_2fa()
                qr_code_image = two_fa.generate_qr_code(qr_code_url)
                
                # Store in session for verification
                request.session['2fa_secret'] = secret_key
                request.session['registration_step'] = '2fa_verification'
                
                return JsonResponse({
                    'success': True,
                    'qr_code_image': qr_code_image,
                    'secret_key': secret_key,
                    'backup_instructions': 'Please scan this QR code with your authenticator app.'
                })
                
            except Exception as e:
                return JsonResponse({'success': False, 'error': 'Failed to setup 2FA'})
        
        elif action == 'verify_2fa':
            try:
                totp_token = request.POST.get('totp_token')
                
                if two_fa.verify_totp(totp_token):
                    # Generate secure backup codes
                    backup_codes = two_fa.generate_backup_codes(count=5)  # Generate 5 secure codes
                    
                    # Update session for next step
                    request.session['registration_step'] = 'backup_codes'
                    request.session['backup_codes'] = backup_codes  # Now using secure codes
                    
                    return JsonResponse({
                        'success': True,
                        'message': '2FA verified successfully!'
                    })
                else:
                    return JsonResponse({
                        'success': False, 
                        'error': 'Invalid 2FA token. Please try again.'
                    })
            except Exception as e:
                messages.error(request, f'Verification failed: {str(e)}')
                return JsonResponse({
                    'success': False, 
                    'error': f'Verification failed: {str(e)}'
                })
    
    return render(request, 'accounts/setup_2fa.html', {'user': user})

def backup_codes_view(request):
    """Step 4: Backup Codes Download"""
    
    user_id = request.session.get('registration_user_id')
    registration_step = request.session.get('registration_step')
    backup_codes = request.session.get('backup_codes')
    
    if not all([user_id, registration_step == 'backup_codes', backup_codes]):
        messages.error(request, 'Invalid registration session.')
        return redirect('accounts:register')
    
    try:
        user = CustomUser.objects.get(id=user_id, is_active=False)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Invalid registration session.')
        return redirect('accounts:register')
    
    if request.method == 'POST':
        codes_confirmed = request.POST.get('codes_confirmed')
        
        if codes_confirmed == 'true':
            # Clear backup codes from session
            del request.session['backup_codes']
            request.session['registration_step'] = 'transaction_pin'
            
            messages.success(request, 'Backup codes saved! Now set up your transaction PIN.')
            return redirect('accounts:setup_pin')
    
    return render(request, 'accounts/backup_codes.html', {
        'user': user,
        'backup_codes': backup_codes
    })

def setup_pin_view(request):
    """Step 5: Transaction PIN Setup"""
    
    user_id = request.session.get('registration_user_id')
    registration_step = request.session.get('registration_step')
    
    if not user_id or registration_step != 'transaction_pin':
        messages.error(request, 'Invalid registration session.')
        return redirect('accounts:register')
    
    try:
        user = CustomUser.objects.get(id=user_id, is_active=False)
    except CustomUser.DoesNotExist:
        messages.error(request, 'Invalid registration session.')
        return redirect('accounts:register')
    
    if request.method == 'POST':
        form = TransactionPinForm(request.POST)
        if form.is_valid():
            try:
                # Set transaction PIN
                pin = form.cleaned_data['pin']
                user.profile.set_transaction_pin(pin)
                
                # Complete registration
                user.is_active = True
                user.save()
                
                # Note: Bank account will be created automatically by signal in banking/signals.py
                
                # Register device
                device_manager = DeviceManager(user)
                device_manager.register_device(request, trust_level='trusted')
                
                # Send welcome email
                try:
                    send_welcome_email(user)
                except Exception as e:
                    # Don't break registration if email fails
                    logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
                
                # Trigger webhook event
                try:
                    trigger_user_created(user)
                except Exception as e:
                    # Don't break registration if webhook fails
                    logger.error(f"Failed to trigger user_created webhook for {user.email}: {str(e)}")
                
                # Log registration completion
                audit_logger = AuditLogger(user=user, request=request)
                audit_logger.log_administrative_action(
                    'USER_REGISTRATION_COMPLETED',
                    changes={
                        'email': user.email,
                        'has_2fa': True,
                        'has_transaction_pin': True,
                        'accounts_created': 1  # Now only 1 account via signal
                    }
                )
                
                # Clean up session
                del request.session['registration_user_id']
                del request.session['registration_step']
                if '2fa_secret' in request.session:
                    del request.session['2fa_secret']
                
                # Auto-login user (specify backend to avoid multi-backend error)
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                
                messages.success(request, 'Registration completed successfully! Welcome to PrimeTrust.')
                return redirect('dashboard:home')
                
            except Exception as e:
                messages.error(request, 'Failed to set up transaction PIN. Please try again.')
    else:
        form = TransactionPinForm()
    
    return render(request, 'accounts/setup_pin.html', {'form': form, 'user': user})

def login_view(request):
    """API-based login with 2FA support"""
    
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    # For GET requests or when JavaScript is disabled, just serve the login page
    # All authentication logic is handled by JavaScript via API calls
    return render(request, 'accounts/login.html')

@require_POST
@csrf_exempt
def establish_session_view(request):
    """Establish Django session after successful API authentication"""
    
    try:
        import json
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        
        data = json.loads(request.body)
        access_token = data.get('access_token')
        
        if not access_token:
            return JsonResponse({'success': False, 'error': 'No access token provided'})
        
        # Verify the token and get user
        try:
            token = AccessToken(access_token)
            user_id = token['user_id']
            user = CustomUser.objects.get(id=user_id)
            
            # Establish Django session
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
            return JsonResponse({
                'success': True,
                'redirect_url': reverse('dashboard:home')
            })
            
        except (InvalidToken, TokenError, CustomUser.DoesNotExist) as e:
            return JsonResponse({'success': False, 'error': 'Invalid token'})
            
    except Exception as e:
        logger.error(f"Session establishment error: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Session establishment failed'})

@login_required
def profile_view(request):
    """User profile view with security information"""
    two_fa = TwoFactorAuth(request.user)
    device_manager = DeviceManager(request.user)
    security_info = {
        '2fa_status': two_fa.get_2fa_status(),
        'devices': device_manager.get_user_devices()[:5],
        'security_score': two_fa.security_settings.security_score,
        'account_locked': two_fa.security_settings.is_account_locked()
    }

    from .forms import UserProfileUpdateForm
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        user_form = ProfileUpdateForm(request.POST, instance=user)
        profile_form = UserProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            audit_logger = AuditLogger(user=user, request=request)
            audit_logger.log_administrative_action(
                'PROFILE_UPDATED',
                changes={'fields_changed': list(user_form.changed_data) + list(profile_form.changed_data)}
            )
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        user_form = ProfileUpdateForm(instance=user)
        profile_form = UserProfileUpdateForm(instance=profile)

    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'security_info': security_info
    })

def logout_view(request):
    """Enhanced logout with audit logging"""
    
    if request.user.is_authenticated:
        # Log logout
        audit_logger = AuditLogger(user=request.user, request=request)
        audit_logger.log_event('LOGOUT', 'info', 'User logged out')
        
        user_name = request.user.first_name
        logout(request)
        messages.success(request, f'Goodbye, {user_name}! You have been logged out securely.')
    
    return redirect('home')

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip or '127.0.0.1'

# AJAX endpoints for enhanced UX
@require_POST
@csrf_exempt
def resend_verification_code(request):
    """Resend email verification code"""
    
    user_id = request.session.get('registration_user_id')
    if not user_id:
        return JsonResponse({'success': False, 'error': 'Invalid session'})
    
    try:
        user = CustomUser.objects.get(id=user_id, is_active=False)
        
        # Generate new code
        verification_code = generate_verification_code()
        cache.set(f"email_verification_{user.id}", verification_code, 3600)
        send_verification_email(user, verification_code)
        
        return JsonResponse({'success': True, 'message': 'Verification code sent!'})
        
    except Exception as e:
        messages.error(request, 'Failed to send code')
        return JsonResponse({'success': False, 'error': 'Failed to send code'})

@require_POST
@csrf_exempt  
def check_2fa_token(request):
    """Check 2FA token during setup"""
    
    user_id = request.session.get('registration_user_id')
    if not user_id:
        return JsonResponse({'success': False, 'error': 'Invalid session'})
    
    try:
        user = CustomUser.objects.get(id=user_id)
        token = request.POST.get('token')
        
        two_fa = TwoFactorAuth(user)
        is_valid = two_fa.verify_totp(token)
        
        return JsonResponse({'success': is_valid})
        
    except Exception as e:
        messages.error(request, 'Verification failed')
        return JsonResponse({'success': False, 'error': 'Verification failed'})

@login_required
def change_password(request):
    """Change password view"""
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = request.user
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            
            # Log password change
            audit_logger = AuditLogger(user=user, request=request)
            audit_logger.log_security_event(
                'PASSWORD_CHANGED',
                'User changed their password',
                risk_level='low'
            )
            
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:login')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

@login_required
def change_transaction_pin(request):
    """Change transaction PIN view"""
    
    if request.method == 'POST':
        form = TransactionPINChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            
            # Log PIN change
            audit_logger = AuditLogger(user=request.user, request=request)
            audit_logger.log_security_event(
                'TRANSACTION_PIN_CHANGED',
                'User changed their transaction PIN',
                risk_level='low'
            )
            
            messages.success(request, 'Transaction PIN changed successfully!')
            return redirect('accounts:profile')
    else:
        form = TransactionPINChangeForm(request.user)
    
    return render(request, 'accounts/partials/transaction_pin_form.html', {'form': form})

# Legacy view functions for backward compatibility
def register(request):
    """Legacy register view - redirect to new registration"""
    return redirect('accounts:register')

def verify_email(request):
    """Legacy verify email view - redirect to new verification"""
    return redirect('accounts:verify_email')

def resend_verification(request):
    """Legacy resend verification - redirect to new endpoint"""
    return redirect('accounts:resend_verification')

def setup_pin(request):
    """Legacy setup PIN view - redirect to new setup"""
    return redirect('accounts:setup_pin')

def login_view_legacy(request):
    """Legacy login view - redirect to new login"""
    return redirect('accounts:login')

def user_logout(request):
    """Legacy logout view - redirect to new logout"""
    return redirect('accounts:logout')

def profile(request):
    """Legacy redirect to new profile view"""
    return redirect('accounts:profile')


# Custom Password Reset Views using Gmail API
def custom_password_reset_view(request):
    """Custom password reset view using Gmail API"""
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, 'Email address is required.')
            return render(request, 'accounts/password_reset.html')
        
        try:
            user = CustomUser.objects.get(email=email, is_active=True)
            
            # Generate reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create reset link
            reset_link = request.build_absolute_uri(
                reverse('accounts:password_reset_confirm', kwargs={
                    'uidb64': uid,
                    'token': token
                })
            )
            
            # Send password reset email via Gmail API
            try:
                send_password_reset_email(user, reset_link)
                
                # Log password reset request
                audit_logger = AuditLogger(user=user, request=request)
                audit_logger.log_security_event(
                    'PASSWORD_RESET_REQUESTED',
                    'User requested password reset',
                    risk_level='low'
                )
                
                messages.success(request, 'Password reset email sent successfully!')
                return redirect('accounts:password_reset_done')
                
            except Exception as email_error:
                logger.error(f"Failed to send password reset email: {str(email_error)}")
                messages.error(request, 'Failed to send password reset email. Please try again.')
                
        except CustomUser.DoesNotExist:
            # Don't reveal if email exists - security best practice
            messages.success(request, 'If an account with that email exists, you will receive a password reset email.')
            return redirect('accounts:password_reset_done')
            
    return render(request, 'accounts/password_reset.html')


def custom_password_reset_done_view(request):
    """Custom password reset done view"""
    return render(request, 'accounts/password_reset_done.html')


def custom_password_reset_confirm_view(request, uidb64, token):
    """Custom password reset confirm view"""
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    
    # Check if token is valid
    validlink = user is not None and default_token_generator.check_token(user, token)
    
    if request.method == 'POST' and validlink:
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            
            # Log password reset completion
            audit_logger = AuditLogger(user=user, request=request)
            audit_logger.log_security_event(
                'PASSWORD_RESET_COMPLETED',
                'User completed password reset',
                risk_level='medium'
            )
            
            messages.success(request, 'Password reset successfully! Please log in with your new password.')
            return redirect('accounts:password_reset_complete')
    else:
        form = SetPasswordForm(user) if validlink else None
    
    context = {
        'form': form,
        'validlink': validlink,
    }
    
    return render(request, 'accounts/password_reset_confirm.html', context)


def custom_password_reset_complete_view(request):
    """Custom password reset complete view"""
    return render(request, 'accounts/password_reset_complete.html')
