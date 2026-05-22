# My Garage — Project Context

> This file is auto-refreshed by: `pixi run refresh-context`
> (management command: `refresh_bmad_context`)
> Static sections are edited manually. The `## Current Project State` section
> is overwritten on each refresh run.

---

## Platform Overview

**My Garage** is a personal asset management and valuation platform for collectors.
It tracks vehicles, timepieces (watches), and any user-defined collection type
(wine, art, bicycles, etc.) as financial investments.

**Core philosophy:** Every asset is an investment. Track acquisition cost, maintenance
spend, current market value, and equity — across all asset types in one portfolio.

---

## Architecture

| Layer | Technology | Purpose |
|---|---|---|
| Web app | Django 5.2 LTS | Models, views, admin, REST API |
| AI microservice | FastAPI (port 8001) | MCP tools, OCR, image generation |
| Async tasks | Celery + Redis | Valuations, OCR, scheduled jobs |
| Primary DB | PostgreSQL | All relational data |
| Document store | MongoDB | OCR docs, RAG knowledge chunks, AI traces |
| Cache/broker | Redis | Celery broker, task results |

### URL Structure
- `/garage/` — Vehicles (namespace: `my_garage:`)
- `/timepieces/` — Timepieces / Horology Salon (namespace: `timepieces:`)
- `/collections/` — Dynamic collections (namespace: `collections:`)
- `/admin/` — Django admin
- `http://localhost:8001/docs` — FastAPI OpenAPI docs
- `http://localhost:8001/mcp-sdk/` — Real MCP server (Claude Code integration)

---

## Data Models

### Core Models
| Model | Key Fields | Purpose |
|---|---|---|
| `Vehicle` | make, model, year, trim, vin, mileage, purchase_price, current_market_value, specs (JSON), features (JSON) | Automotive asset |
| `Timepiece` | brand, model, reference_number, complications (JSON), has_box, has_papers, condition_grade | Watch collection |
| `ServiceRecord` | vehicle, date, vendor, category, total_cost, receipt_image, ocr_raw_data | Vehicle maintenance |
| `Upgrade` | vehicle, part_name, status, cost | Legacy vehicle projects |
| `ValuationHistory` | vehicle, date, value, raw_data | Time-series valuations |
| `ConditionReport` | vehicle, area, grade, ai_feedback | AI condition grading |

### Dynamic Collection Models
| Model | Key Fields | Purpose |
|---|---|---|
| `CollectionType` | name, slug, owner, field_schema (JSON) | User-defined collection schema |
| `DynamicCollectionItem` | collection_type, name, purchase_price, current_market_value, custom_fields (JSON) | Item in any collection |
| `GenericServiceRecord` | item, date, vendor, category, total_cost | Service record for any item |
| `GenericUpgrade` | item OR generic FK, name, status, cost | Project tracking for any asset |
| `CollectionItemAttachment` | item, file, file_type | Documents/photos for items |
| `CollectionItemRelationship` | from_item, to_item, relationship_type | Item-to-item relationships |

### Status Workflows
- **GenericUpgrade**: WISHLIST → ORDERED → IN_PROGRESS → COMPLETED → CANCELLED
- **Upgrade (legacy)**: WISHLIST → ORDERED → INSTALLED

---

## AI & Context Engineering Layer

### MCP Tools (FastAPI microservice)
All tools registered as real MCP server at `/mcp-sdk/`. Claude Code connects natively.

| Tool | API | Key Required |
|---|---|---|
| `lookup_vehicle_details` | NHTSA vPIC | No (free) |
| `search_market_listings` | Marketcheck | Yes (`MARKETCHECK_API_KEY`) |
| `get_sales_stats` | Marketcheck | Yes (`MARKETCHECK_API_KEY`) |
| `get_sales_history_by_vin` | Marketcheck | Yes (`MARKETCHECK_API_KEY`) |
| `get_watch_valuation` | Mock (WatchCharts future) | No |
| `generate_vehicle_image` | Google Gemini 2.5 Flash | Yes (`GOOGLE_API_KEY`) |
| `search_google_images` | Google scraping | No |

### Context Service (`my_garage.services.ContextService`)
Single entry point for assembling typed AI context from the ORM:
- `get_vehicle_context(vehicle_id, user)` → `VehicleContext`
- `get_timepiece_context(timepiece_id, user)` → `TimepieceContext`
- `get_collection_item_context(item_id, user)` → `CollectionItemContext`
- `get_portfolio_summary(user)` → `PortfolioSummary`
- `retrieve_relevant_docs(query, k=5)` → `list[str]` (RAG)

### Prompt Templates (`src/my_garage/prompts/`)
Jinja2 `.j2` templates rendered via `PromptRenderer`:
- `vehicle_valuation.j2` — Market value assessment
- `service_record_analysis.j2` — Maintenance review
- `condition_assessment.j2` — Condition grading
- `collection_item_description.j2` — Portfolio description

### RAG Knowledge Index
- MongoDB collection: `knowledge_chunks`
- Embeddings: Google `text-embedding-004` (768 dimensions)
- Index: `knowledge_embedding_index` (cosine similarity)
- Rebuild: `pixi run manage build_knowledge_index`

### AI Trace Logging
- MongoDB collection: `ai_traces`
- TTL: 30 days
- Decorator: `@trace_ai_call` from `my_garage.utils.tracing`

---

## Development Commands

```bash
pixi run start-app          # Start all services (Django + FastAPI + Celery + MongoDB)
pixi run server             # Django only
pixi run fastapi            # FastAPI only
pixi run test               # Run all tests
pixi run lint               # Ruff lint check
pixi run format             # Ruff format
pixi run manage migrate     # Apply migrations
pixi run manage makemigrations  # Create migrations after model changes
pixi run manage build_knowledge_index  # Build/refresh RAG index
pixi run refresh-context    # Refresh this BMAD context file
```

---

## Code Conventions

- **PYTHONPATH**: Always `src/` — use `pixi run manage` or set `PYTHONPATH=src`
- **Owner isolation**: All ORM queries filter by `owner=request.user`
- **select_related**: Always use for FK traversal in selectors
- **Linting**: Ruff (88 char, Python 3.12), pre-commit hooks auto-run
- **Tests**: `pytest` with `--ds=config.settings.test` (in-memory SQLite)
- **Migrations**: Required after any model field change

---

## Current Project State

> Auto-refreshed by `pixi run refresh-context`. Last updated: 2026-05-22 01:08 UTC

| Metric | Value |
|---|---|
| Collection types | 6 (Automobiles, Coin Collection, Hand Bags, Horology Salon, The Gun Safe, Wine Collection) |
| Collection items | 3 |
| Collections value | $56,995.00 |
| **Total portfolio value** | **$56,995.00** |
| Last refresh | 2026-05-22 01:08 UTC |

