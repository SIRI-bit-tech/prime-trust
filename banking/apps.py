from django.apps import AppConfig


class BankingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'banking'
    
    def ready(self):
        # Import signals to register them
        import banking.signals
