# Feature Specification: My Garage Platform

## Overview

**Feature ID**: 001-my-garage-platform
**Status**: ✅ Phase 13 Complete - Dynamic Collections & Timepieces
**Owner**: Development Team
**Created**: 2025-12-21
**Last Updated**: 2026-02-12

## Problem Statement

Car enthusiasts lack professional-grade tools to manage their vehicles as financial assets. Current solutions are either:
- **Too Simple**: Basic spreadsheets that don't integrate with external data or automate tracking
- **Too Complex**: Enterprise fleet management systems designed for businesses, not individuals
- **Disconnected**: Separate tools for maintenance tracking, valuation, and upgrade planning without integration

**User Pain Points:**
1. Manual entry of service records from paper receipts is tedious and error-prone
2. Unclear whether modifications increase or decrease vehicle value
3. No easy way to track total investment vs. current market value
4. Difficulty proving maintenance history to potential buyers
5. No automated market valuation updates
6. Hard to visualize potential modifications before purchasing parts
7. Generic, boring interfaces that don't reflect the passion of car ownership
8. Lack of support for other luxury assets like watches, which often overlap with car collecting

## User Stories

### Epic 1: Vehicle Management
- **As a** car owner
- **I want to** register my vehicles with detailed information
- **So that** I can track all my automotive assets in one place

**Acceptance Criteria:**
- ✅ Can create vehicle with make, model, year, VIN
- ✅ Can set purchase price and current market value
- ✅ Can track mileage and creation date
- ✅ Can view all my vehicles in a dashboard
- ✅ Can edit and delete vehicles via admin interface
- ✅ Can access vehicle data via REST API
- ✅ Can add vehicles via a dedicated form in the UI
- ✅ System can decode VINs to pre-fill vehicle details (FastAPI service implemented)
- ✅ System automatically fetches stock photos for vehicles (Market Listings + Google Fallback)
- ✅ UI reflects the brand identity of the vehicle (e.g., Porsche font for Porsche cars)

### Epic 2: Service History Tracking
- **As a** car owner
- **I want to** digitize my service receipts automatically
- **So that** I don't have to manually enter every maintenance record

**Acceptance Criteria:**
- ✅ Can upload receipt images
- ✅ System queues OCR processing in background
- ⏳ System extracts vendor, date, cost via OCR (FastAPI service pending)
- ✅ Can categorize services as maintenance, repair, or upgrade
- ✅ Can view service history chronologically
- ✅ Can verify and edit OCR-extracted data

### Epic 3: Upgrade Planning & Tracking
- **As a** car enthusiast
- **I want to** plan and track modifications
- **So that** I can manage my build project and budget

**Acceptance Criteria:**
- ✅ Can add parts to wishlist with estimated costs
- ✅ Can mark parts as ordered or installed
- ✅ Can track actual installation costs
- ✅ Can view total upgrade investment
- ✅ Can add notes for each modification
- ✅ Can generate AI visualizations of potential modifications (FastAPI service implemented)

### Epic 4: Market Valuation
- **As a** car owner
- **I want to** know my vehicle's current market value
- **So that** I can make informed decisions about selling or insuring

**Acceptance Criteria:**
- ✅ System fetches comparable listings from an API (FastAPI service implemented)
- ✅ Calculates median market value automatically
- ✅ Updates valuation on demand or scheduled (Celery task implemented)
- ✅ Displays equity (market value - total investment)
- ✅ Shows whether vehicle is profitable
- ✅ Valuation considers trim, mileage, and color for accuracy

### Epic 5: Condition Assessment
- **As a** car owner
- **I want to** track my vehicle's condition over time
- **So that** I can monitor depreciation and plan maintenance

**Acceptance Criteria:**
- ✅ Can upload photos of different vehicle areas
- ⏳ AI grades condition on 1-10 scale
- ⏳ System provides feedback on visible issues
- ⏳ Calculates value impact based on condition
- ✅ Tracks condition changes over time

### Epic 6: Interactive Exploration
- **As a** car enthusiast
- **I want to** rotate and inspect my car in 3D/360°
- **So that** I can appreciate the aesthetics and visualize changes dynamically

**Acceptance Criteria:**
- ⏳ Vehicle detail page features an interactive 360° spin viewer
- ⏳ Viewer dynamically loads images based on Make, Model, Year, and Paint Color
- ⏳ Users can drag to rotate the vehicle
- ⏳ Integration with Imagin.Studio or similar automotive imagery API

### Epic 7: Timepiece Management
- **As a** collector
- **I want to** track my fine watches alongside my cars
- **So that** I can manage my entire luxury portfolio in one place

**Acceptance Criteria:**
- ✅ Can add timepieces with brand, model, reference number
- ✅ Can track movement type, case material, and complications
- ✅ Can upload photos of the watch
- ✅ Can track purchase price and current market value
- ✅ Dedicated "Horology Salon" view with appropriate aesthetic
- ✅ Dedicated URL structure (`/timepieces/`) separate from garage

### Epic 8: Dynamic Collections
- **As a** collector
- **I want to** create custom collection types for any asset (Wine, Art, Books, etc.)
- **So that** I can track my entire portfolio in one system

**Acceptance Criteria:**
- ✅ Can create custom collection types with user-defined schemas
- ✅ Can add custom fields (text, number, date, file, relationship)
- ✅ Can track items with standard + custom fields
- ✅ Can track service records for any collection item
- ✅ Can manage projects/upgrades with Kanban board
- ✅ Dedicated URL structure (`/collections/`)

### Epic 9: Portfolio Dashboard
- **As a** collector
- **I want to** see a unified view of all my assets and their total value
- **So that** I can understand my net worth and recent activity

**Acceptance Criteria:**
- ✅ Home page displays total portfolio valuation (sum of vehicles, timepieces, collections)
- ✅ Breakdown of value by category
- ✅ Recent acquisitions feed showing latest items from all categories
- ✅ Unified aesthetic matching the "Vault" theme

## Technical Specification

### Architecture

**Framework**: Django 5.2 LTS with service layer pattern
**Database**: SQLite (dev), PostgreSQL (prod)
**Async Tasks**: Celery with Redis broker
**AI Services**: Separate FastAPI microservice
**External Data**: NHTSA vPIC API, Marketcheck API, Google Search (Fallback), Google Gemini API
**Package Manager**: Pixi
**Code Quality**: Ruff (Linting/Formatting), Pre-commit hooks

### Data Model

#### Vehicle
```python
class Vehicle(models.Model):
    owner = ForeignKey(User, on_delete=CASCADE)
    make = CharField(max_length=50)
    model = CharField(max_length=50)
    year = PositiveIntegerField
    trim = CharField(max_length=100, blank=True)
    vin = CharField(max_length=17, unique=True, blank=True)
    license_plate = CharField(max_length=20, blank=True)
    
    # Collector Specs
    transmission = CharField(max_length=50, blank=True)
    exterior_color = CharField(max_length=50, blank=True)
    interior_color = CharField(max_length=50, blank=True)

    purchase_price = DecimalField(max_digits=12, decimal_places=2)
    purchase_date = DateField(null=True, blank=True)
    current_market_value = DecimalField(max_digits=12, decimal_places=2)
    mileage = PositiveIntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
    notes = TextField(blank=True)
```

#### Timepiece
```python
class Timepiece(models.Model):
    owner = ForeignKey(User, on_delete=CASCADE)
    brand = CharField(max_length=100)
    model = CharField(max_length=100)
    reference_number = CharField(max_length=100)
    serial_number = CharField(max_length=100, blank=True)
    year = PositiveIntegerField(null=True)
    
    movement_type = CharField(choices=MOVEMENT_CHOICES)
    case_material = CharField(max_length=50)
    dial_color = CharField(max_length=50)
    complications = JSONField(default=list)
    
    has_box = BooleanField(default=False)
    has_papers = BooleanField(default=False)
    condition_grade = CharField(max_length=20)
    
    purchase_price = DecimalField(max_digits=12, decimal_places=2)
    current_market_value = DecimalField(max_digits=12, decimal_places=2)
    photo = ImageField(upload_to="timepieces/%Y/%m/")
```

#### Dynamic Collections
```python
class CollectionType(models.Model):
    owner = ForeignKey(User, on_delete=CASCADE)
    name = CharField(max_length=100)
    slug = SlugField(max_length=100)
    icon = CharField(max_length=50)  # FontAwesome class
    description = TextField(blank=True)
    field_schema = JSONField(default=dict)  # {fields: [{name, type, label, required}]}
    list_display_fields = JSONField(default=list)

class DynamicCollectionItem(models.Model):
    collection_type = ForeignKey(CollectionType, on_delete=CASCADE)
    owner = ForeignKey(User, on_delete=CASCADE)
    name = CharField(max_length=200)
    photo = ImageField(upload_to="collections/%Y/%m/", blank=True)
    purchase_price = DecimalField(max_digits=12, decimal_places=2, null=True)
    purchase_date = DateField(null=True, blank=True)
    current_market_value = DecimalField(max_digits=12, decimal_places=2, null=True)
    custom_fields = JSONField(default=dict)  # Stores dynamic field values
```

#### ServiceRecord
```python
class ServiceRecord(models.Model):
    vehicle = ForeignKey(Vehicle, on_delete=CASCADE)
    date = DateField()
    vendor = CharField(max_length=255)
    description = TextField()
    category = CharField(choices=CATEGORY_CHOICES)  # MAINTENANCE/REPAIR/UPGRADE
    total_cost = DecimalField(max_digits=10, decimal_places=2)
    receipt_image = ImageField(upload_to="receipts/%Y/%m/")
    ocr_raw_data = JSONField(null=True, blank=True)
    is_verified = BooleanField(default=False)
```

#### GenericServiceRecord (Collections)
```python
class GenericServiceRecord(models.Model):
    item = ForeignKey(DynamicCollectionItem, on_delete=CASCADE)
    # Same fields as ServiceRecord...
```

#### Upgrade
```python
class Upgrade(models.Model):
    vehicle = ForeignKey(Vehicle, on_delete=CASCADE)
    part_name = CharField(max_length=255)
    brand = CharField(max_length=100)
    part_number = CharField(max_length=100)
    status = CharField(choices=STATUS_CHOICES)  # WISHLIST/ORDERED/INSTALLED
    cost = DecimalField(max_digits=10, decimal_places=2)
    installation_date = DateField(null=True, blank=True)
    notes = TextField(blank=True)
```

#### GenericUpgrade (Collections)
```python
class GenericUpgrade(models.Model):
    item = ForeignKey(DynamicCollectionItem, on_delete=CASCADE)
    # Same fields as Upgrade plus Kanban support...
```

#### ConditionReport
```python
class ConditionReport(models.Model):
    vehicle = ForeignKey(Vehicle, on_delete=CASCADE)
    area = CharField(choices=AREA_CHOICES)  # EXTERIOR/INTERIOR/ENGINE/WHEELS
    photo = ImageField(upload_to="condition_checks/%Y/%m/")
    grade = FloatField(validators=[MinValue(1.0), MaxValue(10.0)])
    ai_feedback = TextField()
    value_adjustment = DecimalField(max_digits=10, decimal_places=2)
    created_at = DateTimeField(auto_now_add=True)
```

### API Endpoints

#### Selectors (Read Operations)
```python
vehicle_get_build_summary(vehicle_id: int) -> Dict[str, Any]
vehicle_get_total_maintenance_cost(vehicle: Vehicle) -> Decimal
vehicle_get_total_upgrade_cost(vehicle: Vehicle) -> Decimal
vehicle_list_wishlist_items(vehicle: Vehicle) -> QuerySet[Upgrade]
vehicle_get_pending_service_count(vehicle: Vehicle) -> int
```

#### Services (Write Operations)
```python
vehicle_update_market_valuation(vehicle: Vehicle) -> Decimal
service_record_create_from_ocr(vehicle: Vehicle, receipt_image) -> ServiceRecord
service_record_process_ocr_data(record: ServiceRecord) -> bool
condition_report_add_ai_grade(vehicle: Vehicle, ...) -> ConditionReport
upgrade_install_part(upgrade: Upgrade, cost: Optional[Decimal]) -> Upgrade
```

#### Celery Tasks
```python
task_process_receipt_ocr(record_id: int) -> bool
task_update_market_valuation(vehicle_id: int) -> str
task_bulk_valuation_refresh() -> str
```

### External Integrations

#### FastAPI Services (Implemented)
- **VIN Lookup**:
  - **Endpoint**: `POST /mcp/execute` with tool `lookup_vehicle_details`
  - **Input**: VIN string
  - **Output**: JSON with vehicle make, model, year, etc.
  - **API Used**: NHTSA vPIC API
- **Market Valuation**:
  - **Endpoint**: `POST /mcp/execute` with tool `search_market_listings`
  - **Input**: Make, model, year, trim, mileage, color
  - **Output**: List of comparable listings with prices and photos
  - **API Used**: Marketcheck API
- **Image Search**:
  - **Endpoint**: `POST /mcp/execute` with tool `search_google_images`
  - **Input**: Search query string
  - **Output**: List of image URLs
  - **API Used**: Google Search (Scraping/API)
- **Image Generation**:
  - **Endpoint**: `POST /mcp/execute` with tool `generate_vehicle_image`
  - **Input**: Prompt string, Negative Prompt string (optional)
  - **Output**: Base64 encoded image
  - **API Used**: Google Gemini 2.5 Flash Image
- **Sales Statistics**:
  - **Endpoint**: `POST /mcp/execute` with tool `get_sales_stats` or `get_sales_history_by_vin`
  - **Input**: Year, Make, Model, Zip (for stats) OR VIN (for history)
  - **Output**: JSON with sales metrics (mean/median price, DOM) or transaction history
  - **API Used**: Marketcheck API
- **Watch Valuation**:
  - **Endpoint**: `POST /mcp/execute` with tool `get_watch_valuation`
  - **Input**: Brand, Model, Reference Number
  - **Output**: JSON with estimated value
  - **API Used**: Mock Service (Placeholder for Chrono24/WatchCharts)

#### FastAPI OCR Service (To Implement)
- **Endpoint**: `POST /ocr/process`
- **Input**: Image file (receipt photo)
- **Output**: JSON with extracted vendor, date, cost, line items
- **Technology**: Tesseract OCR, OpenAI Vision API, or similar

## Implementation Status

### ✅ Completed (Phase 1-13)

**Phase 1-6**: (See previous versions for details)

**Phase 7: FastAPI Service Development**
- ✅ Created `fastapi_services` directory in `src/`
- ✅ Structured MCP service with `main.py`, `config.py`, and `tools/`
- ✅ Implemented `vehicle_lookup.py` tool using NHTSA vPIC API
- ✅ Implemented `market_valuation.py` tool using Marketcheck API
- ✅ Added `beautifulsoup4` for potential scraping tasks
- ✅ Configured environment variables for API keys
- ✅ Updated UI with "Add Vehicle" link and fixed visual bugs

**Phase 8: Photo Fetching & Enhanced Valuation**
- ✅ Implemented `vehicle_fetch_stock_photo` service with multi-strategy fallback
- ✅ Created `google_search.py` MCP tool for image fallback
- ✅ Enhanced `market_valuation.py` to accept trim, mileage, and color
- ✅ Updated `vehicle_update_market_valuation` to use detailed specs for better accuracy
- ✅ Updated UI to display stock photos with indicators

**Phase 9: Generative AI Integration**
- ✅ Implemented `image_generation.py` MCP tool using Google Gemini
- ✅ Configured API key handling for Google services
- ✅ Registered new tool in FastAPI router

**Phase 10: UI/UX Overhaul**
- ✅ Redesigned `vehicle_detail.html` with "Race Deck" theme and cabinet-style inputs
- ✅ Implemented dynamic manufacturer fonts in `garage.html` carousel
- ✅ Added scrollable containers for specs and features
- ✅ Enhanced `base.html` with global font libraries and Tailwind config

**Phase 11: Market Intelligence & Fixes**
- ✅ Implemented `sales_stats.py` MCP tool for sold data analysis
- ✅ Implemented `get_sales_history_by_vin` for provenance tracking
- ✅ Refactored `image_generation.py` to use native Google Gemini API (fixing Banana.dev deprecation)

**Phase 12: Timepieces & Navigation**
- ✅ Implemented `Timepiece` model and views
- ✅ Created "Horology Salon" templates (`timepiece_list.html`, `timepiece_detail.html`)
- ✅ Updated `home.html` to serve as central dashboard
- ✅ Fixed navigation links to point to Home instead of Garage
- ✅ Updated `vehicle_form.html` to match Race Deck theme
- ✅ Created `start_app.sh` for unified service startup

**Phase 13: Dynamic Collections & Restructuring**
- ✅ Implemented `CollectionType` and `DynamicCollectionItem` models
- ✅ Created schema builder for custom collection types
- ✅ Implemented Kanban board for project management
- ✅ Restructured URLs: `/garage/` (vehicles), `/timepieces/` (watches), `/collections/` (dynamic)
- ✅ Implemented `watch_valuation` MCP tool (mock)
- ✅ Updated all templates to use correct namespaces
- ✅ Implemented Portfolio Dashboard with total valuation and recent acquisitions

### ⏳ Remaining Work

**FastAPI OCR Service**
- Implement receipt image preprocessing
- Integrate OCR library (Tesseract or cloud API)
- Parse extracted text into structured data
- Return JSON with vendor, date, cost, line items

**Dashboard Views**
- Create service history timeline view
- Create upgrade tracker with status indicators
- Create condition report gallery
- Implement 360° Spin Viewer (Epic 6)

**Additional Features**
- PDF export of vehicle history
- Price tracking for wishlist parts
- Email notifications for market changes

## Success Metrics

### User Engagement
- **Target**: Users log in weekly to check vehicle values
- **Measure**: Weekly active users, session duration

### Data Quality
- **Target**: 95%+ accuracy on OCR extraction
- **Measure**: Percentage of verified vs. manually corrected records

### Value Tracking
- **Target**: Users can answer "Is my car worth more than I paid?" instantly
- **Measure**: Average time to access equity calculation

### Feature Adoption
- **Target**: 80% of users upload at least one receipt
- **Measure**: Percentage of users with service records

## Dependencies

### External
- **Django 5.2+**: Web framework
- **PostgreSQL**: Production database (or SQLite for dev)
- **Redis**: Celery broker and result backend
- **FastAPI**: Separate AI/OCR service
- **NHTSA vPIC API**: For VIN decoding
- **Marketcheck API**: For market valuation
- **Google Gemini API**: For generative AI
- **OCR Service**: Tesseract, Google Cloud Vision, or similar

### Internal
- Must have user authentication system (Django built-in)
- Must have file upload capability (Django media files)
- Must have task queue (Celery)
- **Ruff**: Linter and Formatter
- **Pre-commit**: Git hook manager

## Risks & Mitigations

### Risk 1: OCR Accuracy
**Risk**: Receipt OCR may not be accurate enough for financial data
**Impact**: High - incorrect costs lead to wrong equity calculations
**Mitigation**:
- Implement manual verification workflow
- Show confidence scores for extracted data
- Allow easy editing of OCR results
- Keep original receipt image for reference

### Risk 2: Market Data Availability
**Risk**: Web scraping may be blocked or data unavailable
**Impact**: Medium - users can't get automated valuations
**Mitigation**:
- Support multiple data sources
- Implement rate limiting and respectful scraping
- Allow manual market value entry
- Cache results to reduce scraping frequency

### Risk 3: External API Costs
**Risk**: Cloud OCR/vision/GenAI APIs may be expensive at scale
**Impact**: Medium - affects project viability
**Mitigation**:
- Use open-source Tesseract first
- Only call cloud APIs if Tesseract fails
- Implement usage limits per user
- Consider self-hosted AI models

### Risk 4: Data Privacy
**Risk**: Receipts contain sensitive personal information
**Impact**: High - privacy breach would be severe
**Mitigation**:
- Encrypt uploaded files at rest
- Limit access to vehicle owner only
- Implement proper Django permissions
- Don't share data with third parties

## Testing Strategy

### Unit Tests
- Test selectors return correct aggregations
- Test services handle edge cases (negative equity, missing data)
- Test models validate data correctly
- Test forms reject invalid input

### Integration Tests
- Test views call selectors/services correctly
- Test admin interface CRUD operations
- Test file uploads save correctly
- Test task queueing and execution

### External API Tests
- Mock FastAPI responses for OCR
- Mock MCP responses for market data
- Test error handling when APIs fail
- Test retry logic for transient failures

### Performance Tests
- Test database queries don't have N+1 issues
- Test page load times under realistic data volume
- Test Celery task processing time
- Test concurrent user sessions

## Documentation

### User Documentation
- Getting started guide
- How to add a vehicle
- How to upload receipts
- How to interpret equity calculations
- FAQ for common questions

### Developer Documentation
- ✅ claude.md - Comprehensive project guide
- ✅ design.md - Feature specifications
- ✅ constitution.md - Project principles

### API Documentation
- Selector function signatures and return types
- Service function signatures and exceptions
- Celery task parameters and return values
- External API request/response formats

## Release Plan

### Version 0.1.0 (Current) ✅
- Django project structure
- Database models and migrations
- Django admin interface
- Service layer pattern

### Version 0.2.0 (Current) ✅
- Celery task queue integration
- DRF API endpoints
- Async OCR and Valuation triggers
- Pixi integration
- UI/UX Refresh

### Version 0.3.0 (Current) ✅
- FastAPI service for VIN lookup and market valuation

### Version 0.4.0 (Current) ✅
- Generative AI integration
- Enhanced photo fetching

### Version 0.5.0 (Current) ✅
- UI/UX Overhaul (Dark Mode, Dynamic Fonts)

### Version 0.6.0 (Current) ✅
- Timepiece Management
- Navigation Restructuring
- Unified Startup Script

### Version 0.7.0 (Current) ✅
- Dynamic Collections System
- Kanban Board
- URL Restructuring
- Portfolio Dashboard

### Version 0.8.0 (Next)
- FastAPI OCR service
- Receipt upload and processing
- Dashboard views

### Version 1.0.0
- All core features implemented
- Comprehensive test coverage
- Production-ready deployment
- User documentation complete

---

**Status**: Living specification - update as requirements evolve
**Review Cadence**: After each major feature implementation
**Approval**: Development team consensus
