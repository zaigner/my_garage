# My Garage - Automotive Asset Management Platform

## Project Overview

My Garage is an automotive asset management and valuation platform designed for car enthusiasts. It helps users track their vehicles as financial assets, manage service history, plan upgrades, and understand their car's market value through AI-powered tools and real-time market intelligence.

**Current Status:** ✅ **Production-Ready Structure** - Fully restructured following django-kedro pattern, with working Django application, migrations applied, and admin interface ready to use.

## Core Features

1. **Digital Vehicle Vault**: Track vehicles with VIN decoding, purchase price, current market value, and comprehensive metadata
2. **Paperless Service Catalog**: AI-powered OCR for digitizing service receipts and categorizing maintenance/repairs/upgrades
3. **Upgrade Project Manager**: Track modifications from wishlist to installation with cost tracking
4. **Market Intelligence Engine**: Real-time market valuation using Web MCP to browse comparable listings
5. **Visual Condition Grading**: AI-powered condition assessment with value impact analysis

## Technology Stack

### Backend
- **Django 5.2 LTS** - Web framework
- **Django REST Framework 3.14+** - API framework (configured, not yet used)
- **Celery 5.3+** - Async task queue
- **Redis 5.0+** - Celery broker and result backend

### Database
- **Development:** SQLite3 (no setup required)
- **Production:** PostgreSQL 2.9+ (recommended)

### External Services
- **FastAPI 0.104+** - Separate microservice for compute-intensive AI/OCR tasks
- **Model Context Protocol (MCP)** - Web scraping for market data

### Development Tools
- **django-debug-toolbar** - Development debugging
- **django-cors-headers** - CORS handling
- **pytest** - Testing framework (optional dependency)

## Project Architecture

This project follows a **strict layered architecture** pattern inspired by django-kedro:

```
my_garage/
├── config/                          # Project Configuration
│   ├── settings/
│   │   ├── base.py                 # Shared settings
│   │   ├── local.py                # Development (SQLite, debug toolbar)
│   │   ├── production.py           # Production (PostgreSQL, security)
│   │   └── test.py                 # Testing (in-memory DB)
│   ├── urls.py                     # Main URL routing
│   ├── wsgi.py                     # WSGI entry point
│   ├── asgi.py                     # ASGI entry point
│   └── celery_app.py               # Celery configuration
│
├── django_apps/                     # Django Applications
│   └── my_garage/                  # Main App
│       ├── api/                    # Service Layer (django-kedro pattern)
│       │   ├── selectors.py        # Read operations (queries)
│       │   └── services.py         # Write operations (business logic)
│       ├── migrations/             # Database migrations
│       ├── templates/my_garage/    # HTML templates
│       ├── static/my_garage/       # App static files
│       ├── tests/                  # Unit tests
│       ├── models.py               # Database models
│       ├── views.py                # Web views
│       ├── admin.py                # Django admin
│       ├── forms.py                # Django forms
│       ├── tasks.py                # Celery tasks
│       ├── urls.py                 # App URLs
│       └── apps.py                 # App configuration
│
├── fastapi_services/                # FastAPI Microservice
│   ├── ocr/                        # OCR endpoints (to be implemented)
│   └── mcp/                        # MCP endpoints (to be implemented)
│
├── templates/                       # Project-level templates
├── static/                          # Project-level static files
├── media/                           # User uploads
│   ├── receipts/
│   └── condition_checks/
├── logs/                            # Application logs
│
├── manage.py                        # Django CLI
├── pyproject.toml                   # Project configuration
├── .env                            # Environment variables (not in git)
└── db.sqlite3                      # Local database (not in git)
```

## Architecture Pattern: Service Layer in api/

Following the django-kedro pattern, business logic is organized in the `api/` subdirectory:

### api/selectors.py - Read Operations
- **Purpose**: Data retrieval and complex queries
- **Rules**:
  - Read-only operations (no mutations)
  - All aggregation at database level
  - Return QuerySets, model instances, or dictionaries
  - Use `Coalesce` to prevent None in aggregations

**Example Functions:**
```python
vehicle_get_build_summary(vehicle_id: int) -> Dict[str, Any]
vehicle_list_wishlist_items(vehicle: Vehicle) -> QuerySet[Upgrade]
vehicle_get_total_maintenance_cost(vehicle: Vehicle) -> Decimal
```

### api/services.py - Write Operations
- **Purpose**: Business logic, AI integrations, data mutations
- **Rules**:
  - Use `@transaction.atomic` for multi-record operations
  - Raise custom exceptions (e.g., `VehicleServiceError`)
  - Handle external API calls (FastAPI OCR, Web MCP)
  - Call selectors when needing to read data

**Example Functions:**
```python
vehicle_update_market_valuation(vehicle: Vehicle) -> Decimal
service_record_create_from_ocr(vehicle: Vehicle, receipt_image) -> ServiceRecord
service_record_process_ocr_data(record: ServiceRecord) -> bool
condition_report_add_ai_grade(...) -> ConditionReport
```

## Database Models

### Vehicle
Core asset representing a user's car with financial tracking.

**Key Fields:**
- `owner` (ForeignKey to User)
- `make`, `model`, `year`, `trim`, `vin`
- `purchase_price`, `current_market_value`
- `mileage`, `created_at`

### ServiceRecord
Stores service history with digitized document support.

**Key Fields:**
- `vehicle` (ForeignKey)
- `date`, `vendor`, `description`, `category`
- `total_cost`, `receipt_image`
- `ocr_raw_data` (JSONField - raw OCR output)
- `is_verified` (Boolean)

**Categories:** MAINTENANCE, REPAIR, UPGRADE

### Upgrade
Tracks ongoing and planned car modifications.

**Key Fields:**
- `vehicle` (ForeignKey)
- `part_name`, `brand`, `part_number`
- `status`, `cost`, `installation_date`, `notes`

**Status Flow:** WISHLIST → ORDERED → INSTALLED

### ConditionReport
AI-graded assessments of vehicle condition.

**Key Fields:**
- `vehicle` (ForeignKey)
- `area`, `photo`
- `grade` (1-10 scale), `ai_feedback`
- `value_adjustment`, `created_at`

**Areas:** EXTERIOR, INTERIOR, ENGINE, WHEELS

## Coding Conventions

### Naming Patterns

**Selectors (Read):**
- `{model}_get_{description}` - Get single item or aggregation
- `{model}_list_{description}` - Get QuerySet of items

**Services (Write):**
- `{model}_{action}_{description}` - Perform action
- Actions: `create`, `update`, `delete`, `process`, etc.

**Tasks (Async):**
- `task_{action}_{description}` - Background job

### Type Hints
- Always use type hints for parameters and return values
- Use `Optional[Type]` for nullable values
- Import from `typing` module

### Decimal Handling
- Use `Decimal` type for all financial calculations
- Never use floats for money
- Use `Coalesce` with `Decimal('0.00')` in aggregations

### Error Handling
- Create custom exceptions in services.py
- Use `@transaction.atomic` for multi-record operations
- Let views catch and convert exceptions to HTTP responses

## Development Workflow

### Initial Setup

```bash
# Clone and navigate to project
cd /home/zaigner77/projects/zaigner/my_garage

# Activate virtual environment
source .venv/bin/activate

# Install dependencies (already done)
pip install -e .

# Run migrations (already done)
python manage.py migrate

# Create superuser (already created: admin/admin)
python manage.py createsuperuser
```

### Running the Application

```bash
# Start Django development server
python manage.py runserver

# Start Celery worker (in another terminal)
celery -A config.celery_app worker -l info

# Start FastAPI service (when implemented)
cd fastapi_services
uvicorn main:app --reload --port 8001
```

### Accessing the Application

- **Home Page:** http://localhost:8000/
- **Admin Panel:** http://localhost:8000/admin/ (admin/admin)
- **My Garage:** http://localhost:8000/garage/
- **Debug Toolbar:** Available in DEBUG mode

### Adding New Features

1. **Update Models** (if needed)
   ```bash
   # Edit django_apps/my_garage/models.py
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Add Selectors** (`api/selectors.py`)
   - Create functions for data retrieval
   - Use Django ORM aggregations

3. **Add Services** (`api/services.py`)
   - Create functions for business logic
   - Use `@transaction.atomic` where needed

4. **Add Views** (`views.py`)
   - Call selectors for data
   - Call services for mutations
   - Keep views thin

5. **Add URLs** (`urls.py`)
   - Wire up new views

6. **Add Forms** (`forms.py`)
   - Create ModelForms for data entry

7. **Add Tests** (`tests/`)
   - Write unit tests for selectors
   - Write integration tests for services

## Integration Points

### FastAPI OCR Service
- **Base URL**: `http://localhost:8001` (configured in .env)
- **Endpoint**: `/ocr/process` (to be implemented)
- **Purpose**: Document OCR, receipt parsing
- **Called by**: `service_record_process_ocr_data()` in api/services.py

### Model Context Protocol (MCP)
- **Endpoint**: `{FASTAPI_BASE_URL}/mcp/execute` (to be implemented)
- **Tool**: `search_market_listings`
- **Purpose**: Web scraping for comparable vehicle listings
- **Called by**: `vehicle_update_market_valuation()` in api/services.py

## Financial Calculations

### Total Investment
```python
total_investment = (
    vehicle.purchase_price +
    sum(verified_service_records.total_cost) +
    sum(installed_upgrades.cost)
)
```

### Equity (Profit/Loss)
```python
equity = vehicle.current_market_value - total_investment
is_profitable = equity > 0
```

### Market Value Updates
- Triggered manually via admin or views
- Can be automated via Celery Beat (scheduled tasks)
- Queries comparable listings via Web MCP
- Calculates median price from results
- Updates atomically with transaction

## Admin Interface

The Django admin provides full CRUD functionality for all models:

### Vehicle Admin
- List display: vehicle details, owner, year, mileage, value
- Filters: make, year, owner
- Search: make, model, VIN, owner username
- Fieldsets: Vehicle Info, Financial, Metadata

### ServiceRecord Admin
- List display: vehicle, date, vendor, category, cost, verification status
- Filters: category, verification status, date
- Search: vehicle make/model, vendor
- Date hierarchy by service date
- Readonly: OCR raw data

### Upgrade Admin
- List display: vehicle, part, brand, status, cost, installation date
- Filters: status, brand
- Search: vehicle, part name, brand, part number
- Date hierarchy by installation date

### ConditionReport Admin
- List display: vehicle, area, grade, value adjustment, created date
- Filters: area, created date
- Search: vehicle, AI feedback
- Readonly: created date

## Testing Guidelines

- Write tests for selectors to verify query logic
- Write tests for services to verify business logic
- Mock external API calls (FastAPI, MCP)
- Use Django's TestCase for database tests
- Use TransactionTestCase for atomic operations
- Run tests: `pytest django_apps/my_garage/tests/`

## Environment Variables

Key environment variables in `.env`:

```bash
DJANGO_ENVIRONMENT=local          # local, production, test
DJANGO_SECRET_KEY=<secret>        # Change in production!
DEBUG=True                        # False in production

# Database (production)
DB_NAME=my_garage
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# FastAPI Service
FASTAPI_BASE_URL=http://localhost:8001
```

## Security Considerations

### Development
- DEBUG=True (shows detailed errors)
- SQLite database (easy setup)
- CORS allows all origins
- No HTTPS required

### Production
- DEBUG=False (never expose errors)
- PostgreSQL database (robust, scalable)
- CORS restricted to known origins
- HTTPS enforced (SECURE_SSL_REDIRECT=True)
- HSTS enabled (1 year)
- SECRET_KEY must be changed
- Session/CSRF cookies secured

## Common Patterns

### Reading Data (in views)
```python
from .api.selectors import vehicle_get_build_summary

def vehicle_detail(request, vehicle_id):
    summary = vehicle_get_build_summary(vehicle_id)
    return render(request, 'template.html', summary)
```

### Mutating Data (in views)
```python
from .api.services import vehicle_update_market_valuation, VehicleServiceError

def trigger_valuation_refresh(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id)
    try:
        new_value = vehicle_update_market_valuation(vehicle)
        messages.success(request, f"Updated to ${new_value}")
    except VehicleServiceError as e:
        messages.error(request, str(e))
    return redirect('my_garage:vehicle_detail', vehicle_id)
```

### Background Tasks
```python
from .tasks import task_update_market_valuation

# In view
task_update_market_valuation.delay(vehicle.id)
```

## Future Roadmap

### Immediate (Implemented)
- ✅ Django project structure
- ✅ Database models and migrations
- ✅ Django admin interface
- ✅ Service layer pattern
- ✅ Forms and basic views

### Short-term (To Implement)
- ⏳ FastAPI OCR service endpoints
- ⏳ FastAPI MCP integration endpoints
- ⏳ Dashboard templates and views
- ⏳ Celery tasks for background processing
- ⏳ API endpoints with DRF (optional)

### Mid-term
- VIN decoder integration
- PDF export for vehicle history
- Price tracking for wishlist parts
- Installation time tracking (DIY vs shop)
- Market alerts for similar vehicle sales

### Long-term
- Mod-adjusted valuation algorithms
- Computer vision for condition grading
- Mobile app (React Native or Flutter)
- Multi-user garage sharing
- Integration with car forums/communities

## Additional Resources

- **Design Documentation**: See `design.md` for detailed feature specifications
- **Restructuring Plan**: See `RESTRUCTURE_PLAN.md` for architecture decisions
- **Migration Guide**: See `MIGRATION_GUIDE.md` for step-by-step migration
- **Django Documentation**: https://docs.djangoproject.com/en/5.2/
- **Celery Documentation**: https://docs.celeryq.dev/
- **DRF Documentation**: https://www.django-rest-framework.org/

## Quick Reference

### Superuser Credentials
- **Username:** admin
- **Password:** admin
- **Email:** admin@mygarage.com

### Key Files to Edit
- **Models:** `django_apps/my_garage/models.py`
- **Selectors:** `django_apps/my_garage/api/selectors.py`
- **Services:** `django_apps/my_garage/api/services.py`
- **Views:** `django_apps/my_garage/api/views.py`
- **Tasks:** `django_apps/my_garage/tasks.py`
- **Admin:** `django_apps/my_garage/admin.py`
- **URLs:** `django_apps/my_garage/urls.py`

### Important Commands
```bash
# Development
python manage.py runserver
python manage.py shell
python manage.py dbshell

# Database
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations

# Admin
python manage.py createsuperuser
python manage.py changepassword <username>

# Static files
python manage.py collectstatic

# Testing
pytest
pytest --cov=django_apps.my_garage
python manage.py test

# Celery
celery -A config.celery_app worker -l info
celery -A config.celery_app beat
```

---

**Last Updated:** 2025-12-21
**Project Status:** ✅ Production-Ready Structure
**Django Version:** 5.2.9
**Python Version:** 3.12+
