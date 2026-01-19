# My Garage - Automotive Asset Management Platform

## Project Overview

My Garage is an automotive asset management and valuation platform designed for car enthusiasts. It helps users track their vehicles as financial assets, manage service history, plan upgrades, and understand their car's market value through AI-powered tools and real-time market intelligence.

**Current Status:** ✅ **VIN Enrichment Feature Complete** - The full pipeline for enriching vehicle data from a VIN is now functional, from the UI trigger to the background task and external API call.

## Core Features

1. **Digital Vehicle Vault**: Track vehicles with VIN decoding, purchase price, current market value, and comprehensive metadata.
2. **Paperless Service Catalog**: AI-powered OCR for digitizing service receipts and categorizing maintenance/repairs/upgrades.
3. **Upgrade Project Manager**: Track modifications from wishlist to installation with cost tracking.
4. **Market Intelligence Engine**: Real-time market valuation using Web MCP to browse comparable listings.
5. **Visual Condition Grading**: AI-powered condition assessment with value impact analysis.

## Technology Stack

### Backend
- **Django 5.2 LTS** - Web framework
- **Django REST Framework 3.14+** - API framework
- **Celery 5.3+** - Async task queue
- **Redis 5.0+** - Celery broker and result backend

### Quality Assurance & Tooling
- **Ruff** - Extremely fast Python linter and formatter
- **Pre-commit** - Git hook manager for code quality checks
- **Pixi** - Package management and workflow automation

### External Services
- **FastAPI 0.104+** - Microservice for AI/compute tasks.
- **NHTSA vPIC API** - For VIN decoding.
- **Marketcheck API** - For market valuation.

## Development Log - Code Quality Integration

Today's session focused on integrating code quality tools to ensure a clean and maintainable codebase.

1.  **Linter & Formatter Integration**:
    *   Added **Ruff** to the project dependencies in `pixi.toml` and `pyproject.toml`.
    *   Configured Ruff in `pyproject.toml` to target Python 3.12, with a line length of 88 characters.
    *   Enabled specific linting rules: `E` (pycodestyle errors), `W` (pycodestyle warnings), `F` (pyflakes), `I` (isort), `C` (flake8-comprehensions), and `B` (flake8-bugbear).

2.  **Pre-commit Hooks**:
    *   Created `.pre-commit-config.yaml` to manage Git hooks.
    *   Configured hooks for `ruff` (linting with auto-fix) and `ruff-format` (code formatting).
    *   Added a `pre-commit-install` task to `pixi.toml` for easy setup.

3.  **Workflow Automation**:
    *   Added `lint` and `format` tasks to `pixi.toml` so developers can run checks manually via `pixi run lint` or `pixi run format`.

## Development Log - VIN Enrichment

Previous session focused on implementing and debugging the "Enrich from VIN" feature.

1.  **Feature Implementation**:
    *   Added a button to the `vehicle_detail.html` page to manually trigger the VIN enrichment process.
    *   Created a new Django view (`trigger_vin_enrichment`) to handle the request.
    *   Created a Celery task (`task_enrich_vehicle_data`) to perform the lookup in the background.

2.  **Debugging the Celery Pipeline**:
    *   **Initial Problem**: The Celery worker was not processing any tasks, appearing "idle" despite tasks being sent.
    *   **Investigation**:
        *   Corrected a path issue in `config/celery_app.py` that was preventing task discovery.
        *   Diagnosed and fixed an incorrect use of `transaction.on_commit` for a `GET` request, which was preventing the task from being dispatched to the broker.
        *   Resolved a `ModuleNotFoundError` for `pytesseract` by synchronizing `pixi.toml` with `pyproject.toml`.
        *   Fixed a `pydantic` validation error in the FastAPI service by configuring it to ignore extra environment variables from the shared `.env` file.
    *   **Resolution**: After these fixes, the end-to-end pipeline (Django View → Celery Task → FastAPI Service → NHTSA API) was confirmed to be working successfully.

3.  **API Data Handling**:
    *   **Initial Problem**: The API was returning metadata and warnings (e.g., `error_text`) that were cluttering the UI.
    *   **Improvement**: Modified the FastAPI tool to filter out a known list of ignored keys, ensuring only clean vehicle data is returned.
    *   **Accuracy Boost**: Updated the service to send the vehicle's `model_year` along with the VIN to the NHTSA API, improving the accuracy of the returned data.

**Outcome**: The "Enrich from VIN" feature is now robust and functional. The debugging process has also hardened the Celery and FastAPI configurations, improving the overall stability of the project.
