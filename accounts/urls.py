from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('verify-security-question/', views.verify_security_question, name='verify_security_question'),
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),
]
