from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # Enhanced Registration Flow
    path('register/', views.register_view, name='register'),
    path('verify-email/', views.verify_email_view, name='verify_email'),
    path('setup-2fa/', views.setup_2fa_view, name='setup_2fa'),
    path('backup-codes/', views.backup_codes_view, name='backup_codes'),
    path('setup-pin/', views.setup_pin_view, name='setup_pin'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('change-transaction-pin/', views.change_transaction_pin, name='change_transaction_pin'),
    
    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='accounts/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
    
    # AJAX endpoints
    path('resend-verification/', views.resend_verification_code, name='resend_verification'),
    path('check-2fa-token/', views.check_2fa_token, name='check_2fa_token'),
]
