from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.http import HttpResponse, HttpResponseRedirect
from django_htmx.http import trigger_client_event
import logging

from .models import CustomUser, UserProfile
from .forms import (
    CustomUserCreationForm, 
    VerificationForm, 
    LoginForm, 
    ProfileUpdateForm, 
    UserProfileUpdateForm,
    PasswordChangeForm
)

logger = logging.getLogger(__name__)

def register(request):
    """User registration view with security question"""
    if request.user.is_authenticated:
        return redirect('dashboard:home')
        
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Set security question and answer
            security_question = request.POST.get('security_question')
            security_answer = request.POST.get('security_answer')
            
            if security_question and security_answer:
                user.set_security_question(security_question, security_answer)
                
                # Log the user in directly
                login(request, user)
                messages.success(request, 'Registration successful! You are now logged in.')
                return redirect('dashboard:home')
            else:
                messages.error(request, 'Please provide a security question and answer.')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'security_questions': CustomUser.SECURITY_QUESTIONS
    }
    if request.htmx:
        return render(request, 'accounts/partials/register_form.html', context)
    return render(request, 'accounts/register.html', context)

def verify_email(request, user_id):
    """Email verification view"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    # If already verified, redirect to login
    if user.email_verified:
        messages.success(request, 'Email already verified. Please log in.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['verification_code']
            if user.verify_email(code):
                messages.success(request, 'Email verified successfully! You can now log in.')
                return redirect('accounts:login')
            else:
                messages.error(request, 'Invalid or expired verification code.')
    else:
        form = VerificationForm()
    
    context = {
        'form': form,
        'user_email': user.email
    }
    
    if request.htmx:
        return render(request, 'accounts/partials/verification_form.html', context)
    return render(request, 'accounts/verify_email.html', context)

def resend_verification(request, user_id):
    """Resend verification code"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    if user.email_verified:
        messages.info(request, 'Email already verified.')
        return redirect('accounts:login')
    
    # Generate new code and send email
    code = user.generate_verification_code()
    send_verification_email(user, code)
    
    messages.success(request, f'Verification code sent to {user.email}')
    
    response = HttpResponseRedirect(reverse('accounts:verify_email', args=[user_id]))
    if request.htmx:
        trigger_client_event(response, 'showMessage', {'message': 'Verification code sent!'})
    return response

def user_login(request):
    """User login view with security question verification"""
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            try:
                user = form.get_user()
                # Store user ID in session for security question verification
                request.session['temp_user_id'] = user.id
                return redirect('accounts:verify_security_question')
            except Exception as e:
                logger.error(f"Unexpected error in login view: {str(e)}")
                messages.error(request, "An unexpected error occurred. Please try again.")
                return redirect('accounts:login')
    else:
        form = LoginForm()
    
    context = {'form': form}
    if request.htmx:
        return render(request, 'accounts/partials/login_form.html', context)
    return render(request, 'accounts/login.html', context)

def verify_security_question(request):
    """Verify user's security question"""
    if request.user.is_authenticated:
        return redirect('dashboard:home')
        
    user_id = request.session.get('temp_user_id')
    if not user_id:
        messages.error(request, 'Session expired. Please log in again.')
        return redirect('accounts:login')
        
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        answer = request.POST.get('security_answer', '').strip()
        if user.check_security_answer(answer):
            # Security answer is correct, log the user in
            login(request, user)
            
            # Clean up session
            if 'temp_user_id' in request.session:
                del request.session['temp_user_id']
                
            messages.success(request, f'Welcome back, {user.first_name}!')
            return redirect('dashboard:home')
        else:
            messages.error(request, 'Incorrect answer. Please try again.')
    
    context = {
        'security_question': user.get_security_question_display(),
        'user_email': user.email
    }
    
    if request.htmx:
        return render(request, 'accounts/partials/security_question_form.html', context)
    return render(request, 'accounts/verify_security_question.html', context)

def verify_login(request, user_id):
    """Verify login with code after password authentication"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Check if this is the same user stored in the session
    if 'temp_user_id' not in request.session or request.session['temp_user_id'] != user.id:
        messages.error(request, 'Authentication error. Please try logging in again.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['verification_code']
            # Verify the code is valid and not expired
            if (user.verification_code == code and 
                user.verification_code_created_at and 
                timezone.now() < user.verification_code_created_at + timezone.timedelta(minutes=10)):
                # Login successful
                login(request, user)
                user.verification_code = None
                user.verification_code_created_at = None
                user.save()
                
                # Clean up session
                if 'temp_user_id' in request.session:
                    del request.session['temp_user_id']
                
                messages.success(request, f'Welcome back, {user.first_name}!')
                return redirect('dashboard:home')
            else:
                messages.error(request, 'Invalid or expired verification code.')
    else:
        form = VerificationForm()
    
    context = {
        'form': form,
        'user_email': user.email
    }
    
    if request.htmx:
        return render(request, 'accounts/partials/login_verification_form.html', context)
    return render(request, 'accounts/verify_login.html', context)

@login_required
def user_logout(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('accounts:login')

@login_required
def profile(request):
    """User profile view"""
    user = request.user
    user_profile = user.profile
    
    if request.method == 'POST':
        user_form = ProfileUpdateForm(request.POST, instance=user)
        profile_form = UserProfileUpdateForm(request.POST, request.FILES, instance=user_profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            # Check if email changed
            email_changed = user.email != user_form.cleaned_data['email']
            
            # Save forms
            user_form.save()
            profile_form.save()
            
            # If email changed, require verification
            if email_changed:
                user.email_verified = False
                code = user.generate_verification_code()
                send_verification_email(user, code)
                messages.info(request, 'Please verify your new email address.')
                return redirect('accounts:verify_email', user_id=user.id)
            
            messages.success(request, 'Your profile has been updated!')
            
            if request.htmx:
                response = HttpResponse()
                trigger_client_event(response, 'showMessage', {'message': 'Profile updated successfully!'})
                return response
            return redirect('accounts:profile')
    else:
        user_form = ProfileUpdateForm(instance=user)
        profile_form = UserProfileUpdateForm(instance=user_profile)
    
    # Get current time for greeting
    from datetime import datetime
    current_hour = datetime.now().hour
    greeting = "Good Evening"
    if current_hour < 12:
        greeting = "Good Morning"
    elif current_hour < 18:
        greeting = "Good Afternoon"
    
    context = {
        'greeting': greeting,
        'active_tab': 'profile',
        'user_form': user_form,
        'profile_form': profile_form
    }
    
    if request.htmx:
        return render(request, 'accounts/partials/profile_form.html', context)
    return render(request, 'accounts/profile.html', context)

@login_required
def change_password(request):
    """View for changing user password"""
    user = request.user
    
    if request.method == 'POST':
        form = PasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            # Re-authenticate the user with the new password
            login(request, user)
            messages.success(request, 'Your password was successfully updated!')
            
            if request.htmx:
                response = HttpResponse()
                trigger_client_event(response, 'showMessage', {'message': 'Password updated successfully!'})
                return response
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(user)
    
    # Get current time for greeting
    from datetime import datetime
    current_hour = datetime.now().hour
    greeting = "Good Evening"
    if current_hour < 12:
        greeting = "Good Morning"
    elif current_hour < 18:
        greeting = "Good Afternoon"
    
    context = {
        'greeting': greeting,
        'active_tab': 'profile',
        'form': form
    }
    
    if request.htmx:
        return render(request, 'accounts/partials/password_change_form.html', context)
    return render(request, 'accounts/change_password.html', context)

# Helper functions
def send_verification_email(user, code):
    """Send verification email with code"""
    subject = 'Verify your PrimeTrust account'
    html_message = render_to_string('emails/verification_email.html', {
        'user': user,
        'code': code
    })
    plain_message = strip_tags(html_message)
    to_email = user.email
    
    # Use Brevo API for sending emails
    from .utils import send_email_with_brevo
    send_email_with_brevo(to_email, subject, html_message, plain_message)

def send_login_code_email(user, code):
    """Send login verification code"""
    subject = 'Your PrimeTrust login code'
    html_message = render_to_string('emails/login_code_email.html', {
        'user': user,
        'code': code
    })
    plain_message = strip_tags(html_message)
    to_email = user.email
    
    # Use Brevo API for sending emails
    from .utils import send_email_with_brevo
    send_email_with_brevo(to_email, subject, html_message, plain_message)
