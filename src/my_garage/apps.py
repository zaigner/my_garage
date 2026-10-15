"""App configuration for my_garage."""

from django.apps import AppConfig


class MyGarageConfig(AppConfig):
    """Configuration for the my_garage app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "my_garage"
    verbose_name = "My Garage"

    def ready(self):
        """Import signal handlers when app is ready."""
        from pillow_heif import register_heif_opener

        from my_garage import signals  # noqa: F401

        # Let ImageField validation open iPhone HEIC uploads; forms convert
        # them to JPEG before storage (my_garage.utils.images).
        register_heif_opener()
