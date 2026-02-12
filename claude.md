# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

My Garage is a comprehensive asset management and valuation platform designed for collectors and enthusiasts. It helps users track their assets as financial investments, manage service history, plan upgrades, and understand market values through AI-powered tools and real-time market intelligence.

**Core Features:**
- **Vehicles** - Automotive asset tracking with AI-powered valuations
- **Timepieces** - "Horology Salon" for fine watch collections
- **Dynamic Collections** - User-defined collection types (Wine, Art, Books, Bicycles, etc.)
  - Custom field schemas
  - Service record tracking
  - Project/upgrade management with Kanban boards
  - Relationship mapping between items
- **Portfolio Dashboard** - Unified view of all assets with total valuation and recent acquisitions

**Tech Stack:** Django 5.2 LTS + FastAPI microservices + Celery + Redis + MongoDB + PostgreSQL

## Important Notes

1. **PYTHONPATH**: The project uses `src/` as the source root. This is configured in `pixi.toml` under `[activation]` and set automatically when using pixi. If running Python commands manually, set `PYTHONPATH=src`.

2. **Django Management**: Always use `pixi run manage <command>` or `python manage.py <command>` from the project root (where manage.py is located), not from within src/.

3. **URL Structure**: The application has three separate URL mounts:
   - `/garage/` - Vehicles (uses `my_garage:` namespace)
   - `/timepieces/` - Timepieces (uses `timepieces:` namespace)
   - `/collections/` - Dynamic collections system (uses `collections:` namespace)
   - All share the same Django app but are mounted separately in `config/urls.py`

4. **Dynamic Collections**: User-defined collection types store their schema in a JSONField. Custom fields are prefixed with `custom_` in forms to avoid name conflicts. Each collection type can have different field definitions (text, number, date, file upload, relationships).

5. **FastAPI Service**: The FastAPI microservice must be running for MCP tools (VIN lookup, market valuation, AI image generation) to work from Django. Django communicates with FastAPI via `FASTAPI_BASE_URL`.

6. **MongoDB Directory**: MongoDB stores data in `.mongo_data/` (gitignored). Logs are in `logs/mongo.log`. The directory is created automatically by `start_app.sh`.

7. **API Keys**: External service integrations require API keys:
   - Marketcheck API for market valuation (MARKETCHECK_API_KEY in .env)
   - Google API key for Gemini image generation (configured in FastAPI MCP config)
   - NHTSA vPIC API is free and requires no key

8. **Pre-commit Hooks**: Once installed (`pixi run pre-commit-install`), Ruff will automatically lint and format code on every commit. Use `git commit --no-verify` to bypass if needed.

9. **Static Files**: For development, static files are served by Django. For production, run `python manage.py collectstatic` to gather static files into `staticfiles/`.

10. **Testing**: Tests use a separate test database. Settings are in `src/config/settings/test.py`. Pytest is configured with Django integration via pytest-django.

## Architecture Overview

### Project Structure
```
src/
├── config/              # Django project settings (base, local, production, test)
│   ├── urls.py          # Main URL router (mounts /garage/, /timepieces/ and /collections/)
│   └── views.py         # Home page view (Portfolio Dashboard)
├── my_garage/           # Main Django app (models, views, templates, API)
│   ├── models.py        # All data models (Vehicle, Timepiece, CollectionType, DynamicCollectionItem, etc.)
│   ├── views.py         # View logic for all features
│   ├── urls.py          # URL patterns for /garage/ (vehicles)
│   ├── timepiece_urls.py # URL patterns for /timepieces/ (timepieces)
│   ├── collection_urls.py  # URL patterns for /collections/ (dynamic collections)
│   ├── forms.py         # Form definitions including dynamic form generation
│   ├── admin.py         # Django admin configurations
│   ├── api/             # DRF API endpoints
│   ├── tasks.py         # Celery async tasks
│   ├── utils/           # Helper utilities
│   ├── templates/       # Django templates
│   │   ├── pages/
│   │   │   └── home.html                       # Portfolio Dashboard
│   │   └── my_garage/
│   │       ├── collection_types.html           # Collections dashboard
│   │       ├── collection_type_form.html       # Schema builder UI
│   │       ├── collection_list.html            # Items in a collection
│   │       ├── collection_item_detail.html     # Item detail page
│   │       ├── collection_upgrades_kanban.html # Kanban board for projects
│   │       ├── collection_service_record_form.html  # Service record form
│   │       ├── collection_upgrade_form.html    # Upgrade/project form
│   │       ├── all_services.html               # Unified service records view
│   │       ├── all_upgrades.html               # Unified upgrades view
│   │       └── partials/kanban_card.html       # Reusable kanban card
│   └── templatetags/    # Custom template filters
└── fastapi_services/    # Separate FastAPI microservice
    ├── mcp/             # MCP (Model Context Protocol) tools
    │   └── tools/       # Individual AI/external service integrations
    │       ├── vehicle_lookup.py    # NHTSA VIN decoding
    │       ├── market_valuation.py  # Marketcheck API integration
    │       ├── sales_stats.py       # Sales history and statistics
    │       ├── image_generation.py  # Google Gemini 2.5 Flash Image
    │       └── google_search.py     # Web search integration
    └── ocr/             # OCR service for receipt digitization

manage.py                # Django management script (in project root)
start_app.sh            # One-command startup for all services

# Documentation
DYNAMIC_COLLECTIONS_GUIDE.md  # Complete guide to dynamic collections
SERVICE_RECORDS_GUIDE.md       # Service record tracking documentation
UPGRADES_KANBAN_GUIDE.md       # Kanban board and project management guide
```

### Data Models

#### Original Models (Vehicles & Timepieces)
- **Vehicle** - Core asset tracking (VIN, make, model, purchase/current value)
- **Timepiece** - Watch collection tracking (movement, complications, provenance)
- **ServiceRecord** - Maintenance/repair/upgrade history with OCR support (for vehicles)
- **Upgrade** - Project tracking from wishlist to installation (for vehicles)
- **ConditionReport** - AI-powered condition grading with value impact
- **ValuationHistory** - Time-series market valuation data

#### Dynamic Collections Models (NEW)
- **CollectionType** - User-defined collection schema with JSONField for field definitions
  - Stores field schema: `{fields: [{name, type, label, required, help_text}]}`
  - Each user can create multiple collection types (Wine, Art, Books, etc.)
  - Supports custom icons and display preferences

- **DynamicCollectionItem** - Items in any collection
  - Standard fields: name, photo, purchase_price, current_market_value, notes
  - Custom fields stored in JSONField: `custom_fields = {field_name: value}`
  - Linked to CollectionType via foreign key

- **GenericServiceRecord** - Service records for any collection item
  - Categories: MAINTENANCE, REPAIR, UPGRADE, RESTORATION, APPRAISAL, INSURANCE, OTHER
  - Tracks vendor, date, cost, description, attachments
  - Works across all collection types

- **GenericUpgrade** - Upgrade/project tracking with Kanban workflow
  - Status workflow: WISHLIST → ORDERED → IN_PROGRESS → COMPLETED → CANCELLED
  - Automatic date tracking (ordered_date, completion_date)
  - Cost tracking and notes
  - Drag-and-drop status updates via AJAX

- **CollectionItemAttachment** - File attachments for any collection item
  - Supports multiple file types (documents, images, etc.)
  - Linked to DynamicCollectionItem

- **CollectionItemRelationship** - Item-to-item relationships
  - Links items across or within collections
  - Relationship types: INSPIRED_BY, PART_OF_SET, UPGRADED_FROM, etc.

### Service Architecture
The platform runs as a **multi-service architecture**:
- **Django (port 8000)** - Main web application and REST API
- **FastAPI (port 8001)** - AI/compute microservice for MCP tools
- **Celery Worker** - Async task processing (OCR, market data fetching)
- **Celery Beat** - Scheduled tasks (periodic valuation updates)
- **MongoDB** - Document storage for unstructured data
- **PostgreSQL** - Primary relational database (configured via .env)
- **Redis** - Celery broker and result backend

All services are orchestrated via **pixi** tasks and can be started together with `pixi run start-app`.

## Common Development Commands

### Initial Setup
```bash
# Install dependencies using pixi
pixi install

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys and database credentials

# Install pre-commit hooks
pixi run pre-commit-install

# Run migrations
pixi run migrate
```

### Running the Application

**Option 1: Start all services at once (recommended)**
```bash
pixi run start-app
# This starts MongoDB, Django, Celery Worker, Celery Beat, and FastAPI
# Press Ctrl+C to stop all services
```

**Option 2: Start services individually**
```bash
# Terminal 1: Start MongoDB
pixi run mongo

# Terminal 2: Start Django dev server
pixi run server

# Terminal 3: Start Celery worker
pixi run worker

# Terminal 4: Start Celery beat scheduler
pixi run beat

# Terminal 5: Start FastAPI microservice
pixi run fastapi

# To stop MongoDB
pixi run mongo-stop
```

### Development Workflow
```bash
# Create new migrations after model changes
pixi run makemigrations

# Apply migrations
pixi run migrate

# Django shell
pixi run shell

# Run tests
pixi run test

# Linting and formatting
pixi run lint          # Check code quality
pixi run format        # Auto-format code

# Django management commands
pixi run manage <command>  # Run any Django management command
```

### Key URLs

#### Main Application
- **Home Page:** http://localhost:8000
- **Django Admin:** http://localhost:8000/admin

#### Garage (Vehicles)
- **Dashboard:** http://localhost:8000/garage/
- **Vehicles:** http://localhost:8000/garage/view/

#### Timepieces (Horology Salon)
- **Timepieces:** http://localhost:8000/timepieces/

#### Dynamic Collections
- **Collections Dashboard:** http://localhost:8000/collections/
- **Create Collection Type:** http://localhost:8000/collections/create/
- **View Collection Items:** http://localhost:8000/collections/<slug>/items/
- **Kanban Board:** http://localhost:8000/collections/<slug>/upgrades/kanban/
- **All Services:** http://localhost:8000/collections/all-services/
- **All Upgrades:** http://localhost:8000/collections/all-upgrades/

#### FastAPI Microservice
- **API Base:** http://localhost:8001
- **API Docs:** http://localhost:8001/docs

## Environment Configuration

Required environment variables (see `.env.example`):
- **Django:** `DJANGO_SECRET_KEY`, `DJANGO_ENVIRONMENT`, `DEBUG`
- **Database:** `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- **Redis:** `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- **FastAPI:** `FASTAPI_BASE_URL` (for Django → FastAPI communication)
- **External APIs:** `MARKETCHECK_API_KEY`, Google API key for Gemini (in code config)

## Code Quality Standards

This project uses:
- **Ruff** for linting and formatting (88 char line length, Python 3.12)
- **Pre-commit hooks** that auto-run on git commit
- **isort** for import sorting (integrated into Ruff)
- Linting rules: pycodestyle (E/W), pyflakes (F), isort (I), flake8-comprehensions (C), flake8-bugbear (B)

Before committing, ensure:
```bash
pixi run lint     # No errors
pixi run format   # Code is formatted
pixi run test     # Tests pass
```

## Dynamic Collections System

The dynamic collections feature allows users to create custom collection types with user-defined schemas, enabling tracking of any asset type (Wine, Art, Books, Bicycles, etc.) beyond the built-in Vehicle and Timepiece modules.

### How It Works

1. **Schema Builder** (`collection_type_form.html`)
   - User-facing interface to define collection fields
   - JavaScript-based field editor with live preview
   - Field types: text, number, date, file upload, relationship
   - Schema stored as JSON in CollectionType.field_schema

2. **Dynamic Form Generation** (`forms.py`)
   - Forms are generated at runtime from the schema
   - Custom fields prefixed with `custom_` to avoid conflicts
   - Automatic validation based on field types and constraints
   - Data stored in DynamicCollectionItem.custom_fields JSON

3. **Service Records** (GenericServiceRecord)
   - Unified service tracking across ALL collection types
   - Dark "race deck" themed form matching vehicle service UI
   - Categories: Maintenance, Repair, Upgrade, Restoration, Appraisal, Insurance
   - View all services across collections at `/collections/all-services/`

4. **Project/Upgrade Management** (GenericUpgrade)
   - Kanban workflow: Wishlist → Ordered → In Progress → Completed → Cancelled
   - Drag-and-drop status updates via AJAX
   - Automatic date tracking (ordered_date, completion_date)
   - Cost tracking and notes
   - Visual Kanban board at `/collections/<slug>/upgrades/kanban/`

5. **URL Namespace Separation**
   - Collections use `collections:` namespace (mounted at `/collections/`)
   - Vehicles use `my_garage:` namespace (mounted at `/garage/`)
   - Timepieces use `timepieces:` namespace (mounted at `/timepieces/`)
   - All defined in same app but mounted separately in `config/urls.py`

### Key Design Patterns

- **Hybrid Model**: Standard Django models + JSONField for extensibility
- **Owner Isolation**: All queries filtered by `request.user` for security
- **Template Inheritance**: Reusable components (`partials/kanban_card.html`)
- **AJAX Updates**: Kanban board updates without page reload
- **Form Generation**: Dynamic field creation from JSON schema
- **Unified Dashboard**: Home page aggregates data from all asset types (Vehicles, Timepieces, Collections)

### Documentation Files

- `DYNAMIC_COLLECTIONS_GUIDE.md` - Complete system overview with examples
- `SERVICE_RECORDS_GUIDE.md` - Service tracking documentation
- `UPGRADES_KANBAN_GUIDE.md` - Kanban board usage and features

### Key Features & Integrations

### MCP Tools (FastAPI Microservice)
The FastAPI service at `src/fastapi_services/mcp/` provides AI and external service integrations:
- **vehicle_lookup** - NHTSA vPIC API for VIN decoding
- **market_valuation** - Marketcheck API for vehicle valuations
- **sales_stats** - Marketcheck sales statistics and history by VIN
- **image_generation** - Google Gemini 2.5 Flash Image for AI-generated visuals
- **google_search** - Web search for market research

### UI/UX Design Philosophy

#### Vehicles (Garage Module)
- **Professional Garage Aesthetic** - Dark mode with race deck flooring pattern
- **Dynamic Typography** - Manufacturer-specific fonts (Michroma for Porsche, Orbitron for Toyota, etc.)
- **Immersive Experience** - Spotlight effects, 3D perspective, cabinet-style data containers
- **Color Scheme** - Red accents for service records

#### Timepieces (Horology Salon)
- **Luxury Aesthetic** - Dark blue/gold luxury theme
- **Premium Feel** - Elegant typography and refined styling

#### Dynamic Collections
- **Service Records** - Dark race deck theme with red accents (matches vehicle aesthetic)
- **Upgrade/Projects** - Dark race deck theme with purple accents
- **Kanban Board** - Clean, modern light theme with color-coded columns
  - Gray (Wishlist), Blue (Ordered), Yellow (In Progress), Green (Completed), Red (Cancelled)
- **Schema Builder** - Functional UI with JavaScript field editor

#### Home Page
- **"The Collection"** - Luxury vault aesthetic with Pinyon Script font
- **Deep midnight theme** - Gold accents, elegant serif typography
- **Portfolio dashboard** - Clean cards showcasing collection categories
- **Recent Acquisitions** - Unified feed of latest items across all categories

## Database & Settings Structure

### Django Settings
Located in `src/config/settings/`:
- `base.py` - Common settings for all environments
- `local.py` - Development settings (default, uses SQLite or local PostgreSQL)
- `production.py` - Production settings
- `test.py` - Test settings

Set environment via `DJANGO_ENVIRONMENT` in `.env` (default: `local`)

### Multiple Databases
- **PostgreSQL** - Primary relational database (Vehicle, Timepiece, ServiceRecord, etc.)
- **MongoDB** - Document storage (configured for unstructured data)
- **SQLite** - Fallback for local development if PostgreSQL not configured

## Working with Dynamic Collections

### Creating a New Collection Type
1. Navigate to http://localhost:8000/collections/create/
2. Define basic info: name, slug, icon, description
3. Add custom fields using the JavaScript schema builder
4. Field types available: text, number, date, file, relationship
5. Schema is saved as JSON and forms are generated dynamically

### Adding Items to Collections
- Forms are generated at runtime from the collection's field schema
- Standard fields (name, photo, price) are always available
- Custom fields appear based on the schema definition
- Data is stored in `custom_fields` JSONField

### Service Records
- Use `GenericServiceRecord` model (linked to `DynamicCollectionItem`)
- Access via `/collections/<slug>/items/<id>/add-service/`
- Matches vehicle service UI (dark race deck theme)
- View all services across collections at `/collections/all-services/`

### Kanban Projects
- Each collection has its own Kanban board at `/collections/<slug>/upgrades/kanban/`
- Drag-and-drop updates status via AJAX to `/collections/api/upgrade/<id>/update-status/`
- Status changes automatically set dates (ordered_date, completion_date)
- Color-coded cards show item, brand, cost, dates, and notes indicator

### Important Patterns

**When modifying collection schemas:**
- Schema changes don't require migrations (stored in JSON)
- Existing items' custom_fields may need migration if field names change
- Forms are regenerated on each request from current schema

**When adding new views:**
- Always filter by `owner=request.user` for security
- Use `select_related()` for foreign keys to optimize queries
- Collections use `collections:` namespace, vehicles use `my_garage:`

**Template structure:**
- Most collection templates extend `base.html` (root templates directory)
- Some forms extend `my_garage/base.html` for consistent garage styling
- Use `{% url 'collections:view_name' %}` for collection URLs
- Use `{% url 'my_garage:view_name' %}` for vehicle URLs
- Use `{% url 'timepieces:view_name' %}` for timepiece URLs

### Troubleshooting

**NoReverseMatch errors:**
- Check if using correct namespace (`collections:` vs `my_garage:` vs `timepieces:`)
- Verify URL pattern name matches in urls.py
- Common issue: `vehicle_list` should be `garage_view`

**Custom fields not showing:**
- Verify field is in collection_type.field_schema JSON
- Check field name prefix (should have `custom_` in form)
- Ensure form is regenerating with correct collection_type

**Kanban drag-and-drop not working:**
- Check JavaScript console for errors
- Verify CSRF token is present
- Ensure API endpoint is accessible at `/collections/api/upgrade/<id>/update-status/`

**AttributeError in Home View:**
- When sorting items from different models (Vehicle, Timepiece, DynamicCollectionItem), ensure you handle different timestamp field names (e.g., `created_at` vs `purchase_date`). Use a helper function like `get_sort_date` to normalize.
