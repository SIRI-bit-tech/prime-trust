from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from .auth_views import (
    CustomTokenObtainPairView,
    verify_login_api,
    logout_api,
    profile_api,
    update_profile_api,
    change_password_api,
    resend_login_code_api,
    enable_2fa_api,
    disable_2fa_api,
    verify_2fa_api,
    user_devices_api,
    revoke_device_api,
    security_summary_api,
    generate_backup_codes_api,
    get_2fa_status_api,
)
from .viewsets import (
    AccountViewSet, TransactionViewSet, BankingViewSet,
    BitcoinViewSet, LoanApplicationViewSet, LoanAccountViewSet,
    InvestmentAccountViewSet, InvestmentViewSet,
    InsurancePolicyViewSet, InsuranceClaimViewSet,
    BillerViewSet, BillPaymentViewSet, PayeeViewSet, ScheduledPaymentViewSet,
    NotificationViewSet, AnalyticsViewSet, VirtualCardViewSet
)

app_name = 'api'

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'banking', BankingViewSet, basename='banking')

# Phase 2: Advanced Banking Features
router.register(r'bitcoin', BitcoinViewSet, basename='bitcoin')
router.register(r'virtual-cards', VirtualCardViewSet, basename='virtual-card')
router.register(r'loan-applications', LoanApplicationViewSet, basename='loan-application')
router.register(r'loan-accounts', LoanAccountViewSet, basename='loan-account')
router.register(r'investment-accounts', InvestmentAccountViewSet, basename='investment-account')
router.register(r'investments', InvestmentViewSet, basename='investment')
router.register(r'insurance-policies', InsurancePolicyViewSet, basename='insurance-policy')
router.register(r'insurance-claims', InsuranceClaimViewSet, basename='insurance-claim')
router.register(r'billers', BillerViewSet, basename='biller')
router.register(r'bill-payments', BillPaymentViewSet, basename='bill-payment')
router.register(r'payees', PayeeViewSet, basename='payee')
router.register(r'scheduled-payments', ScheduledPaymentViewSet, basename='scheduled-payment')
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

# API v1 URL patterns
v1_patterns = [
    # Authentication endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/verify-login/', verify_login_api, name='verify_login'),
    path('auth/logout/', logout_api, name='logout'),
    path('auth/resend-code/', resend_login_code_api, name='resend_login_code'),
    
    # User profile endpoints
    path('profile/', profile_api, name='profile'),
    path('profile/update/', update_profile_api, name='update_profile'),
    path('profile/change-password/', change_password_api, name='change_password'),
    
    # Security & 2FA endpoints
    path('security/enable-2fa/', enable_2fa_api, name='enable_2fa'),
    path('security/disable-2fa/', disable_2fa_api, name='disable_2fa'),
    path('security/verify-2fa/', verify_2fa_api, name='verify_2fa'),
    path('security/2fa/status/', get_2fa_status_api, name='get_2fa_status'),
    path('security/2fa/backup-codes/', generate_backup_codes_api, name='generate_backup_codes'),
    path('security/devices/', user_devices_api, name='user_devices'),
    path('security/revoke-device/', revoke_device_api, name='revoke_device'),
    path('security/summary/', security_summary_api, name='security_summary'),
    
    # Include router URLs
    path('', include(router.urls)),
]

urlpatterns = [
    # API versioning
    path('v1/', include(v1_patterns)),
    
    # API Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
] 