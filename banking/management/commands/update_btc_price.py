from django.core.management.base import BaseCommand
from django.core.cache import cache
from decimal import Decimal
import requests

class Command(BaseCommand):
    help = 'Updates Bitcoin price in cache'

    def handle(self, *args, **options):
        try:
            response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd')
            if response.status_code == 200:
                btc_price = Decimal(str(response.json()['bitcoin']['usd']))
                cache.set('btc_price_usd', btc_price, timeout=300)  # Cache for 5 minutes
                self.stdout.write(self.style.SUCCESS(f'Successfully updated BTC price: ${btc_price}'))
            else:
                self.stdout.write(self.style.ERROR('Failed to fetch BTC price'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating BTC price: {e}')) 