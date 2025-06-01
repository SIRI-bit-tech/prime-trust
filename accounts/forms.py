from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
import re
from django.core.exceptions import ValidationError
from .models import CustomUser, UserProfile

class CustomUserCreationForm(UserCreationForm):
    """
    A form for creating new users with email, phone number, password, and name.
    """
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=17, required=True)
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)
    date_of_birth = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    city = forms.CharField(max_length=100, required=True)
    state = forms.CharField(max_length=100, required=True)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set username as email
        self.fields['email'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Email'})
        self.fields['first_name'].widget.attrs.update({'class': 'form-input', 'placeholder': 'First Name'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Last Name'})
        self.fields['phone_number'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Phone Number'})
        self.fields['password1'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Confirm Password'})
        self.fields['date_of_birth'].widget.attrs.update({'class': 'form-input'})
        self.fields['city'].widget.attrs.update({'class': 'form-input', 'placeholder': 'City'})
        self.fields['state'].widget.attrs.update({'class': 'form-input', 'placeholder': 'State'})
        self.fields['address'].widget.attrs.update({'class': 'form-textarea', 'placeholder': 'Address'})
    
    def clean_phone_number(self):
        """Clean and validate the phone number field."""
        phone_number = self.cleaned_data.get('phone_number')
        
        # If it's already in the correct format, return it
        if phone_number and re.match(r'^(\(\d{3}\) \d{3}-\d{4}|\+?1?\d{9,15})$', phone_number):
            return phone_number
            
        # Try to reformat the number if it's not in the correct format
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', phone_number) if phone_number else ''
        
        # Format as US number if it has 10 digits
        if len(digits_only) == 10:
            return f'({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}'
            
        # If it has more digits, try to format as international
        elif len(digits_only) >= 9 and len(digits_only) <= 15:
            # Add + if it doesn't start with one
            if not phone_number.startswith('+'):
                return f'+{digits_only}'
            return phone_number
            
        # If we can't format it properly, raise validation error
        raise forms.ValidationError(
            "Phone number must be in US format: (555) 123-4567 or international format with 9-15 digits."
        )
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # Set username to email
        
        if commit:
            user.save()
            # Use get_or_create to avoid IntegrityError
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'date_of_birth': self.cleaned_data['date_of_birth'],
                    'city': self.cleaned_data['city'],
                    'state': self.cleaned_data['state'],
                    'address': self.cleaned_data['address']
                }
            )
        
        return user

class VerificationForm(forms.Form):
    """Form for email verification code"""
    verification_code = forms.CharField(
        max_length=6, 
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input', 
            'placeholder': 'Enter 6-digit code',
            'autocomplete': 'off'
        })
    )

class LoginForm(forms.Form):
    """Form for user login with email and password"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input', 
            'placeholder': 'Email',
            'autocomplete': 'email'
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password',
            'autocomplete': 'current-password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            try:
                user = CustomUser.objects.get(email=email)
                if not user.is_active:
                    raise ValidationError("This account is inactive.")
                if not user.check_password(password):
                    raise ValidationError("Invalid email or password.")
                # Store the user in cleaned_data for the view to use
                cleaned_data['user'] = user
            except CustomUser.DoesNotExist:
                raise ValidationError("Invalid email or password.")
        
        return cleaned_data

class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile information"""
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=17, required=True)
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone_number')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-input'})
        self.fields['first_name'].widget.attrs.update({'class': 'form-input'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-input'})
        self.fields['phone_number'].widget.attrs.update({'class': 'form-input'})

class UserProfileUpdateForm(forms.ModelForm):
    """Form for updating additional user profile information"""
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date'
        })
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 3
        })
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'City'
        })
    )
    state = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'State'
        })
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-input'
        })
    )
    
    class Meta:
        model = UserProfile
        fields = ('date_of_birth', 'address', 'city', 'state', 'profile_picture')

class PasswordChangeForm(forms.Form):
    """Form for changing user password"""
    current_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Current Password'
        })
    )
    new_password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'New Password'
        })
    )
    new_password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm New Password'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise ValidationError("Your current password was entered incorrectly.")
        return current_password
    
    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise ValidationError("The two password fields didn't match.")
        
        return cleaned_data
    
    def save(self, commit=True):
        password = self.cleaned_data["new_password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user