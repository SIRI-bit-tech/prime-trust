from django.urls import path
from . import views

app_name = 'banking'

urlpatterns = [
    path('send-money/', views.send_money, name='send_money'),
    path('check-recipient/', views.check_recipient, name='check_recipient'),
    path('transaction/<int:transaction_id>/', views.get_transaction_details, name='transaction_details'),
    path('deposit/', views.deposit, name='deposit'),
    path('payment-fields/', views.payment_fields, name='payment_fields'),
]
