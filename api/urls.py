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
)
from .viewsets import AccountViewSet, TransactionViewSet, BankingViewSet

app_name = 'api'

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'banking', BankingViewSet, basename='banking')

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