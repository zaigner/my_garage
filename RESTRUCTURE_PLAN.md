# My Garage - Django Project Restructuring Plan

## Current Structure Analysis

**Current State:**
```
my_garage/
├── config/
│   ├── urls.py           # Main project URLs (incomplete)
│   └── api_router.py     # FastAPI router
├── templates/
│   └── my_garage/
│       └── dashboard.html
├── models.py
├── selectors.py
├── services.py
├── views.py
├── tasks.py
├── urls.py              # App URLs
├── pyproject.toml
└── design.md
```

**Issues with Current Structure:**
1. Missing Django project root structure
2. App code mixed with project configuration
3. No separation between project-level and app-level code
4. Missing essential Django files (manage.py, settings/, wsgi.py, asgi.py)
5. No migrations directory
6. No proper app initialization (__init__.py, apps.py)
7. Config directory contains app-specific FastAPI code (should be in app/api/)

---

## Target Structure (Following django-kedro Pattern)

```
my_garage_project/                    # Project root
│
├── manage.py                         # Django management script
├── pyproject.toml                    # Project dependencies
├── README.md                         # Project documentation
├── .env                              # Environment variables (not in git)
├── .env.example                      # Example environment variables
├── .gitignore                        # Git ignore patterns
│
├── config/                           # Project-level configuration
│   ├── __init__.py                   # Celery app initialization
│   ├── settings/                     # Settings module
│   │   ├── __init__.py
│   │   ├── base.py                   # Base settings
│   │   ├── local.py                  # Development settings
│   │   ├── production.py             # Production settings
│   │   └── test.py                   # Test settings
│   ├── urls.py                       # Main URL routing
│   ├── wsgi.py                       # WSGI entry point
│   ├── asgi.py                       # ASGI entry point
│   ├── api_router.py                 # DRF API router (not FastAPI)
│   └── celery_app.py                 # Celery configuration
│
├── django_apps/                      # All Django apps
│   └── my_garage/                    # Main app
│       ├── __init__.py
│       ├── apps.py                   # AppConfig
│       ├── models.py                 # Database models
│       ├── admin.py                  # Django admin
│       ├── urls.py                   # App URL routing
│       ├── views.py                  # Web views
│       ├── forms.py                  # Django forms
│       ├── managers.py               # Custom model managers (if needed)
│       ├── tasks.py                  # Celery tasks
│       │
│       ├── api/                      # API & Services (Service Layer)
│       │   ├── __init__.py
│       │   ├── views.py              # DRF ViewSets
│       │   ├── serializers.py        # DRF Serializers
│       │   ├── selectors.py          # Data retrieval (read operations)
│       │   ├── services.py           # Business logic (write operations)
│       │   ├── ocr_service.py        # OCR integration service
│       │   ├── valuation_service.py  # Market valuation service
│       │   └── mcp_client.py         # MCP client wrapper
│       │
│       ├── migrations/               # Database migrations
│       │   └── __init__.py
│       │
│       ├── templates/                # HTML templates
│       │   └── my_garage/
│       │       ├── dashboard.html
│       │       ├── vehicle_detail.html
│       │       └── base.html
│       │
│       ├── static/                   # Static files
│       │   └── my_garage/
│       │       ├── css/
│       │       ├── js/
│       │       └── images/
│       │
│       ├── tests/                    # App tests
│       │   ├── __init__.py
│       │   ├── test_models.py
│       │   ├── test_views.py
│       │   ├── test_selectors.py
│       │   ├── test_services.py
│       │   └── factories.py          # Test data factories
│       │
│       └── fixtures/                 # Sample data
│           └── sample.yaml
│
├── fastapi_services/                 # Separate FastAPI app (optional)
│   ├── __init__.py
│   ├── main.py                       # FastAPI app
│   ├── ocr/                          # OCR endpoints
│   │   ├── __init__.py
│   │   └── routes.py
│   └── mcp/                          # MCP endpoints
│       ├── __init__.py
│       └── routes.py
│
├── static/                           # Project-level static files
│   └── .gitkeep
│
├── media/                            # User-uploaded files
│   ├── receipts/
│   └── condition_checks/
│
└── logs/                             # Application logs
    └── .gitkeep
```

---

## Key Differences from Current Structure

### 1. Project Root vs App Root
- **Before**: Everything in one directory
- **After**: Clear separation between project config (`config/`) and apps (`django_apps/my_garage/`)

### 2. Service Layer Organization
- **Before**: `services.py` and `selectors.py` at app root
- **After**: `api/services.py` and `api/selectors.py` grouped with other API components

### 3. Settings Structure
- **Before**: No settings file
- **After**: Settings module with environment-specific configurations

### 4. FastAPI Separation
- **Before**: Mixed with Django in `config/api_router.py`
- **After**: Separate `fastapi_services/` directory (optional) or integrated via DRF

---

## Architecture Pattern Comparison

### django-kedro Pattern Applied to my_garage

| Component | django-kedro | my_garage Equivalent |
|-----------|--------------|---------------------|
| Main App | `django_kedro/` | `my_garage/` |
| Models | `models.py` (7 models) | `models.py` (4 models: Vehicle, ServiceRecord, Upgrade, ConditionReport) |
| API ViewSets | `api/views.py` (6 ViewSets) | `api/views.py` (VehicleViewSet, ServiceRecordViewSet, etc.) |
| Serializers | `api/serializers.py` | `api/serializers.py` |
| External Services | `api/git_tools.py`, `api/kedro_runner.py` | `api/ocr_service.py`, `api/valuation_service.py`, `api/mcp_client.py` |
| Data Retrieval | Embedded in ViewSets | `api/selectors.py` (existing pattern preserved) |
| Business Logic | `api/views.py` methods | `api/services.py` (existing pattern preserved) |
| Async Tasks | `tasks.py` (Celery) | `tasks.py` (Celery for OCR, market updates) |
| Web Views | `views.py` | `views.py` (dashboard, vehicle detail) |

### Key Pattern: Service Layer in api/

Following django-kedro, we move service-related code into `api/`:

```
my_garage/
└── api/                          # Service Layer
    ├── views.py                  # API endpoints (DRF ViewSets)
    ├── serializers.py            # Data validation
    ├── selectors.py              # Read operations (like django-kedro queries)
    ├── services.py               # Write operations (like django-kedro actions)
    ├── ocr_service.py            # External OCR integration
    ├── valuation_service.py      # Market valuation logic
    └── mcp_client.py             # MCP protocol client
```

This mirrors django-kedro's pattern:
```
django_kedro/
└── api/
    ├── views.py                  # ViewSets
    ├── serializers.py            # Serializers
    ├── git_tools.py              # Git service
    ├── kedro_runner.py           # Kedro execution service
    └── git_interface.py          # Git abstraction
```

---

## Migration Strategy

### Phase 1: Create Project Structure (Non-Breaking)
1. Create `config/` directory at project root
2. Create `django_apps/` directory
3. Set up settings module in `config/settings/`
4. Create `manage.py`
5. Create WSGI/ASGI entry points

### Phase 2: Move App Code
1. Move current app code to `django_apps/my_garage/`
2. Create `api/` subdirectory
3. Move `selectors.py` → `api/selectors.py`
4. Move `services.py` → `api/services.py`
5. Create new service modules (`ocr_service.py`, `valuation_service.py`, `mcp_client.py`)
6. Create `apps.py` for AppConfig
7. Create `admin.py` for admin interface

### Phase 3: Create API Layer
1. Create `api/serializers.py` for DRF
2. Create `api/views.py` with ViewSets
3. Update `config/api_router.py` to use DRF router
4. Move FastAPI logic to separate service (optional)

### Phase 4: Testing & Configuration
1. Set up migrations directory
2. Create initial migrations
3. Set up test structure
4. Configure Celery
5. Set up static/media directories
6. Update `.gitignore`

---

## Benefits of This Structure

1. **Scalability**: Easy to add new apps (e.g., `django_apps/analytics/`)
2. **Separation of Concerns**: Project config separated from app logic
3. **Service Layer**: Business logic isolated in `api/` for testability
4. **Environment Management**: Different settings for dev/prod/test
5. **Standards Compliance**: Follows Django best practices and django-kedro pattern
6. **API-First**: Clear API layer with DRF ViewSets
7. **Maintainability**: Code organized by responsibility, not just file type

---

## Next Steps

1. Review and approve this restructuring plan
2. Decide on FastAPI integration strategy:
   - Option A: Separate FastAPI service (`fastapi_services/`)
   - Option B: Full DRF integration (replace FastAPI with DRF)
   - Option C: Hybrid (DRF for REST, FastAPI for heavy AI/OCR)
3. Proceed with Phase 1 implementation
4. Test each phase before moving to the next
