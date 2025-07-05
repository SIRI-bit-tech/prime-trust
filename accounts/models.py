from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator, MinLengthValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password, check_password
import random
import string
import uuid

class CustomUser(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)
    phone_regex = RegexValidator(
        regex=r'^(\(\d{3}\) \d{3}-\d{4}|\+?1?\d{9,15})$',
        message="Phone number must be in US format: (555) 123-4567 or international format: +999999999."
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    
    # Security question fields
    SECURITY_QUESTIONS = [
        ('mother_maiden', "What is your mother's maiden name?"),
        ('pet_name', "What was your first pet's name?"),
        ('birth_city', "In what city were you born?"),
        ('school_name', "What was the name of your first school?"),
        ('favorite_color', "What is your favorite color?"),
        ('favorite_food', "What is your favorite food?"),
    ]
    
    security_question = models.CharField(
        max_length=50,
        choices=SECURITY_QUESTIONS,
        blank=True,
        null=True
    )
    security_answer = models.CharField(max_length=255, blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.email
    
    def set_security_question(self, question, answer):
        """Set the security question and hashed answer."""
        self.security_question = question
        self.security_answer = make_password(answer.lower().strip())
        self.save()
    
    def check_security_answer(self, answer):
        """Verify the security answer."""
        if not self.security_answer:
            return False
        return check_password(answer.lower().strip(), self.security_answer)

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    company = models.CharField(max_length=100, blank=True)
    transaction_pin = models.CharField(
        max_length=128,  # Using 128 for hashed pin storage
        null=True,
        blank=True,
        help_text=_('4-digit PIN used for transaction verification')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()}'s Profile"

    def set_transaction_pin(self, pin):
        """Set the transaction PIN using proper hashing."""
        if not pin.isdigit() or len(pin) != 4:
            raise ValueError(_('Transaction PIN must be exactly 4 digits'))
        self.transaction_pin = make_password(pin)
        self.save()

    def check_transaction_pin(self, pin):
        """Verify the transaction PIN."""
        if not self.transaction_pin:
            return False
        return check_password(pin, self.transaction_pin)

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a UserProfile for new users"""
    if created:
        # Create user profile
        UserProfile.objects.create(user=instance)
