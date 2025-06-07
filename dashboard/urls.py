from django.urls import path
from . import views
from .views_more_services import more_services

app_name = 'dashboard'

urlpatterns = [
    # Main pages
    path('', views.home, name='home'),
    path('accounts/', views.accounts, name='accounts'),
    path('transactions/', views.transactions, name='transactions'),
    path('cards/', views.cards, name='cards'),
    path('cards/<int:card_id>/', views.card_details, name='card_details'),
    
    # Banking Features
    path('transfer/', views.transfer_money, name='transfer'),
    path('pay-bills/', views.pay_bills, name='pay-bills'),
    
    # Loans
    path('loans/', views.loans, name='loans'),
    path('loans/new/', views.new_loan, name='new_loan'),
    path('loans/apply/', views.handle_loan_application, name='apply_loan'),
    path('loans/<int:loan_id>/', views.loan_detail, name='loan_detail'),
    path('loans/<int:loan_id>/payment/', views.make_loan_payment, name='make_loan_payment'),
    
    # Investments and Insurance
    path('investments/', views.investments, name='investments'),
    path('investments/new/', views.new_investment, name='new_investment'),
    path('investments/<int:account_id>/', views.investment_detail, name='investment_detail'),
    path('investments/<int:pk>/edit/', views.new_investment, name='edit_investment'),
    path('insurance/', views.insurance, name='insurance'),
    path('insurance/new/', views.new_insurance_policy, name='new_insurance_policy'),
    path('insurance/policy/<int:pk>/edit/', views.new_insurance_policy, name='edit_insurance_policy'),
    path('insurance/policy/<int:policy_id>/', views.insurance_policy_detail, name='insurance_policy_detail'),
    path('services/', views.services, name='services'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # HTMX updates
    path('balance-update/', views.balance_update, name='balance_update'),
    path('transactions-update/', views.transactions_update, name='transactions_update'),
    path('metrics-update/', views.metrics_update, name='metrics_update'),
    
    # More Services
    path('more-services/', more_services, name='more_services'),
]
