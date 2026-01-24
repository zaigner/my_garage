# My Garage - Automotive Asset Management Platform

## Project Overview

My Garage is an automotive asset management and valuation platform designed for car enthusiasts. It helps users track their vehicles as financial assets, manage service history, plan upgrades, and understand their car's market value through AI-powered tools and real-time market intelligence.

**Current Status:** ✅ **Generative AI Integration** - Added capability to generate vehicle images using Google Gemini 2.5 Flash Image, expanding the platform's visual capabilities.

## Core Features

1. **Digital Vehicle Vault**: Track vehicles with VIN decoding, purchase price, current market value, and comprehensive metadata.
2. **Paperless Service Catalog**: AI-powered OCR for digitizing service receipts and categorizing maintenance/repairs/upgrades.
3. **Upgrade Project Manager**: Track modifications from wishlist to installation with cost tracking.
4. **Market Intelligence Engine**: Real-time market valuation using Web MCP to browse comparable listings.
5. **Visual Condition Grading**: AI-powered condition assessment with value impact analysis.
6. **Generative Visuals**: AI-generated visualizations for project cars and modifications.

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
- **Google Gemini API** - For generative AI image creation.

## Development Log - Generative AI Integration

Today's session focused on adding generative AI capabilities to the platform.

1.  **Image Generation Tool**:
    *   Created `src/fastapi_services/mcp/tools/image_generation.py` to interface with Google's Gemini 2.5 Flash Image model.
    *   Implemented `generate_vehicle_image` function that accepts a prompt and negative prompt.
    *   Configured the tool to return base64 encoded images for immediate display or storage.

2.  **Configuration & Routing**:
    *   Updated `src/fastapi_services/mcp/config.py` to support `google_api_key` (and `gemini_api_key` fallback).
    *   Registered the new tool in `src/fastapi_services/mcp/main.py` under the `generate_vehicle_image` tool name.
    *   Ensured the FastAPI service can gracefully handle missing API keys by making them optional.

## Development Log - Code Quality Integration

Previous session focused on integrating code quality tools to ensure a clean and maintainable codebase.

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

**Outcome**: The platform now supports generative AI for vehicle visualization, alongside robust VIN enrichment and code quality standards.
