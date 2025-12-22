"""App configuration for my_garage."""
from django.apps import AppConfig


class MyGarageConfig(AppConfig):
    """Configuration for the my_garage app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_apps.my_garage'
    verbose_name = 'My Garage'

    def ready(self):
        """Import signal handlers when app is ready."""
        # Import signals here if needed in the future
        # import django_apps.my_garage.signals
        pass
