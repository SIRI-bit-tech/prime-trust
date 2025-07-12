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
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'gender',
                 'password1', 'password2', 'security_question', 'security_answer')

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
        
        # Validate gender
        gender = cleaned_data.get('gender')
        if not gender:
            self.add_error('gender', 'Please select a gender.')
        
        # Validate date of birth
        date_of_birth = cleaned_data.get('date_of_birth')
        if not date_of_birth:
            self.add_error('date_of_birth', 'Please provide your date of birth.')
        
        # Validate state
        state = cleaned_data.get('state')
        if not state:
            self.add_error('state', 'Please select a state.')
        
        # Validate city
        city = cleaned_data.get('city')
        if not city:
            self.add_error('city', 'Please enter your city.')
        
        # Validate address
        address = cleaned_data.get('address')
        if not address:
            self.add_error('address', 'Please enter your address.')

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
            
            # Save profile fields
            profile.date_of_birth = self.cleaned_data.get('date_of_birth')
            profile.city = self.cleaned_data.get('city')
            profile.state = self.cleaned_data.get('state')
            profile.address = self.cleaned_data.get('address')
            profile.save()
            
            # Handle gender field - save in user object if it has the field
            gender = self.cleaned_data.get('gender')
            if gender and hasattr(user, 'gender'):
                user.gender = gender
                user.save()
            
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
    first_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
            'placeholder': 'Last Name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
            'placeholder': 'Email Address'
        })
    )
    phone_number = forms.CharField(
        max_length=17, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
            'placeholder': 'Phone Number'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'phone_number')

class UserProfileUpdateForm(forms.ModelForm):
    """Form for updating additional user profile information"""
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
            'type': 'date'
        })
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
            'rows': 3,
            'placeholder': 'Street Address'
        })
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.Select(choices=[('', 'Select City')], attrs={
            'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
        })
    )
    state = forms.ChoiceField(
        choices=[('', 'Select State')] + US_STATES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm',
        })
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100'
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

class TransactionPinForm(forms.Form):
    """Transaction PIN form for registration"""
    pin = forms.CharField(
        max_length=6,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 4-6 digit PIN',
            'pattern': '[0-9]{4,6}',
            'title': 'Enter a 4-6 digit PIN'
        })
    )
    confirm_pin = forms.CharField(
        max_length=6,
        min_length=4,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your PIN',
            'pattern': '[0-9]{4,6}',
            'title': 'Confirm your 4-6 digit PIN'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        pin = cleaned_data.get('pin')
        confirm_pin = cleaned_data.get('confirm_pin')
        
        if pin and confirm_pin:
            if pin != confirm_pin:
                raise ValidationError("PINs don't match")
            
            # Validate PIN format
            if not pin.isdigit():
                raise ValidationError("PIN must contain only numbers")
            
            # Check for weak PINs
            if len(set(pin)) == 1:  # All same digits
                raise ValidationError("PIN cannot have all same digits")
            
            if pin in ['1234', '0000', '1111', '2222', '3333', '4444', '5555', '6666', '7777', '8888', '9999']:
                raise ValidationError("PIN is too common. Please choose a different PIN")
        
        return cleaned_data