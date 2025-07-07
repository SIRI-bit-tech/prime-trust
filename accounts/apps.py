from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """Import models when the app is ready"""
        try:
            # Import security models to ensure they're registered
            from . import models_security
        except ImportError:
            pass
