# Step-by-Step Migration Guide
## Restructuring my_garage to Follow django-kedro Pattern

This guide will walk you through restructuring your my_garage Django app to follow the django-kedro pattern with proper project structure.

---

## 📋 Pre-Migration Checklist

- [ ] Backup your current code: `git commit -am "Pre-restructure backup"`
- [ ] Read `RESTRUCTURE_PLAN.md` to understand the target structure
- [ ] Read `FILES_CHECKLIST.md` to see all required files
- [ ] Ensure you have PostgreSQL and Redis installed
- [ ] Have a terminal and text editor ready

---

## 🚀 Phase 1: Create Project Infrastructure (30 minutes)

### Step 1.1: Create Directory Structure

```bash
cd /home/zaigner77/projects/zaigner/my_garage

# Create main directories
mkdir -p config/settings
mkdir -p django_apps
mkdir -p static
mkdir -p media/{receipts,condition_checks}
mkdir -p logs
mkdir -p templates/pages

# Create __init__.py files
touch config/__init__.py
touch config/settings/__init__.py
touch django_apps/__init__.py
```

### Step 1.2: Create manage.py

```bash
cat > manage.py << 'EOF'
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
EOF

chmod +x manage.py
```

### Step 1.3: Create Settings Files

**Create config/settings/base.py:**

```bash
cat > config/settings/base.py << 'EOF'
"""Base settings shared across all environments."""
import os
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-CHANGE-THIS-IN-PRODUCTION-12345')

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

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Media files
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
EOF
```

**Create config/settings/local.py:**

```bash
cat > config/settings/local.py << 'EOF'
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
EOF
```

**Create config/settings/__init__.py:**

```bash
cat > config/settings/__init__.py << 'EOF'
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
EOF
```

### Step 1.4: Create WSGI and ASGI Files

**Create config/wsgi.py:**

```bash
cat > config/wsgi.py << 'EOF'
"""WSGI config for my_garage project."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()
EOF
```

**Create config/asgi.py:**

```bash
cat > config/asgi.py << 'EOF'
"""ASGI config for my_garage project."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_asgi_application()
EOF
```

### Step 1.5: Create Celery Configuration

**Update config/__init__.py:**

```bash
cat > config/__init__.py << 'EOF'
"""Configuration package initialization."""
# This will make sure the Celery app is always imported when
# Django starts so that shared_task will use this app.
from .celery_app import app as celery_app

__all__ = ('celery_app',)
EOF
```

**Create config/celery_app.py:**

```bash
cat > config/celery_app.py << 'EOF'
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
EOF
```

### Step 1.6: Create Environment Files

**Create .env.example:**

```bash
cat > .env.example << 'EOF'
# Django Settings
DJANGO_ENVIRONMENT=local
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
EOF
```

**Create .env:**

```bash
cp .env.example .env
# Edit .env with your actual values if needed
```

### Step 1.7: Update .gitignore

```bash
cat >> .gitignore << 'EOF'

# Django
*.log
db.sqlite3
db.sqlite3-journal
/staticfiles/

# Environment
.env

# Logs
logs/*.log

# Celery
celerybeat-schedule
celerybeat.pid
EOF
```

---

## 🔄 Phase 2: Move App Code to django_apps (45 minutes)

### Step 2.1: Create App Directory Structure

```bash
# Create app directory structure
mkdir -p django_apps/my_garage/{api,migrations,templates/my_garage,static/my_garage/{css,js},tests,fixtures}

# Create __init__.py files
touch django_apps/my_garage/__init__.py
touch django_apps/my_garage/api/__init__.py
touch django_apps/my_garage/migrations/__init__.py
touch django_apps/my_garage/tests/__init__.py
```

### Step 2.2: Move Existing Files

```bash
# Move models.py
mv models.py django_apps/my_garage/models.py

# Move views.py
mv views.py django_apps/my_garage/views.py

# Move urls.py (app-level)
mv urls.py django_apps/my_garage/urls.py

# Move tasks.py
mv tasks.py django_apps/my_garage/tasks.py

# Move templates
mv templates/my_garage/* django_apps/my_garage/templates/my_garage/

# Move service files to api directory
mv selectors.py django_apps/my_garage/api/selectors.py
mv services.py django_apps/my_garage/api/services.py
```

### Step 2.3: Create apps.py

```bash
cat > django_apps/my_garage/apps.py << 'EOF'
"""App configuration for my_garage."""
from django.apps import AppConfig


class MyGarageConfig(AppConfig):
    """Configuration for the my_garage app."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_apps.my_garage'
    verbose_name = 'My Garage'

    def ready(self):
        """Import signal handlers when app is ready."""
        pass
EOF
```

### Step 2.4: Create admin.py

```bash
cat > django_apps/my_garage/admin.py << 'EOF'
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


@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    """Admin for ServiceRecord model."""

    list_display = ['vehicle', 'date', 'vendor', 'category', 'total_cost', 'is_verified']
    list_filter = ['category', 'is_verified', 'date']
    search_fields = ['vehicle__make', 'vehicle__model', 'vendor']
    date_hierarchy = 'date'


@admin.register(Upgrade)
class UpgradeAdmin(admin.ModelAdmin):
    """Admin for Upgrade model."""

    list_display = ['vehicle', 'part_name', 'brand', 'status', 'cost', 'installation_date']
    list_filter = ['status', 'brand']
    date_hierarchy = 'installation_date'


@admin.register(ConditionReport)
class ConditionReportAdmin(admin.ModelAdmin):
    """Admin for ConditionReport model."""

    list_display = ['vehicle', 'area', 'grade', 'value_adjustment', 'created_at']
    list_filter = ['area', 'created_at']
    readonly_fields = ['created_at']
EOF
```

### Step 2.5: Create forms.py

```bash
cat > django_apps/my_garage/forms.py << 'EOF'
"""Django forms for my_garage."""
from django import forms
from .models import Vehicle, ServiceRecord, Upgrade


class VehicleForm(forms.ModelForm):
    """Form for creating/updating vehicles."""

    class Meta:
        model = Vehicle
        fields = ['make', 'model', 'year', 'trim', 'vin', 'purchase_price', 'mileage']
        widgets = {
            'year': forms.NumberInput(attrs={'min': 1900, 'max': 2100}),
            'mileage': forms.NumberInput(attrs={'min': 0}),
        }


class ServiceRecordForm(forms.ModelForm):
    """Form for creating service records."""

    class Meta:
        model = ServiceRecord
        fields = ['date', 'vendor', 'description', 'category', 'total_cost', 'receipt_image']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class UpgradeForm(forms.ModelForm):
    """Form for creating upgrades."""

    class Meta:
        model = Upgrade
        fields = ['part_name', 'brand', 'part_number', 'status', 'cost', 'installation_date', 'notes']
        widgets = {
            'installation_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
EOF
```

### Step 2.6: Fix Import Paths

**Update django_apps/my_garage/views.py:**

```python
# Change any imports from:
# from .services import ...
# to:
from .api.services import ...

# Change any imports from:
# from .selectors import ...
# to:
from .api.selectors import ...
```

**Update django_apps/my_garage/tasks.py:**

```python
# Add at the top:
from config.celery_app import app as celery_app

# Change decorators from @app.task to @celery_app.task
# Change any model imports to:
from django_apps.my_garage.models import Vehicle, ServiceRecord
```

**Update django_apps/my_garage/api/services.py:**

```python
# Change model imports from:
# from .models import ...
# to:
from django_apps.my_garage.models import ...
```

**Update django_apps/my_garage/api/selectors.py:**

```python
# Change model imports from:
# from .models import ...
# to:
from django_apps.my_garage.models import ...
```

### Step 2.7: Fix Model Issue in models.py

```bash
# Edit django_apps/my_garage/models.py
# Line 10: Fix the typo
# Change: on_backend=models.CASCADE
# To: on_delete=models.CASCADE
```

---

## 🌐 Phase 3: Create API Layer with DRF (30 minutes)

### Step 3.1: Create Serializers

```bash
cat > django_apps/my_garage/api/serializers.py << 'EOF'
"""DRF Serializers for my_garage API."""
from rest_framework import serializers
from django_apps.my_garage.models import Vehicle, ServiceRecord, Upgrade, ConditionReport


class VehicleSerializer(serializers.ModelSerializer):
    """Serializer for Vehicle model."""

    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            'id', 'owner', 'owner_username', 'make', 'model', 'year', 'trim', 'vin',
            'purchase_price', 'current_market_value', 'mileage', 'created_at'
        ]
        read_only_fields = ['owner', 'created_at']


class ServiceRecordSerializer(serializers.ModelSerializer):
    """Serializer for ServiceRecord model."""

    vehicle_display = serializers.CharField(source='vehicle.__str__', read_only=True)

    class Meta:
        model = ServiceRecord
        fields = [
            'id', 'vehicle', 'vehicle_display', 'date', 'vendor', 'description',
            'category', 'total_cost', 'receipt_image', 'ocr_raw_data', 'is_verified'
        ]
        read_only_fields = ['ocr_raw_data']


class UpgradeSerializer(serializers.ModelSerializer):
    """Serializer for Upgrade model."""

    vehicle_display = serializers.CharField(source='vehicle.__str__', read_only=True)

    class Meta:
        model = Upgrade
        fields = [
            'id', 'vehicle', 'vehicle_display', 'part_name', 'brand', 'part_number',
            'status', 'cost', 'installation_date', 'notes'
        ]


class ConditionReportSerializer(serializers.ModelSerializer):
    """Serializer for ConditionReport model."""

    vehicle_display = serializers.CharField(source='vehicle.__str__', read_only=True)

    class Meta:
        model = ConditionReport
        fields = [
            'id', 'vehicle', 'vehicle_display', 'area', 'photo',
            'grade', 'ai_feedback', 'value_adjustment', 'created_at'
        ]
        read_only_fields = ['created_at']
EOF
```

### Step 3.2: Create API ViewSets

```bash
cat > django_apps/my_garage/api/views.py << 'EOF'
"""DRF ViewSets for my_garage API."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django_apps.my_garage.models import Vehicle, ServiceRecord, Upgrade, ConditionReport
from .serializers import (
    VehicleSerializer,
    ServiceRecordSerializer,
    UpgradeSerializer,
    ConditionReportSerializer,
)
from .services import vehicle_update_market_valuation
from .selectors import vehicle_get_build_summary


class VehicleViewSet(viewsets.ModelViewSet):
    """ViewSet for Vehicle CRUD operations."""

    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['make', 'model', 'year', 'owner']
    ordering_fields = '__all__'
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter to show only user's own vehicles."""
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """Set owner to current user on creation."""
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def refresh_valuation(self, request, pk=None):
        """Refresh market valuation for a vehicle."""
        vehicle = self.get_object()
        try:
            new_value = vehicle_update_market_valuation(vehicle)
            return Response({
                'current_market_value': str(new_value),
                'message': 'Valuation updated successfully'
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def build_summary(self, request, pk=None):
        """Get comprehensive build summary."""
        vehicle = self.get_object()
        summary = vehicle_get_build_summary(vehicle.id)
        # Convert Decimal to string for JSON
        summary_json = {k: str(v) if isinstance(v, type(summary['equity'])) else v
                       for k, v in summary.items() if k != 'vehicle'}
        return Response(summary_json)


class ServiceRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for ServiceRecord CRUD operations."""

    queryset = ServiceRecord.objects.all()
    serializer_class = ServiceRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['vehicle', 'category', 'is_verified']
    ordering = ['-date']

    def get_queryset(self):
        """Filter to show only records for user's vehicles."""
        return self.queryset.filter(vehicle__owner=self.request.user)


class UpgradeViewSet(viewsets.ModelViewSet):
    """ViewSet for Upgrade CRUD operations."""

    queryset = Upgrade.objects.all()
    serializer_class = UpgradeSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['vehicle', 'status']
    ordering = ['-installation_date']

    def get_queryset(self):
        """Filter to show only upgrades for user's vehicles."""
        return self.queryset.filter(vehicle__owner=self.request.user)


class ConditionReportViewSet(viewsets.ModelViewSet):
    """ViewSet for ConditionReport CRUD operations."""

    queryset = ConditionReport.objects.all()
    serializer_class = ConditionReportSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['vehicle', 'area']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter to show only reports for user's vehicles."""
        return self.queryset.filter(vehicle__owner=self.request.user)
EOF
```

### Step 3.3: Create API Router (Update)

```bash
cat > config/api_router.py << 'EOF'
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
EOF
```

### Step 3.4: Create Main URL Configuration

**Update config/urls.py:**

```bash
cat > config/urls.py << 'EOF'
"""Main URL Configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API
    path('api/', include('config.api_router')),

    # My Garage App
    path('garage/', include('django_apps.my_garage.urls', namespace='my_garage')),

    # Home
    path('', TemplateView.as_view(template_name='pages/home.html'), name='home'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
EOF
```

---

## ✅ Phase 4: Testing and Finalization (30 minutes)

### Step 4.1: Create Database and Run Migrations

```bash
# Create PostgreSQL database
createdb my_garage

# Create migrations
python manage.py makemigrations my_garage

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### Step 4.2: Test Basic Functionality

```bash
# Start development server
python manage.py runserver

# In another terminal, test API
curl http://localhost:8000/api/
curl http://localhost:8000/admin/

# Visit in browser:
# http://localhost:8000/admin/
# http://localhost:8000/api/
# http://localhost:8000/garage/
```

### Step 4.3: Create Basic Tests

```bash
cat > django_apps/my_garage/tests/test_models.py << 'EOF'
"""Tests for my_garage models."""
import pytest
from django.contrib.auth import get_user_model
from django_apps.my_garage.models import Vehicle

User = get_user_model()

@pytest.mark.django_db
def test_vehicle_creation():
    """Test vehicle creation."""
    user = User.objects.create_user(username='testuser', password='testpass')
    vehicle = Vehicle.objects.create(
        owner=user,
        make='Toyota',
        model='Supra',
        year=1998,
        purchase_price=35000.00
    )
    assert vehicle.id is not None
    assert str(vehicle) == '1998 Toyota Supra'
EOF
```

### Step 4.4: Run Tests

```bash
# Install pytest-django if not already
pip install pytest pytest-django

# Run tests
pytest django_apps/my_garage/tests/
```

### Step 4.5: Cleanup Old Files

```bash
# Remove old config directory (if it's different from new one)
# Only if you had a different structure before
# rm -rf old_config_if_exists

# Remove old templates directory (already moved)
rmdir templates/my_garage templates 2>/dev/null || true

# Commit changes
git add .
git commit -m "Restructure project following django-kedro pattern"
```

---

## 🎉 Post-Migration Verification Checklist

- [ ] Django server starts without errors: `python manage.py runserver`
- [ ] Admin panel accessible: http://localhost:8000/admin/
- [ ] API browsable: http://localhost:8000/api/
- [ ] Can create vehicle via admin
- [ ] Can access vehicle via API
- [ ] Migrations applied successfully
- [ ] No import errors in any Python files
- [ ] Static files serving correctly
- [ ] Media upload works
- [ ] Tests pass

---

## 🐛 Troubleshooting

### Issue: ImportError for models

**Solution:** Update import paths in all files:
```python
# Old
from .models import Vehicle

# New (from api/ directory)
from django_apps.my_garage.models import Vehicle
```

### Issue: Settings module not found

**Solution:** Ensure DJANGO_SETTINGS_MODULE is set:
```bash
export DJANGO_SETTINGS_MODULE=config.settings.local
```

### Issue: Migrations not found

**Solution:** Create migrations:
```bash
python manage.py makemigrations my_garage
python manage.py migrate
```

### Issue: Static files not loading

**Solution:** Collect static files:
```bash
python manage.py collectstatic --noinput
```

### Issue: Celery tasks not running

**Solution:** Start Celery worker:
```bash
celery -A config.celery_app worker -l info
```

---

## 📚 Next Steps After Migration

1. **Create sample data fixtures:**
   ```bash
   python manage.py dumpdata my_garage --indent=2 > django_apps/my_garage/fixtures/sample_data.json
   ```

2. **Set up CI/CD:**
   - Add GitHub Actions or similar
   - Configure automated testing
   - Set up deployment pipeline

3. **Enhance API:**
   - Add API documentation with drf-spectacular
   - Add filtering and search
   - Add pagination

4. **Add monitoring:**
   - Set up logging
   - Add Sentry for error tracking
   - Configure performance monitoring

5. **Security hardening:**
   - Change SECRET_KEY in production
   - Set up HTTPS
   - Configure ALLOWED_HOSTS
   - Enable CSRF protection

---

## 📞 Getting Help

If you encounter issues during migration:

1. Check the error message carefully
2. Verify all import paths are correct
3. Ensure all __init__.py files exist
4. Check that migrations are applied
5. Review the django-kedro project for reference: `/home/zaigner77/projects/repos/django-kedro`

---

## ✨ Success!

Once all phases are complete, you'll have a properly structured Django project following industry best practices and the django-kedro pattern!

Your project will be:
- ✅ Properly organized with clear separation of concerns
- ✅ Following Django best practices
- ✅ Scalable and maintainable
- ✅ Ready for production deployment
- ✅ Easy to test and debug
