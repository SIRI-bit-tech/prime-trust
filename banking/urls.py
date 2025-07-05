from django.urls import path
from . import views, views_bitcoin

app_name = 'banking'

urlpatterns = [
    path('send-money-options/', views.send_money_options, name='send_money_options'),
    path('send-money/', views.send_money, name='send_money'),
    path('check-recipient/', views.check_recipient, name='check_recipient'),
    path('transaction/<int:transaction_id>/', views.get_transaction_details, name='transaction_details'),
    path('deposit/', views.deposit, name='deposit'),
    path('payment-fields/', views.payment_fields, name='payment_fields'),
    path('receive-bitcoin/', views_bitcoin.receive_bitcoin, name='receive_bitcoin'),
    path('send-bitcoin/', views_bitcoin.send_bitcoin, name='send_bitcoin'),
    path('send-bitcoin-page/', views_bitcoin.send_bitcoin_page, name='send_bitcoin_page'),
    path('swap-bitcoin/', views_bitcoin.swap_bitcoin, name='swap_bitcoin'),
]
