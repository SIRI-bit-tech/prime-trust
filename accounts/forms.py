from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserProfile

# US States data
US_STATES = [
    ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'),
    ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'),
    ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'),
    ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'),
    ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'),
    ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'),
    ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'),
    ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'),
    ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'),
    ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'),
    ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'),
    ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'),
    ('WI', 'Wisconsin'), ('WY', 'Wyoming'), ('DC', 'District of Columbia')
]

class CustomUserCreationForm(UserCreationForm):
    """
    A form for creating new users with email, phone number, password, and name.
    """
    GENDER_CHOICES = [
        ('F', 'Female'),
        ('M', 'Male'),
        ('C', 'Custom'),
    ]

    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'form-input',
        'placeholder': 'First name'
    }))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'form-input',
        'placeholder': 'Surname'
    }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-input',
        'placeholder': 'Mobile number or email address'
    }))
    phone_number = forms.CharField(max_length=17, required=True, widget=forms.TextInput(attrs={
        'class': 'form-input',
        'placeholder': 'Phone number'
    }))
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={
        'class': 'form-input',
        'placeholder': 'New password',
        'id': 'id_password1'
    }))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={
        'class': 'form-input',
        'placeholder': 'Confirm password',
        'id': 'id_password2'
    }))
    date_of_birth = forms.DateField(required=True, widget=forms.HiddenInput())
    gender = forms.ChoiceField(choices=GENDER_CHOICES, required=True)
    state = forms.ChoiceField(
        choices=[('', 'Select State')] + US_STATES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-input',
            'id': 'id_state'
        })
    )
    city = forms.CharField(
        max_length=100,
        required=True
    )
    address = forms.CharField(widget=forms.Textarea(attrs={
        'class': 'form-textarea',
        'placeholder': 'Address',
        'rows': 3
    }), required=True)
    security_question = forms.ChoiceField(
        choices=CustomUser.SECURITY_QUESTIONS,
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-input'
        })
    )
    security_answer = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={
        'class': 'form-input',
        'placeholder': 'Security Answer'
    }))
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone_number',
                 'date_of_birth', 'gender', 'state', 'city', 'address', 'password1', 'password2',
                 'security_question', 'security_answer')

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if password1 and password2 and password1 != password2:
            self.add_error('password2', 'The passwords do not match.')

        # Generate username from email
        email = cleaned_data.get('email')
        if email:
            username = email.split('@')[0]
            # Ensure username is unique
            base_username = username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            cleaned_data['username'] = username

        return cleaned_data
    
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
        user.username = self.cleaned_data['username']  # Set the generated username
        
        if commit:
            user.save()
            # Create or update UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.date_of_birth = self.cleaned_data['date_of_birth']
            profile.city = self.cleaned_data['city']
            profile.state = self.cleaned_data['state']
            profile.address = self.cleaned_data['address']
            
            profile.save()
            
            # Set security question and answer on user
            question = self.cleaned_data.get('security_question')
            answer = self.cleaned_data.get('security_answer')
            if question and answer:
                user.set_security_question(question, answer)
        
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
    
    def get_user(self):
        """Return the authenticated user after clean()"""
        return self.cleaned_data.get('user')

class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile information"""
    first_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=17, required=True)
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'email', 'phone_number')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({'class': 'form-input'})
        self.fields['first_name'].widget.attrs.update({'class': 'form-input', 'placeholder': 'Full Name'})
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

class TransactionPINChangeForm(forms.Form):
    """Form for changing transaction PIN"""
    current_pin = forms.CharField(
        max_length=4,
        min_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Current PIN',
            'pattern': '[0-9]*',
            'inputmode': 'numeric',
            'autocomplete': 'off'
        })
    )
    new_pin = forms.CharField(
        max_length=4,
        min_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'New PIN',
            'pattern': '[0-9]*',
            'inputmode': 'numeric',
            'autocomplete': 'off'
        })
    )
    confirm_new_pin = forms.CharField(
        max_length=4,
        min_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm New PIN',
            'pattern': '[0-9]*',
            'inputmode': 'numeric',
            'autocomplete': 'off'
        })
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_pin(self):
        current_pin = self.cleaned_data.get('current_pin')
        if not self.user.profile.check_transaction_pin(current_pin):
            raise ValidationError(_('Current PIN is incorrect'))
        return current_pin

    def clean_new_pin(self):
        new_pin = self.cleaned_data.get('new_pin')
        if not new_pin.isdigit():
            raise ValidationError(_('PIN must contain only digits'))
        return new_pin

    def clean(self):
        cleaned_data = super().clean()
        new_pin = cleaned_data.get('new_pin')
        confirm_new_pin = cleaned_data.get('confirm_new_pin')

        if new_pin and confirm_new_pin:
            if new_pin != confirm_new_pin:
                self.add_error('confirm_new_pin', _('New PINs do not match'))

        return cleaned_data

    def save(self):
        new_pin = self.cleaned_data.get('new_pin')
        self.user.profile.set_transaction_pin(new_pin)
        return self.user.profile

class TransactionPINSetupForm(forms.Form):
    """Form for initial transaction PIN setup"""
    transaction_pin = forms.CharField(
        max_length=4,
        min_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter 4-digit Transaction PIN',
            'pattern': '[0-9]*',
            'inputmode': 'numeric',
            'autocomplete': 'off'
        })
    )
    confirm_transaction_pin = forms.CharField(
        max_length=4,
        min_length=4,
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm Transaction PIN',
            'pattern': '[0-9]*',
            'inputmode': 'numeric',
            'autocomplete': 'off'
        })
    )

    def clean_transaction_pin(self):
        pin = self.cleaned_data.get('transaction_pin')
        if not pin.isdigit():
            raise ValidationError(_('Transaction PIN must contain only digits'))
        return pin

    def clean(self):
        cleaned_data = super().clean()
        pin = cleaned_data.get('transaction_pin')
        confirm_pin = cleaned_data.get('confirm_transaction_pin')

        if pin and confirm_pin:
            if pin != confirm_pin:
                self.add_error('confirm_transaction_pin', _('Transaction PINs do not match'))

        return cleaned_data