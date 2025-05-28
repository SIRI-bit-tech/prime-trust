from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import random
import string
import uuid

class CustomUser(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    email_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    verification_code_created_at = models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.email
    
    def generate_verification_code(self):
        """Generate a 6-digit verification code and save it to the user model."""
        code = ''.join(random.choices(string.digits, k=6))
        self.verification_code = code
        self.verification_code_created_at = timezone.now()
        self.save()
        return code
    
    def verify_email(self, code):
        """Verify the user's email with the provided code."""
        # Check if code is valid and not expired (valid for 10 minutes)
        if (self.verification_code == code and 
            self.verification_code_created_at and 
            timezone.now() < self.verification_code_created_at + timezone.timedelta(minutes=10)):
            self.email_verified = True
            self.verification_code = None
            self.verification_code_created_at = None
            self.save()
            return True
        return False

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile and accounts for new users"""
    if created:
        # Create user profile
        UserProfile.objects.create(user=instance)
        
        # Import here to avoid circular import
        from banking.models import Account
        
        # Create a checking account with a unique account number
        # The routing number and virtual card will be created automatically by the Account model's save method
        checking_account = Account.objects.create(
            user=instance,
            account_number=f"PT{uuid.uuid4().hex[:8].upper()}",
            account_type='checking',
            balance=0.00
        )
        
        # Also create a savings account
        Account.objects.create(
            user=instance,
            account_number=f"PS{uuid.uuid4().hex[:8].upper()}",
            account_type='savings',
            balance=0.00
        )
