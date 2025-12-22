# Complete Django Project Files & Folders Checklist

## ✅ Required Files for Executable Django Project

### 🔧 Project Root Files

- [ ] `manage.py` - Django management script
- [ ] `pyproject.toml` - Project dependencies and configuration
- [ ] `README.md` - Project documentation
- [ ] `.env` - Environment variables (DO NOT commit to git)
- [ ] `.env.example` - Example environment variables (commit to git)
- [ ] `.gitignore` - Git ignore patterns
- [ ] `requirements.txt` or use `pyproject.toml` dependencies
- [ ] `LICENSE` - Project license (already exists ✓)

### 📁 config/ - Project Configuration Directory

- [ ] `config/__init__.py` - Package initialization + Celery app import
- [ ] `config/urls.py` - Main URL routing
- [ ] `config/wsgi.py` - WSGI entry point for production servers
- [ ] `config/asgi.py` - ASGI entry point for async/WebSocket support
- [ ] `config/api_router.py` - DRF API router configuration
- [ ] `config/celery_app.py` - Celery configuration

#### config/settings/ - Settings Module

- [ ] `config/settings/__init__.py` - Settings package init (imports based on environment)
- [ ] `config/settings/base.py` - Base settings (shared across all environments)
- [ ] `config/settings/local.py` - Development settings (DEBUG=True)
- [ ] `config/settings/production.py` - Production settings (DEBUG=False)
- [ ] `config/settings/test.py` - Test settings (for pytest/unittest)

### 📁 django_apps/ - Django Applications Directory

- [ ] `django_apps/__init__.py` - Package initialization

#### django_apps/my_garage/ - Main App

**Core App Files:**
- [ ] `django_apps/my_garage/__init__.py` - App package initialization
- [ ] `django_apps/my_garage/apps.py` - AppConfig class
- [ ] `django_apps/my_garage/models.py` - Database models (already exists ✓)
- [ ] `django_apps/my_garage/admin.py` - Django admin configuration
- [ ] `django_apps/my_garage/views.py` - Web views (already exists ✓)
- [ ] `django_apps/my_garage/urls.py` - App URL routing (already exists ✓)
- [ ] `django_apps/my_garage/forms.py` - Django forms
- [ ] `django_apps/my_garage/managers.py` - Custom model managers (optional)
- [ ] `django_apps/my_garage/tasks.py` - Celery tasks (already exists ✓)

**API Layer (Service Pattern):**
- [ ] `django_apps/my_garage/api/__init__.py`
- [ ] `django_apps/my_garage/api/views.py` - DRF ViewSets
- [ ] `django_apps/my_garage/api/serializers.py` - DRF Serializers
- [ ] `django_apps/my_garage/api/selectors.py` - Data retrieval (move from root)
- [ ] `django_apps/my_garage/api/services.py` - Business logic (move from root)
- [ ] `django_apps/my_garage/api/ocr_service.py` - OCR integration
- [ ] `django_apps/my_garage/api/valuation_service.py` - Market valuation
- [ ] `django_apps/my_garage/api/mcp_client.py` - MCP client wrapper

**Migrations:**
- [ ] `django_apps/my_garage/migrations/__init__.py`
- [ ] `django_apps/my_garage/migrations/0001_initial.py` - Initial migration (auto-generated)

**Templates:**
- [ ] `django_apps/my_garage/templates/my_garage/base.html` - Base template
- [ ] `django_apps/my_garage/templates/my_garage/dashboard.html` (already exists ✓)
- [ ] `django_apps/my_garage/templates/my_garage/vehicle_detail.html`
- [ ] `django_apps/my_garage/templates/my_garage/vehicle_form.html`
- [ ] `django_apps/my_garage/templates/my_garage/service_record_list.html`

**Static Files:**
- [ ] `django_apps/my_garage/static/my_garage/css/styles.css`
- [ ] `django_apps/my_garage/static/my_garage/js/main.js`
- [ ] `django_apps/my_garage/static/my_garage/images/.gitkeep`

**Tests:**
- [ ] `django_apps/my_garage/tests/__init__.py`
- [ ] `django_apps/my_garage/tests/test_models.py`
- [ ] `django_apps/my_garage/tests/test_views.py`
- [ ] `django_apps/my_garage/tests/test_api.py`
- [ ] `django_apps/my_garage/tests/test_selectors.py`
- [ ] `django_apps/my_garage/tests/test_services.py`
- [ ] `django_apps/my_garage/tests/factories.py` - Test data factories
- [ ] `django_apps/my_garage/tests/conftest.py` - Pytest configuration

**Fixtures:**
- [ ] `django_apps/my_garage/fixtures/sample_data.yaml` - Sample data for development

### 📁 static/ - Project-level Static Files

- [ ] `static/.gitkeep` - Placeholder for collected static files

### 📁 media/ - User-uploaded Files

- [ ] `media/.gitkeep`
- [ ] `media/receipts/.gitkeep`
- [ ] `media/condition_checks/.gitkeep`

### 📁 logs/ - Application Logs

- [ ] `logs/.gitkeep`
- [ ] `logs/django.log` (auto-generated, in .gitignore)
- [ ] `logs/celery.log` (auto-generated, in .gitignore)

### 📁 templates/ - Project-level Templates (Optional)

- [ ] `templates/base.html` - Global base template
- [ ] `templates/404.html` - 404 error page
- [ ] `templates/500.html` - 500 error page
- [ ] `templates/pages/home.html` - Home page

### 📁 locale/ - Internationalization (Optional)

- [ ] `locale/.gitkeep` - If using i18n

---

## 📝 File Content Templates

### 1. manage.py

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
```

### 2. config/__init__.py

```python
"""Configuration package initialization."""
# This will make sure the Celery app is always imported when
# Django starts so that shared_task will use this app.
from .celery_app import app as celery_app

__all__ = ('celery_app',)
```

### 3. config/settings/__init__.py

```python
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
```

### 4. config/settings/base.py (Minimal)

```python
"""Base settings shared across all environments."""
import os
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-this-in-production')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'corsheaders',

    # Local apps
    'django_apps.my_garage.apps.MyGarageConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'my_garage'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Celery Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# FastAPI Service URL
FASTAPI_BASE_URL = os.environ.get('FASTAPI_BASE_URL', 'http://localhost:8001')
```

### 5. config/settings/local.py

```python
"""Development settings."""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

# CORS for development
CORS_ALLOW_ALL_ORIGINS = True

# Celery - Use eager for development (synchronous)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Install Django Debug Toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
INTERNAL_IPS = ['127.0.0.1']
```

### 6. config/urls.py

```python
"""Main URL Configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('config.api_router')),
    path('', include('django_apps.my_garage.urls', namespace='my_garage')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
```

### 7. config/wsgi.py

```python
"""WSGI config for my_garage project."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()
```

### 8. config/api_router.py

```python
"""API Router configuration."""
from rest_framework.routers import DefaultRouter, SimpleRouter
from django.conf import settings

from django_apps.my_garage.api.views import (
    VehicleViewSet,
    ServiceRecordViewSet,
    UpgradeViewSet,
    ConditionReportViewSet,
)

# Use DefaultRouter for development (browsable API), SimpleRouter for production
router = DefaultRouter() if settings.DEBUG else SimpleRouter()

# Register ViewSets
router.register("vehicles", VehicleViewSet)
router.register("service-records", ServiceRecordViewSet)
router.register("upgrades", UpgradeViewSet)
router.register("condition-reports", ConditionReportViewSet)

urlpatterns = router.urls
```

### 9. config/celery_app.py

```python
"""Celery configuration."""
import os
from celery import Celery

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

app = Celery('my_garage')

# Load config from Django settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery."""
    print(f'Request: {self.request!r}')
```

### 10. django_apps/my_garage/apps.py

```python
"""App configuration for my_garage."""
from django.apps import AppConfig


class MyGarageConfig(AppConfig):
    """Configuration for the my_garage app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_apps.my_garage'
    verbose_name = 'My Garage'

    def ready(self):
        """Import signal handlers when app is ready."""
        # Import signals here if needed
        # import django_apps.my_garage.signals
        pass
```

### 11. django_apps/my_garage/admin.py

```python
"""Django admin configuration for my_garage."""
from django.contrib import admin
from .models import Vehicle, ServiceRecord, Upgrade, ConditionReport


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    """Admin for Vehicle model."""

    list_display = ['__str__', 'owner', 'year', 'mileage', 'current_market_value', 'created_at']
    list_filter = ['make', 'year', 'owner']
    search_fields = ['make', 'model', 'vin', 'owner__username']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Vehicle Information', {
            'fields': ('owner', 'make', 'model', 'year', 'trim', 'vin')
        }),
        ('Financial', {
            'fields': ('purchase_price', 'current_market_value')
        }),
        ('Metadata', {
            'fields': ('mileage', 'created_at')
        }),
    )


@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    """Admin for ServiceRecord model."""

    list_display = ['vehicle', 'date', 'vendor', 'category', 'total_cost', 'is_verified']
    list_filter = ['category', 'is_verified', 'date']
    search_fields = ['vehicle__make', 'vehicle__model', 'vendor', 'description']
    readonly_fields = ['ocr_raw_data']
    date_hierarchy = 'date'


@admin.register(Upgrade)
class UpgradeAdmin(admin.ModelAdmin):
    """Admin for Upgrade model."""

    list_display = ['vehicle', 'part_name', 'brand', 'status', 'cost', 'installation_date']
    list_filter = ['status', 'brand']
    search_fields = ['vehicle__make', 'vehicle__model', 'part_name', 'brand']
    date_hierarchy = 'installation_date'


@admin.register(ConditionReport)
class ConditionReportAdmin(admin.ModelAdmin):
    """Admin for ConditionReport model."""

    list_display = ['vehicle', 'area', 'grade', 'value_adjustment', 'created_at']
    list_filter = ['area', 'created_at']
    search_fields = ['vehicle__make', 'vehicle__model', 'ai_feedback']
    readonly_fields = ['created_at']
```

### 12. .env.example

```bash
# Django Settings
DJANGO_ENVIRONMENT=local  # local, production, test
DJANGO_SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True

# Database Configuration
DB_NAME=my_garage
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# FastAPI Service URL
FASTAPI_BASE_URL=http://localhost:8001

# Email Configuration (for production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password

# AWS S3 (for production media storage)
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_STORAGE_BUCKET_NAME=
# AWS_S3_REGION_NAME=
```

### 13. .gitignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Django
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal
/media/
/staticfiles/

# Environment
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
logs/*.log

# Celery
celerybeat-schedule
celerybeat.pid

# Testing
.coverage
htmlcov/
.pytest_cache/
.tox/

# Pixi
.pixi/
```

---

## 🚀 Commands to Get Project Running

### 1. Initial Setup

```bash
# Navigate to project root
cd /home/zaigner77/projects/zaigner/my_garage

# Create .env file from example
cp .env.example .env

# Edit .env with your configuration
nano .env
```

### 2. Database Setup

```bash
# Create PostgreSQL database (if not exists)
createdb my_garage

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load sample data (optional)
python manage.py loaddata django_apps/my_garage/fixtures/sample_data.yaml
```

### 3. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 4. Run Development Server

```bash
# Django server
python manage.py runserver

# Celery worker (in separate terminal)
celery -A config.celery_app worker -l info

# FastAPI service (in separate terminal, if using)
cd fastapi_services
uvicorn main:app --reload --port 8001
```

### 5. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=django_apps.my_garage

# Run specific test file
pytest django_apps/my_garage/tests/test_models.py
```

---

## 📦 Additional Dependencies Needed

Update `pyproject.toml` to include:

```toml
[project]
dependencies = [
    "django>=5.2,<5.3",
    "djangorestframework>=3.14,<4.0",
    "django-cors-headers>=4.0,<5.0",
    "django-environ>=0.11,<1.0",
    "psycopg2-binary>=2.9,<3.0",
    "pillow>=10.0,<11.0",
    "celery>=5.3,<6.0",
    "redis>=5.0,<6.0",
    "requests>=2.31,<3.0",
    "pydantic>=2.0,<3.0",

    # Optional but recommended
    "django-debug-toolbar>=4.2,<5.0",  # Development only
    "pytest>=7.4,<8.0",
    "pytest-django>=4.5,<5.0",
    "pytest-cov>=4.1,<5.0",
    "factory-boy>=3.3,<4.0",  # For test factories
    "faker>=19.0,<20.0",  # For fake data
]
```

---

## ✅ Final Checklist Before First Run

- [ ] All required files created
- [ ] `.env` file configured
- [ ] PostgreSQL database created
- [ ] Redis server running (for Celery)
- [ ] Migrations created and applied
- [ ] Superuser created
- [ ] Static files collected
- [ ] All dependencies installed

---

## 🎯 Quick Start Command Sequence

```bash
# 1. Setup
cd /home/zaigner77/projects/zaigner/my_garage
cp .env.example .env

# 2. Database
createdb my_garage
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# 3. Static files
python manage.py collectstatic --noinput

# 4. Run
python manage.py runserver
```

Visit: http://localhost:8000
Admin: http://localhost:8000/admin
API: http://localhost:8000/api/
