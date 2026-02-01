# My Garage - Automotive Asset Management Platform

## Project Overview

My Garage is an automotive asset management and valuation platform designed for car enthusiasts. It helps users track their vehicles as financial assets, manage service history, plan upgrades, and understand their car's market value through AI-powered tools and real-time market intelligence.

**Current Status:** ✅ **UI/UX Overhaul Complete** - The platform has been redesigned with a "Professional Garage" aesthetic, featuring dark mode, race deck flooring, and dynamic manufacturer-specific typography.

## Core Features

1. **Digital Vehicle Vault**: Track vehicles with VIN decoding, purchase price, current market value, and comprehensive metadata.
2. **Paperless Service Catalog**: AI-powered OCR for digitizing service receipts and categorizing maintenance/repairs/upgrades.
3. **Upgrade Project Manager**: Track modifications from wishlist to installation with cost tracking.
4. **Market Intelligence Engine**: Real-time market valuation using Web MCP to browse comparable listings.
5. **Visual Condition Grading**: AI-powered condition assessment with value impact analysis.
6. **Generative Visuals**: AI-generated visualizations for project cars and modifications.
7. **Immersive Garage Experience**: A high-fidelity UI that mimics a physical garage with dynamic lighting, flooring, and branding.
8. **Interactive 360° Viewer**: Exploratory vehicle detail pages allowing users to rotate and inspect vehicles from all angles (Imagin.Studio integration).

## Technology Stack

### Backend
- **Django 5.2 LTS** - Web framework
- **Django REST Framework 3.14+** - API framework
- **Celery 5.3+** - Async task queue
- **Redis 5.0+** - Celery broker and result backend

### Frontend
- **Tailwind CSS** - Utility-first CSS framework
- **Google Fonts** - Dynamic typography (Michroma, Cinzel, Orbitron, etc.)
- **CSS3 Animations** - For carousel and spotlight effects

### Quality Assurance & Tooling
- **Ruff** - Extremely fast Python linter and formatter
- **Pre-commit** - Git hook manager for code quality checks
- **Pixi** - Package management and workflow automation

### External Services
- **FastAPI 0.104+** - Microservice for AI/compute tasks.
- **NHTSA vPIC API** - For VIN decoding.
- **Marketcheck API** - For market valuation.
- **Imagin.Studio API** - For 360° vehicle imagery.
- **Google Gemini API** - For generative AI image creation.

## Development Log - UI/UX Overhaul

Today's session focused on transforming the user interface into a premium, immersive experience.

1.  **Vehicle Detail Redesign**:
    *   **Theme**: Implemented a "Dark Mode" aesthetic with a "Race Deck" floor pattern background.
    *   **Typography**: Integrated `Michroma` (Porsche-style) font for headers and monospaced fonts for financial telemetry.
    *   **Layout**: Created a driver-focused 3-column layout with "cabinet-style" containers for data entry.
    *   **Usability**: Added scrollable containers for long lists of specifications and features to maintain layout integrity.

2.  **Garage Carousel Enhancements**:
    *   **Dynamic Typography**: Implemented JavaScript logic to automatically apply manufacturer-appropriate fonts (e.g., `Orbitron` for Toyota, `Michroma` for Porsche, `Racing Sans One` for Ford) based on the vehicle make.
    *   **Visuals**: Enhanced the carousel with spotlight effects and 3D perspective flooring.

## Development Log - Generative AI Integration

Previous session focused on adding generative AI capabilities to the platform.

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

## Development Log - Market Intelligence & Fixes

Today's session focused on expanding market data capabilities and fixing the generative AI pipeline.

1.  **Sales Statistics Integration**:
    *   Created `src/fastapi_services/mcp/tools/sales_stats.py` to interface with Marketcheck's Sales Stats and History endpoints.
    *   Implemented `get_sales_stats` to retrieve mean/median sold prices and days-on-market.
    *   Implemented `get_sales_history_by_vin` to track specific vehicle transaction history.
    *   Registered new tools in `src/fastapi_services/mcp/main.py`.

2.  **Gemini API Refactor**:
    *   Refactored `image_generation.py` to remove the deprecated Banana.dev dependency.
    *   Updated the tool to use Google's `generativelanguage.googleapis.com` REST endpoint directly for the Gemini 2.5 Flash Image model (Nano Banana).

**Outcome**: The platform now combines robust backend functionality with a high-end, enthusiast-focused user interface.
