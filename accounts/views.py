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
from django.http import HttpResponse, HttpResponseRedirect
from django_htmx.http import trigger_client_event, HttpResponseClientRedirect
from datetime import datetime

from .models import CustomUser, UserProfile
from .forms import (
    CustomUserCreationForm, 
    VerificationForm, 
    LoginForm, 
    ProfileUpdateForm, 
    UserProfileUpdateForm,
    PasswordChangeForm
)
from .utils import generate_verification_code, send_verification_email, verify_code

def register(request):
    """Single-step user registration"""
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                # Create user but don't save yet
                user = form.save(commit=False)
                user.is_active = False
                user.save()
                
                # Generate and send verification code
                code = generate_verification_code()
                
                if send_verification_email(user.email, code):
                    # Store email in session for verification
                    request.session['registration_email'] = user.email
                    messages.success(request, 'Account created successfully! Please check your email for verification.')
                    
                    redirect_url = reverse('accounts:verify_email')
                    
                    # Handle HTMX request
                    if request.htmx:
                        response = HttpResponseClientRedirect(redirect_url)
                        return response
                    
                    return redirect('accounts:verify_email')
                else:
                    messages.error(request, 'Error sending verification email. Please try again.')
                    user.delete()  # Delete the user if email sending fails
            except Exception as e:
                messages.error(request, 'An error occurred during registration. Please try again.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def verify_email(request):
    """Handle email verification after registration"""
    email = request.session.get('registration_email')
    if not email:
        messages.error(request, 'No registration in progress. Please register first.')
        return redirect('accounts:register')
    
    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            try:
                code = form.cleaned_data['verification_code']
                if verify_code(email, code):
                    # Activate user and log them in
                    user = CustomUser.objects.get(email=email)
                    user.is_active = True
                    user.save()
                    
                    # Clear session data
                    del request.session['registration_email']
                    
                    # Log the user in
                    login(request, user)
                    messages.success(request, 'Email verified successfully! Welcome to PrimeTrust.')
                    
                    # Handle HTMX request
                    if request.htmx:
                        response = HttpResponseClientRedirect(reverse('dashboard:home'))
                        return response
                    
                    return redirect('dashboard:home')
                else:
                    messages.error(request, 'Invalid or expired verification code.')
            except Exception as e:
                messages.error(request, 'An error occurred during verification. Please try again.')
    else:
        form = VerificationForm()
        messages.info(request, 'Please check your email for the verification code.')
    
    context = {
        'form': form,
        'user_email': email,
    }
    
    # Handle HTMX request
    if request.htmx:
        return render(request, 'accounts/partials/verification_form.html', context)
    
    return render(request, 'accounts/verify_email.html', context)

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            # Generate and send verification code
            code = generate_verification_code()
            if send_verification_email(user.email, code, is_login=True):
                request.session['login_email'] = user.email
                return redirect('accounts:verify_login')
            else:
                messages.error(request, 'Error sending verification code. Please try again.')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def verify_login(request):
    email = request.session.get('login_email')
    if not email:
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = VerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['verification_code']
            if verify_code(email, code):
                # Log the user in
                user = CustomUser.objects.get(email=email)
                login(request, user)
                messages.success(request, 'Login successful!')
                return redirect('dashboard:home')
            else:
                messages.error(request, 'Invalid or expired verification code.')
    else:
        form = VerificationForm()
    
    return render(request, 'accounts/verify_login.html', {'form': form})

def resend_verification(request):
    """Resend verification code"""
    email = request.session.get('registration_email')
    if not email:
        if request.htmx:
            return HttpResponse(
                '<div class="text-sm text-center text-red-600">No registration in progress. Please try again.</div>'
            )
        messages.error(request, 'No registration in progress.')
        return redirect('accounts:register')
    
    try:
        user = CustomUser.objects.get(email=email)
        code = generate_verification_code()
        if send_verification_email(email, code):
            if request.htmx:
                return HttpResponse(
                    '<div class="text-sm text-center text-green-600">'
                    'Verification code sent! Please check your email.'
                    '</div>'
                )
            messages.success(request, 'Verification code resent successfully.')
        else:
            if request.htmx:
                return HttpResponse(
                    '<div class="text-sm text-center text-red-600">'
                    'Error sending verification code. Please try again.'
                    '</div>'
                )
            messages.error(request, 'Error sending verification code. Please try again.')
    except CustomUser.DoesNotExist:
        if request.htmx:
            return HttpResponse(
                '<div class="text-sm text-center text-red-600">User not found. Please register again.</div>'
            )
        messages.error(request, 'User not found.')
        return redirect('accounts:register')
    
    if not request.htmx:
        return redirect('accounts:verify_email')

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
        'profile_form': profile_form,
        'swift_code': settings.BANK_SWIFT_CODE
    }
    
    if request.htmx:
        return render(request, 'accounts/partials/profile_form.html', context)
    return render(request, 'accounts/profile.html', context)

@login_required
def change_password(request):
    """Change password view"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:login')
    else:
        form = PasswordChangeForm()
    
    # Get current time for greeting
    current_hour = datetime.now().hour
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

def send_login_code_email(user, code):
    """Send login verification code email"""
    subject = 'Login Verification Code'
    html_message = render_to_string('emails/login_code_email.html', {
        'user': user,
        'code': code
    })
    plain_message = strip_tags(html_message)
    to_email = user.email
    
    # Send email using Django's built-in email functionality
    return send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        html_message=html_message,
        fail_silently=False,
    )
