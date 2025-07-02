from django.core.management.base import BaseCommand
from accounts.models import CustomUser
from banking.models import BitcoinWallet
import secrets
import hashlib

class Command(BaseCommand):
    help = 'Creates Bitcoin wallets for users who don\'t have one'

    def handle(self, *args, **options):
        users_without_wallet = CustomUser.objects.exclude(bitcoin_wallet__isnull=False)
        wallets_created = 0

        for user in users_without_wallet:
            wallet_seed = secrets.token_bytes(32)
            wallet_address = hashlib.sha256(wallet_seed).hexdigest()
            BitcoinWallet.objects.create(
                user=user,
                address=wallet_address
            )
            wallets_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {wallets_created} Bitcoin wallet(s)'
            )
        ) 