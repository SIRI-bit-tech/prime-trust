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
    PasswordChangeForm,
    TransactionPINChangeForm,
    TransactionPINSetupForm
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
                
                # Create or update UserProfile
                profile = UserProfile.objects.get_or_create(user=user)[0]
                profile.date_of_birth = form.cleaned_data['date_of_birth']
                profile.gender = request.POST.get('gender')  # Get gender from POST data
                profile.city = form.cleaned_data['city']
                profile.state = form.cleaned_data['state']
                profile.address = form.cleaned_data['address']
                profile.save()
                
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
                messages.error(request, f'An error occurred during registration: {str(e)}')
        else:
            # Show form validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    if field == 'email' and 'already exists' in error:
                        messages.error(request, 'This email address is already registered. Please use a different email or try logging in.')
                    else:
                        messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
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
                    messages.success(request, 'Email verified successfully!')
                    
                    # Redirect to PIN setup instead of dashboard
                    redirect_url = reverse('accounts:setup_pin')
                    
                    # Handle HTMX request
                    if request.htmx:
                        response = HttpResponseClientRedirect(redirect_url)
                        return response
                    
                    return redirect('accounts:setup_pin')
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
    """Handle user login and 2FA code generation"""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            # Generate and send verification code
            code = generate_verification_code()
            if send_verification_email(user.email, code, is_login=True):
                request.session['login_email'] = user.email
                
                # Handle HTMX request
                if request.htmx:
                    return HttpResponseClientRedirect(reverse('accounts:verify_login'))
                return redirect('accounts:verify_login')
            else:
                messages.error(request, 'Error sending verification code. Please try again.')
    else:
        form = LoginForm()
    
    context = {'form': form}
    
    # Handle HTMX request
    if request.htmx:
        return render(request, 'accounts/partials/login_form.html', context)
    return render(request, 'accounts/login.html', context)

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
                
                # Handle HTMX request
                if request.htmx:
                    response = HttpResponse()
                    response['HX-Redirect'] = reverse('dashboard:home')
                    return response
                return redirect('dashboard:home')
            else:
                messages.error(request, 'Invalid or expired verification code.')
    else:
        form = VerificationForm()
    
    context = {'form': form}
    if request.htmx:
        return render(request, 'accounts/partials/login_verification_form.html', context)
    return render(request, 'accounts/verify_login.html', context)

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

@login_required
def change_transaction_pin(request):
    """Handle transaction PIN changes"""
    if request.method == 'POST':
        form = TransactionPINChangeForm(request.user, request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Transaction PIN updated successfully.')
                
                # Return success message for HTMX
                return HttpResponse(
                    '<div class="rounded-md bg-green-50 p-4 mb-6">'
                    '<div class="flex">'
                    '<div class="flex-shrink-0">'
                    '<svg class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">'
                    '<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>'
                    '</svg>'
                    '</div>'
                    '<div class="ml-3">'
                    '<p class="text-sm font-medium text-green-800">Transaction PIN updated successfully</p>'
                    '</div>'
                    '</div>'
                    '</div>'
                )
            except Exception as e:
                messages.error(request, 'An error occurred. Please try again.')
    else:
        form = TransactionPINChangeForm(request.user)
    
    return render(request, 'accounts/partials/transaction_pin_form.html', {'form': form})

@login_required
def setup_pin(request):
    """Handle initial transaction PIN setup"""
    # Check if PIN is already set
    if request.user.profile.transaction_pin:
        messages.info(request, 'Transaction PIN is already set.')
        return redirect('dashboard:home')
    
    if request.method == 'POST':
        form = TransactionPINSetupForm(request.POST)
        if form.is_valid():
            try:
                # Set the transaction PIN
                request.user.profile.set_transaction_pin(form.cleaned_data['transaction_pin'])
                request.user.profile.save()
                
                messages.success(request, 'Transaction PIN set successfully! Welcome to PrimeTrust.')
                return redirect('dashboard:home')
            except Exception as e:
                messages.error(request, 'An error occurred while setting your PIN. Please try again.')
    else:
        form = TransactionPINSetupForm()
    
    return render(request, 'accounts/setup_pin.html', {'form': form})

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
