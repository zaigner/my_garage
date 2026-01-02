"""Settings package initialization."""
import os

# Determine which settings to use based on environment
environment = os.environ.get('DJANGO_ENVIRONMENT', 'local')

if environment == 'production':
    from .production import *
elif environment == 'test':
    from .test import *
else:
    from .local import *
