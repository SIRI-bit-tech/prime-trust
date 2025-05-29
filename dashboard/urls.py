from django.urls import path
from . import views

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
    path('insurance/', views.insurance, name='insurance'),
    path('services/', views.services, name='services'),
    
    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # HTMX updates
    path('balance-update/', views.balance_update, name='balance_update'),
    path('transactions-update/', views.transactions_update, name='transactions_update'),
]
