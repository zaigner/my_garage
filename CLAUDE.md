# CLAUDE.md — my_garage

Engineering reference for Claude Code. Covers architecture, conventions, data models, service contracts, and operational runbooks.

---

## 1. PROJECT OVERVIEW

**my_garage** is a Django 5.2 LTS + FastAPI personal asset management platform for vehicles, timepieces, and user-defined dynamic collections. It features AI-powered enrichment (market valuation, VIN decoding, OCR receipt parsing, image generation), a Model Context Protocol (MCP) server for Claude Code integration, and a RAG knowledge layer backed by MongoDB.

**Runtime stack:**

| Layer | Technology | Port |
|---|---|---|
| Web app | Django 5.2 LTS | 8000 |
| AI/MCP services | FastAPI + Uvicorn | 8001 |
| Task queue | Celery + Redis | — |
| Task scheduler | Celery Beat | — |
| Primary DB | PostgreSQL (SQLite in dev) | 5432 |
| Vector / trace store | MongoDB 6.x | 27017 |
| Cache / broker | Redis | 6379 |

---

## 2. REPOSITORY LAYOUT

```
my_garage/
├── src/
│   ├── config/                     # Django project config
│   │   ├── settings/
│   │   │   ├── base.py             # Shared settings
│   │   │   ├── local.py            # Dev overrides (SQLite, eager Celery)
│   │   │   ├── test.py             # Test overrides (in-memory SQLite, fast hasher)
│   │   │   └── production.py       # Production overrides
│   │   ├── celery_app.py           # Celery application factory
│   │   ├── api_router.py           # Centralized DRF URL routing
│   │   └── urls.py                 # Root URL configuration
│   ├── my_garage/                  # Primary Django application
│   │   ├── models.py               # All ORM models
│   │   ├── views.py                # Django views (non-API)
│   │   ├── urls.py                 # Vehicle URL patterns
│   │   ├── timepiece_urls.py       # Timepiece URL patterns
│   │   ├── collection_urls.py      # Collection URL patterns
│   │   ├── forms.py                # ModelForms
│   │   ├── admin.py                # Admin registrations
│   │   ├── tasks.py                # Celery tasks
│   │   ├── api/
│   │   │   ├── selectors.py        # Read-only ORM queries
│   │   │   ├── services.py         # Business logic + external API calls
│   │   │   ├── serializers.py      # DRF serializers
│   │   │   └── views.py            # DRF ViewSets
│   │   ├── services/
│   │   │   ├── context_service.py  # AI context assembly (RAG + structured data)
│   │   │   └── context_models.py   # Pydantic models for context output
│   │   ├── skills/
│   │   │   └── theme_generator.py  # AI-powered collection schema/UI generation
│   │   ├── utils/
│   │   │   ├── mongo.py            # MongoDB connection helper
│   │   │   ├── chunker.py          # Markdown chunker for RAG indexing
│   │   │   ├── prompt_renderer.py  # Jinja2 template renderer
│   │   │   └── tracing.py          # AI call instrumentation
│   │   ├── prompts/
│   │   │   ├── vehicle_valuation.j2
│   │   │   ├── service_record_analysis.j2
│   │   │   ├── condition_assessment.j2
│   │   │   └── collection_item_description.j2
│   │   └── management/commands/
│   │       ├── build_knowledge_index.py   # Build RAG index from markdown docs
│   │       ├── refresh_bmad_context.py    # Update live portfolio stats
│   │       └── migrate_vehicle_upgrades.py
│   └── fastapi_services/           # FastAPI application (port 8001)
│       ├── main.py                 # App factory + lifespan + route mounting
│       ├── mcp/
│       │   ├── server.py           # FastMCP server instance + tool registration
│       │   ├── main.py             # Legacy REST dispatcher (backward compat)
│       │   ├── config.py           # Pydantic Settings + API key validation
│       │   └── tools/
│       │       ├── vehicle_lookup.py
│       │       ├── market_valuation.py
│       │       ├── sales_stats.py
│       │       ├── watch_valuation.py
│       │       ├── google_search.py
│       │       └── image_generation.py
│       └── ocr/
│           └── main.py             # OCR router (pytesseract + receipt parser)
├── tests/
│   ├── conftest.py
│   ├── unit/                       # Pure unit tests (no I/O)
│   ├── functional/                 # Django test client (views, models)
│   ├── fastapi/                    # FastAPI TestClient tests
│   └── eval/                       # MCP tool + RAG quality evals
├── docs/
│   ├── IMPLEMENTATION_PLAN.md      # Phase-by-phase AI harness build plan
│   ├── SERVICE_RECORDS_GUIDE.md
│   ├── UPGRADES_KANBAN_GUIDE.md
│   └── UX-enhancement.md
├── templates/                      # Django HTML templates
├── static/                         # Static assets (CSS, JS)
├── media/                          # User-uploaded files
├── logs/                           # Runtime logs (git-ignored)
├── _bmad/                          # BMAD context + memory files
├── manage.py
├── start_app.sh                    # Dev launcher (all services)
├── pyproject.toml                  # Python package + tool config
├── pixi.toml                       # Environment + task runner
└── pixi.lock
```

---

## 3. DEPENDENCY MANAGEMENT

Package management uses **pixi** (conda-based). Do not use pip directly.

```bash
pixi install          # Install all dependencies
pixi add <package>    # Add a new dependency
```

### Runtime Dependencies (pyproject.toml)

| Package | Version | Purpose |
|---|---|---|
| `django` | >=5.2,<5.3 | Web framework (LTS) |
| `djangorestframework` | latest | REST API layer |
| `django-cors-headers` | latest | CORS middleware |
| `django-celery-beat` | latest | DB-backed Celery scheduler |
| `fastapi` | >=0.104 | AI/MCP microservice |
| `uvicorn[standard]` | >=0.24 | ASGI server |
| `pydantic` | >=2.0 | Data validation (v2 only) |
| `psycopg2-binary` | latest | PostgreSQL adapter |
| `celery` | >=5.3 | Task queue |
| `redis` | >=5.0 | Celery broker + result backend |
| `pymongo` | latest | MongoDB client |
| `google-generativeai` | latest | Gemini API (embeddings + image gen) |
| `mcp` | >=1.0 | Model Context Protocol SDK |
| `pillow` | >=10.0 | Image processing |
| `pytesseract` | >=0.3 | OCR (requires tesseract binary) |
| `beautifulsoup4` | >=4.12 | HTML parsing for image scraping |
| `jinja2` | latest | Prompt template rendering |
| `python-dotenv` | latest | `.env` file loading |
| `requests` | >=2.31 | HTTP client for external APIs |

### Dev Dependencies

| Package | Purpose |
|---|---|
| `pytest` + `pytest-django` | Test runner |
| `pytest-cov` | Coverage |
| `factory-boy` + `faker` | Test fixture factories |
| `ruff` | Linter + formatter |
| `pre-commit` | Git hooks |

### pixi Tasks

```bash
pixi run server           # Django dev server (localhost:8000)
pixi run fastapi          # FastAPI + MCP server (localhost:8001)
pixi run worker           # Celery worker
pixi run beat             # Celery Beat scheduler
pixi run migrate          # Apply database migrations
pixi run manage <cmd>     # Django management commands
pixi run mongo            # Start local MongoDB
pixi run pytest           # Run all tests
pixi run refresh-context  # Refresh BMAD portfolio context
pixi run start-app        # starts all services
```

**All tasks set `PYTHONPATH=src` automatically. Never run `python` directly — use `pixi run`.**

---

## 4. CONFIGURATION

### Settings Module

Django settings are split by environment. The default is `config.settings.local`.

Override via `DJANGO_SETTINGS_MODULE` environment variable.

**base.py — Shared across all environments:**

- `BASE_DIR` resolves to project root (parent of `src/`)
- Secrets loaded from `.env` via `python-dotenv`
- Installed apps: standard Django + `rest_framework`, `corsheaders`, `django_celery_beat`, `my_garage`
- `LOGIN_REDIRECT_URL = /garage/`, `LOGOUT_REDIRECT_URL = /accounts/login/`

**REST Framework:**
- `DEFAULT_AUTHENTICATION_CLASSES`: `SessionAuthentication`
- `DEFAULT_PERMISSION_CLASSES`: `IsAuthenticated`
- `DEFAULT_PAGINATION_CLASS`: `PageNumberPagination`, page_size=20

**local.py — Development:**
- `DEBUG = True`, SQLite (`db.sqlite3`)
- `CORS_ALLOW_ALL_ORIGINS = True`
- `CELERY_TASK_ALWAYS_EAGER = True` (synchronous task execution)
- Console email backend

**test.py — Pytest:**
- In-memory SQLite, `TEST_RUNNER` disables migrations
- `PASSWORD_HASHERS`: MD5 (fast)
- `CELERY_TASK_ALWAYS_EAGER = True`

### Environment Variables

All secrets go in `.env` (git-ignored). See `.env.example` for the full template.

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | Django secret key |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | Prod only | SQLite | PostgreSQL config |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Celery broker |
| `MONGO_URI` | Yes | `mongodb://localhost:27017/` | MongoDB connection |
| `MONGO_DB_NAME` | No | `my_garage_docs` | MongoDB database name |
| `FASTAPI_BASE_URL` | No | `http://localhost:8001` | Internal FastAPI URL |
| `GOOGLE_API_KEY` | For AI features | — | Gemini embeddings + image gen |
| `MARKETCHECK_API_KEY` | For valuations | — | Vehicle market data |
| `WATCHCHARTS_API_KEY` | Planned | — | Watch valuations (not yet live) |

### Celery Configuration (config/celery_app.py)

- App name: `my_garage`
- Autodiscovers tasks from `INSTALLED_APPS`
- Serializer: JSON (no pickle)
- Timezone: UTC

**Celery Beat Schedule:**

| Task | Schedule | Purpose |
|---|---|---|
| `task_bulk_valuation_refresh` | Monday 3:00 AM | Refresh all vehicle market values |
| `task_refresh_bmad_context` | Daily midnight | Update portfolio stats in context file |

---

## 5. DATA MODELS

All models live in `src/my_garage/models.py`.

### Vehicle

Primary asset model for automobiles.

| Field | Type | Notes |
|---|---|---|
| `owner` | FK → User | Cascade delete |
| `make`, `model`, `year`, `trim` | CharField / IntegerField | Core identity |
| `vin` | CharField(17) | Optional, blank=True |
| `license_plate` | CharField | Optional |
| `transmission` | CharField | Optional |
| `exterior_color`, `interior_color` | CharField | Used for image gen + valuation |
| `purchase_price` | DecimalField | Optional |
| `purchase_date` | DateField | Optional |
| `current_market_value` | DecimalField | Updated by valuation tasks |
| `mileage` | IntegerField | Optional |
| `features` | JSONField | Decoded VIN features (NHTSA) |
| `specs` | JSONField | Additional decoded specs |
| `photo` | ImageField | Upload to `media/vehicles/` |
| `notes` | TextField | Optional |
| `created_at` | DateTimeField | auto_now_add |

GenericRelation: `projects` → `GenericUpgrade`

### Timepiece

Fine watches and horology.

| Field | Type | Notes |
|---|---|---|
| `owner` | FK → User | Cascade delete |
| `brand`, `model`, `reference_number`, `serial_number` | CharField | Identity |
| `year` | IntegerField | Optional |
| `movement_type` | CharField | Choices: Automatic, Manual, Quartz, Spring Drive |
| `case_material`, `dial_color`, `complications` | CharField | Spec fields |
| `has_box`, `has_papers` | BooleanField | Completeness (affects valuation) |
| `condition_grade` | CharField | Choices: Mint, Excellent, Very Good, Good, Fair |
| `purchase_price`, `purchase_date` | Decimal / Date | Financial |
| `current_market_value` | DecimalField | Updated by valuation tasks |
| `photo` | ImageField | Upload to `media/timepieces/` |
| `notes` | TextField | Optional |

GenericRelation: `projects` → `GenericUpgrade`

### ValuationHistory

Immutable audit trail for vehicle valuations.

| Field | Type | Notes |
|---|---|---|
| `vehicle` | FK → Vehicle | Cascade delete |
| `date` | DateField | Valuation date |
| `value` | DecimalField | Estimated value |
| `raw_data` | JSONField | Full API response |

### ServiceRecord

Vehicle maintenance history.

| Field | Type | Notes |
|---|---|---|
| `vehicle` | FK → Vehicle | Cascade delete |
| `date` | DateField | Service date |
| `vendor` | CharField | Shop / provider |
| `description` | TextField | Work performed |
| `category` | CharField | Choices: MAINTENANCE, REPAIR, UPGRADE |
| `total_cost` | DecimalField | Optional |
| `receipt_image` | ImageField | Optional, triggers OCR pipeline |
| `ocr_raw_data` | JSONField | Parsed receipt data |
| `is_verified` | BooleanField | Set true after OCR + human review |

### ConditionReport

AI-graded photo assessments.

| Field | Type | Notes |
|---|---|---|
| `vehicle` | FK → Vehicle | Cascade delete |
| `area` | CharField | Choices: EXTERIOR, INTERIOR, ENGINE, WHEELS |
| `photo` | ImageField | Area photo |
| `grade` | FloatField | 1.0–10.0 scale |
| `ai_feedback` | TextField | AI-generated description |
| `value_adjustment` | DecimalField | Estimated impact on market value |

### Upgrade

Vehicle project / modification tracker.

| Field | Type | Notes |
|---|---|---|
| `vehicle` | FK → Vehicle | Cascade delete |
| `part_name`, `brand`, `part_number` | CharField | Part identity |
| `status` | CharField | Choices: WISHLIST, ORDERED, INSTALLED |
| `cost` | DecimalField | Optional |
| `installation_date` | DateField | Optional |
| `notes` | TextField | Optional |

### CollectionType

User-defined collection schema. One row per collection category (e.g., "Wine Cellar", "Art Collection").

| Field | Type | Notes |
|---|---|---|
| `owner` | FK → User | Cascade delete |
| `name` | CharField | Display name |
| `slug` | SlugField | Auto-generated from name, unique per owner |
| `icon`, `description` | CharField / TextField | UI metadata |
| `field_schema` | JSONField | Custom field definitions (name, type, required, etc.) |
| `list_display_fields` | JSONField | Which fields to show in list view |
| `ui_theme_html` | TextField | AI-generated Tailwind + Alpine.js component |
| `is_active` | BooleanField | Soft delete |
| `created_at`, `updated_at` | DateTimeField | Timestamps |

### DynamicCollectionItem

An instance within a CollectionType (e.g., a specific bottle of wine).

| Field | Type | Notes |
|---|---|---|
| `collection_type` | FK → CollectionType | Cascade delete |
| `owner` | FK → User | Cascade delete |
| `name` | CharField | Item name |
| `purchase_price`, `purchase_date` | Decimal / Date | Financial |
| `current_market_value` | DecimalField | Optional |
| `photo` | ImageField | Optional |
| `notes` | TextField | Optional |
| `custom_fields` | JSONField | Schema-driven values |
| `created_at`, `updated_at` | DateTimeField | Timestamps |

Indexes: `(collection_type, owner)`, `(owner, -created_at)`
Property: `equity = current_market_value - purchase_price`

### GenericServiceRecord

Service records for any collection item.

| Field | Type | Notes |
|---|---|---|
| `item` | FK → DynamicCollectionItem | Cascade delete |
| `date`, `vendor`, `description` | Standard fields | Service details |
| `category` | CharField | MAINTENANCE / REPAIR / UPGRADE / RESTORATION / APPRAISAL / OTHER |
| `total_cost` | DecimalField | Optional |
| `receipt_image` | ImageField | Optional |
| `ocr_raw_data` | JSONField | Parsed receipt |
| `is_verified` | BooleanField | Human-verified flag |

Index: `(item, -date)`

### GenericUpgrade

Modifications for any asset type via GenericForeignKey.

| Field | Type | Notes |
|---|---|---|
| `content_type` + `object_id` | GenericForeignKey | Links to any model |
| `name`, `brand`, `part_number` | CharField | Part identity |
| `status` | CharField | WISHLIST / ORDERED / IN_PROGRESS / COMPLETED / CANCELLED |
| `cost` | DecimalField | Optional |
| `ordered_date`, `completion_date` | DateField | Timeline |
| `notes` | TextField | Optional |

### CollectionItemAttachment

Files / documents associated with any collection item.

| Field | Type | Notes |
|---|---|---|
| `item` | FK → DynamicCollectionItem | Cascade delete |
| `file` | FileField | Upload to `media/attachments/` |
| `file_type` | CharField | RECEIPT / CERTIFICATE / APPRAISAL / MANUAL / PHOTO / OTHER |
| `title`, `description` | CharField / TextField | Metadata |
| `uploaded_at` | DateTimeField | auto_now_add |
| `uploader` | FK → User | Optional |

### CollectionItemRelationship

Cross-collection item links.

| Field | Type | Notes |
|---|---|---|
| `from_item`, `to_item` | FK → DynamicCollectionItem | Cascade delete |
| `relationship_type` | CharField | PAIRED_WITH / PART_OF / INSPIRED_BY / RELATED_TO / CUSTOM |
| `custom_label` | CharField | Used when type=CUSTOM |
| `notes` | TextField | Optional |
| `created_at` | DateTimeField | auto_now_add |
| `creator` | FK → User | Optional |

Unique constraint: `(from_item, to_item, relationship_type)`

---

## 6. APPLICATION LAYER (src/my_garage/api/)

### Architecture: Selector / Service / Serializer

```
HTTP Request
    ↓
DRF ViewSet (api/views.py)
    ↓
Serializer (api/serializers.py)     ← validates + shapes I/O
    ↓
Service (api/services.py)           ← business logic, external API calls
    ↓
Selector (api/selectors.py)         ← read-only ORM queries
    ↓
Model / DB
```

Views never call ORM directly. Services call selectors for reads, ORM for writes.

### Selectors (api/selectors.py)

Read-only query functions. Return ORM querysets or dicts.

| Function | Returns |
|---|---|
| `vehicle_get_build_summary(vehicle_id, user)` | Full vehicle context dict (specs, financials, history) |
| `vehicle_list_service_records(vehicle)` | ServiceRecord QS with OCR data |
| `vehicle_list_upgrades(vehicle)` | Upgrade QS by status |
| `vehicle_list_wishlist_items(vehicle)` | Wishlist-only upgrades |
| `global_search(query, user)` | Cross-model results (vehicles, timepieces, collections) |

### Services (api/services.py)

Business logic and external API integration. Raise `VehicleServiceError` on failure.

| Function | External Call | Side Effect |
|---|---|---|
| `vehicle_enrich_from_vin(vehicle)` | NHTSA vPIC | Updates `vehicle.features`, `vehicle.specs` |
| `vehicle_fetch_stock_photo(vehicle)` | Google Gemini / Google Images | Updates `vehicle.photo` |
| `vehicle_update_market_valuation(vehicle)` | MCP `search_market_listings` | Creates `ValuationHistory`, updates `vehicle.current_market_value` |
| `service_record_process_ocr_data(record)` | FastAPI `/ocr/parse-receipt` | Updates `record.ocr_raw_data`, sets `record.is_verified=True` |
| `service_record_create_from_ocr(vehicle, image)` | ↑ | Creates `ServiceRecord`, runs OCR |

---

## 7. CELERY TASKS (src/my_garage/tasks.py)

All tasks use `bind=True`, `max_retries=5`, `default_retry_delay=60`, `autoretry_for=(Exception,)` with exponential backoff.

| Task | Trigger | Action |
|---|---|---|
| `task_process_receipt_ocr(record_id)` | Upload receipt | OCR + parse, update ServiceRecord |
| `task_update_market_valuation(vehicle_id)` | Manual or Beat | Valuation API → ValuationHistory |
| `task_enrich_vehicle_data(vehicle_id)` | Manual or post-create | VIN decode → Vehicle.features / specs |
| `task_refresh_vehicle_photo(vehicle_id)` | Manual | Force re-fetch stock photo |
| `task_refresh_bmad_context()` | Beat (daily midnight) | `refresh_bmad_context` management command |
| `task_bulk_valuation_refresh()` | Beat (Monday 3 AM) | Queue `task_update_market_valuation` for all Vehicles |

**Views trigger tasks via `.delay(id)` — never call service functions synchronously from views for external APIs.**

---

## 8. CONTEXT SERVICE (src/my_garage/services/context_service.py)

Single entry point for assembling AI-ready context. Used by prompts, MCP tools, and skill generators.

```python
from my_garage.services.context_service import ContextService

ctx = ContextService()
vehicle_context   = ctx.get_vehicle_context(vehicle_id, user)      # → VehicleContext
timepiece_context = ctx.get_timepiece_context(timepiece_id, user)  # → TimepieceContext
item_context      = ctx.get_collection_item_context(item_id, user) # → CollectionItemContext
portfolio         = ctx.get_portfolio_summary(user)                 # → PortfolioSummary
docs              = ctx.retrieve_relevant_docs(query, k=5)         # → list[str]
```

**Context models** (`services/context_models.py`) are Pydantic v2 models. All serialize to `dict` for template injection.

**RAG retrieval** (`retrieve_relevant_docs`) queries MongoDB `knowledge_chunks` via cosine similarity in pure Python. No Atlas Vector Search required.

---

## 9. PROMPT SYSTEM (src/my_garage/prompts/ + utils/prompt_renderer.py)

Prompts are Jinja2 templates (`.j2`). Rendered via `PromptRenderer` (thread-safe, cached).

```python
from my_garage.utils.prompt_renderer import PromptRenderer

renderer = PromptRenderer()
prompt = renderer.render("vehicle_valuation.j2", context=vehicle_context.dict())
```

**Available templates:**

| Template | Context model | Purpose |
|---|---|---|
| `vehicle_valuation.j2` | VehicleContext | Market value estimation prompt |
| `service_record_analysis.j2` | ServiceRecord data | Receipt / service data parsing |
| `condition_assessment.j2` | ConditionReport data | Photo-based condition grading |
| `collection_item_description.j2` | CollectionItemContext | Item summary generation |

---

## 10. AI TRACING (src/my_garage/utils/tracing.py)

Instruments AI calls and writes to MongoDB `ai_traces` collection asynchronously (non-blocking).

```python
from my_garage.utils.tracing import trace_ai_call

@trace_ai_call(tool_name="vehicle_valuation")
async def call_valuation_api(vehicle_context):
    ...
```

**AITrace fields:** `task_id`, `timestamp`, `tool_name`, `context_summary`, `model`, `tokens`, `duration_ms`, `success`, `error`

**TTL:** 30-day auto-expiry index on `ai_traces` collection.

---

## 11. FASTAPI SERVICES (src/fastapi_services/)

### Application (main.py)

- **Lifespan handler** — logs which MCP tools are available/unavailable at startup
- **Mounts:**
  - `/mcp/` — Legacy REST dispatcher (Django service layer calls here)
  - `/ocr/` — OCR router
  - `/mcp-sdk/` — Real MCP server (Claude Code connects here)

### MCP Server (mcp/server.py)

Uses `mcp.server.fastmcp.FastMCP`. Each tool is decorated with `@mcp_server.tool()`.

**Registered Tools:**

#### `lookup_vehicle_details`
- **Input:** `vin: str`, `model_year: Optional[int]`
- **API:** NHTSA vPIC (free, no key)
- **Output:** make, model, year, engine type, body style, all decoded specs
- **Failure mode:** Returns error dict if VIN not found

#### `search_market_listings`
- **Input:** make, model, year, trim, mileage, exterior_color, interior_color
- **API:** Marketcheck (`MARKETCHECK_API_KEY` required)
- **Output:** List of comparable listings with price, mileage, dealer, photo URL
- **Fallback:** Relaxes filters progressively if zero results

#### `get_sales_stats`
- **Input:** year, make, model, trim, zip_code, radius
- **API:** Marketcheck
- **Output:** Sold vehicle statistics (count, avg price, price range)

#### `get_sales_history_by_vin`
- **Input:** `vin: str`
- **API:** Marketcheck
- **Output:** Historical sale events for this VIN (date, price, dealer)

#### `get_watch_valuation`
- **Input:** brand, model, reference_number, year, condition_grade, has_box, has_papers
- **API:** Mock (WatchCharts integration planned)
- **Output:** `estimated_value`, `currency`, `confidence`, `source`
- **Logic:** Brand multipliers + condition adjustment + completeness bonus

#### `generate_vehicle_image`
- **Input:** `prompt: str`, `negative_prompt: Optional[str]`
- **API:** Google Gemini 2.5 Flash Image (`GOOGLE_API_KEY` required)
- **Output:** Base64-encoded JPEG

#### `search_google_images`
- **Input:** `query: str`
- **API:** Google Images (HTML scraping via BeautifulSoup)
- **Output:** Up to 5 image URLs
- **Filters:** Strips icons, base64 URIs, relative paths

### MCP Config (mcp/config.py)

Pydantic Settings v2. Reads from `.env`.

- `available_tools` property → list of tool names with valid API keys
- `unavailable_tools` property → list of tools missing keys
- `log_startup_status()` — warns if keys missing at startup

### OCR Service (ocr/main.py)

**POST `/ocr/extract-text`** — raw pytesseract extraction from uploaded image

**POST `/ocr/parse-receipt`** — structured extraction

Pipeline:
1. `preprocess_image()` — grayscale + contrast enhancement
2. `pytesseract.image_to_string()`
3. `parse_receipt_data()`:
   - **Vendor:** first non-empty, non-numeric line (heuristic)
   - **Date:** regex for multiple formats (MM/DD/YYYY, YYYY-MM-DD, "Jan 15 2024", etc.)
   - **Line items:** lines containing prices, filtered against exclusion list (Total, Tax, Payment, etc.)
   - **Total:** line containing "TOTAL" keyword; falls back to max price found
4. Returns: `{vendor, date, total_cost, line_items, description}` (never raises — returns error dict on failure)

---

## 12. RAG KNOWLEDGE SYSTEM

**Storage:** MongoDB collection `knowledge_chunks`

**Schema per chunk:**
```json
{
  "content": "...",
  "source": "docs/IMPLEMENTATION_PLAN.md",
  "embedding": [3072-dim float array],
  "created_at": "..."
}
```

**Embedding model:** Google `gemini-embedding-001` (3072 dimensions)

**Similarity:** Cosine similarity in pure Python (no Atlas Vector Search dependency)

**Indexing:** `build_knowledge_index` management command
- Scans: `docs/`, `.specify/specs/`, project root for `.md` files
- Chunks by `##` headers, max 2000 chars per chunk
- Embeds + upserts to MongoDB

**Retrieval:** `ContextService.retrieve_relevant_docs(query, k=5)` → `list[str]`

**Rebuild after documentation changes:**
```bash
pixi run manage build_knowledge_index
```

---

## 13. SKILLS (src/my_garage/skills/)

### CollectionThemeGenerator (skills/theme_generator.py)

Generates collection type schema and UI using Google Gemini 2.5 Flash.

```python
generator = CollectionThemeGenerator()
schema = generator.generate_schema(name, description)
ui_html = generator.generate_ui_component(name, description, feedback=None)
```

- `generate_schema()` → JSON field schema for `CollectionType.field_schema`
- `generate_ui_component()` → Tailwind + Alpine.js HTML for `CollectionType.ui_theme_html`
- Both methods have safe fallbacks if the API call fails

---

## 14. URL STRUCTURE

| Prefix | Namespace | Handler |
|---|---|---|
| `/` | — | Home view |
| `/admin/` | — | Django admin |
| `/accounts/` | — | Django auth + custom register |
| `/api/` | — | DRF router (api_router.py) |
| `/garage/` | `my_garage` | Vehicle management |
| `/timepieces/` | `timepieces` | Timepiece management |
| `/collections/` | `collections` | Dynamic collections |

---

## 15. TESTING

### Structure

| Suite | Location | Scope |
|---|---|---|
| Unit | `tests/unit/` | Pure Python — utils, context service, config, tracing, chunker, prompt renderer |
| Functional | `tests/functional/` | Django test client — views, forms, model logic (vehicles, timepieces, collections) |
| FastAPI | `tests/fastapi/` | `TestClient` — MCP server endpoints, OCR routes |
| Eval | `tests/eval/` | MCP tool quality, RAG retrieval relevance, context assembly |

### Running Tests

```bash
pixi run pytest                    # All tests
pytest tests/unit/                 # Unit only
pytest tests/functional/           # Functional only
pytest tests/fastapi/              # FastAPI only
pytest -k "valuation"              # Keyword filter
pytest --cov=src --cov-report=term # With coverage
```

### Settings for Tests

`config.settings.test`:
- In-memory SQLite, no migrations
- MD5 password hasher
- Eager Celery (synchronous)
- `FASTAPI_BASE_URL = http://testserver`

### Conventions

- Every new feature must have a unit test alongside it
- Functional tests use `factory-boy` for fixture creation — no raw `Model.objects.create` in tests
- MCP tools are tested in `eval/` against real API responses (can be slow — tag with `@pytest.mark.eval` to skip in CI)
- Do not mock the database in functional tests — use Django's test runner with transaction rollback

---

## 16. DEVELOPMENT CONVENTIONS

### Language & Frameworks
- **Python 3.12** — no older syntax
- **Pydantic v2** — use `model_config = SettingsConfigDict(...)`, not `class Config`
- **Django 5.2** — use `path()` not `url()`, type annotations on views where practical
- **DRF** — ViewSets for API endpoints, not function-based API views

### Code Style
- **Ruff** for linting and formatting (configured in `pyproject.toml`)
- Run `ruff check . --fix && ruff format .` before committing
- Pre-commit hooks enforce this automatically

### Database Access
- Views must not call ORM directly — use selectors or services
- Selectors are read-only; services own writes
- Migrations must be generated and committed for every model change: `pixi run manage makemigrations`

### Async / Background Work
- Any call to an external API (Marketcheck, Google, NHTSA, FastAPI) must go through a Celery task
- Never call `service_record_process_ocr_data()` or `vehicle_update_market_valuation()` synchronously from a view
- Exception: management commands may call services directly

### Adding a New MCP Tool
1. Create `src/fastapi_services/mcp/tools/<tool_name>.py` with input Pydantic model + implementation function
2. Register with `@mcp_server.tool()` in `mcp/server.py`
3. Add API key to `mcp/config.py` if required
4. Add to `available_tools` / `unavailable_tools` properties
5. Write eval test in `tests/eval/`

### Adding a New Asset Type (e.g., Art)
1. Decide: use `DynamicCollectionItem` + `CollectionType` (preferred) or new dedicated model
2. If dedicated model: add to `models.py`, create migrations, register in admin, add selectors/services, create views + templates + urls
3. Add `GenericRelation` for upgrades if applicable
4. Update `ContextService` with a new `get_<type>_context()` method
5. Add prompt template to `prompts/`
6. Write functional tests

---

## 17. EXTERNAL API INTEGRATIONS

| API | Auth | Key Var | Fallback |
|---|---|---|---|
| NHTSA vPIC | None | — | None — essential for VIN decode |
| Marketcheck | API key header | `MARKETCHECK_API_KEY` | Returns error response |
| Google Gemini (embeddings) | API key | `GOOGLE_API_KEY` | Skip embedding |
| Google Gemini (image gen) | API key | `GOOGLE_API_KEY` | Return error |
| Google Images | None | — | HTML scraping (fragile) |
| WatchCharts | API key (planned) | `WATCHCHARTS_API_KEY` | Mock multiplier logic |

**Check `MCP_CONFIG.available_tools` at startup to know which tools are live.**

---

## 18. DATABASE LAYOUT

### PostgreSQL (Primary)

All Django model tables. Key indexes:

- `DynamicCollectionItem`: `(collection_type, owner)`, `(owner, -created_at)`
- `GenericServiceRecord`: `(item, -date)`
- `CollectionItemRelationship`: unique on `(from_item, to_item, relationship_type)`

### MongoDB (my_garage_docs)

| Collection | Purpose | TTL |
|---|---|---|
| `knowledge_chunks` | RAG documents + embeddings | None (permanent) |
| `ai_traces` | AI call instrumentation logs | 30 days (TTL index) |

---

## 19. OPERATIONAL RUNBOOKS

### Start All Services (Development)

```bash
bash start_app.sh
# Starts: MongoDB, Django (8000), FastAPI (8001), Celery worker, Celery Beat
# Ctrl+C gracefully shuts everything down
```

### Rebuild RAG Index After Docs Change

```bash
pixi run manage build_knowledge_index
# Optional flags:
#   --dry-run          Preview chunks without writing
#   --source-dir PATH  Override source directory
#   --max-chars N      Override chunk size (default: 2000)
```

### Refresh Portfolio Context (BMAD)

```bash
pixi run refresh-context
# Updates _bmad/_memory/project-context.md with live portfolio stats
# Only replaces the "## Current Project State" section
```

### Apply Database Migrations

```bash
pixi run migrate
pixi run manage makemigrations   # After model changes
```

### Create Superuser

```bash
pixi run manage createsuperuser
```

### Django Shell

```bash
pixi run manage shell
```

### Check Which MCP Tools Are Available

```bash
pixi run fastapi
# Check startup logs for "✓ Available tools:" and "✗ Unavailable tools:"
```

---

## 20. SECURITY NOTES

- `.env` is git-ignored — never commit API keys or credentials
- `.env.example` shows all required keys without values
- CORS: `ALLOW_ALL_ORIGINS=True` in development only — production must whitelist origins explicitly
- Default DRF permission: `IsAuthenticated` — all API endpoints require login
- Public views (home, register, login) are `login_required` exempt
- Receipt images uploaded to `media/` — served only to authenticated owners
- MongoDB traces contain context summaries but not raw user data

---

## 21. SESSION RETROSPECTIVE PROTOCOL

**At the end of every working session, run a retrospective and update memory.**

This is not optional — it is how agent interactions improve over time.

### When to Run

- When the user signals the session is wrapping up
- When the user explicitly asks for a retrospective
- After any session where something broke, required multiple fix attempts, or where an assumption turned out to be wrong

### What to Capture

1. **What went well** — approaches that worked, decisions that held up, patterns worth repeating
2. **What went wrong** — bugs introduced, wrong assumptions, wasted iterations
3. **What to change** — concrete rule changes for future sessions

### Output: Two Artifacts

**1. Session log** — Written to `memory/retros/YYYY-MM-DD.md`:

```markdown
# Retrospective — YYYY-MM-DD
**Session focus:** <one line summary>

## Went Well
- <bullet per item>

## Went Wrong
- <bullet per item — include root cause, not just symptom>

## Rule Changes
- <concrete, actionable rules>
```

**2. Memory updates** — For every "went wrong" item that represents a repeatable mistake, save or update a memory file under:

`/home/zaigner77/.claude/projects/-home-zaigner77-projects-zaigner/memory/`

Session logs: `.../memory/retros/YYYY-MM-DD.md`
