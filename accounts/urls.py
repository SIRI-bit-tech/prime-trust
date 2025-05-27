from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('verify-email/<int:user_id>/', views.verify_email, name='verify_email'),
    path('resend-verification/<int:user_id>/', views.resend_verification, name='resend_verification'),
    path('login/', views.user_login, name='login'),
    path('verify-login/<int:user_id>/', views.verify_login, name='verify_login'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
]
