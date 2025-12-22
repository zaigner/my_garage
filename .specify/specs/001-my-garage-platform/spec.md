# Feature Specification: My Garage Platform

## Overview

**Feature ID**: 001-my-garage-platform
**Status**: ✅ Phase 4 Complete - Production-Ready Structure
**Owner**: Development Team
**Created**: 2025-12-21
**Last Updated**: 2025-12-21

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

### Epic 2: Service History Tracking
- **As a** car owner
- **I want to** digitize my service receipts automatically
- **So that** I don't have to manually enter every maintenance record

**Acceptance Criteria:**
- ✅ Can upload receipt images
- ⏳ System extracts vendor, date, cost via OCR
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

### Epic 4: Market Valuation
- **As a** car owner
- **I want to** know my vehicle's current market value
- **So that** I can make informed decisions about selling or insuring

**Acceptance Criteria:**
- ⏳ System scrapes comparable listings from auction sites
- ⏳ Calculates median market value automatically
- ⏳ Updates valuation on demand or scheduled
- ✅ Displays equity (market value - total investment)
- ✅ Shows whether vehicle is profitable

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

## Technical Specification

### Architecture

**Framework**: Django 5.2 LTS with service layer pattern
**Database**: SQLite (dev), PostgreSQL (prod)
**Async Tasks**: Celery with Redis broker
**AI Services**: Separate FastAPI microservice
**External Data**: Model Context Protocol for web scraping

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
    purchase_price = DecimalField(max_digits=12, decimal_places=2)
    current_market_value = DecimalField(max_digits=12, decimal_places=2)
    mileage = PositiveIntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)
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

#### FastAPI OCR Service (To Implement)
- **Endpoint**: `POST /ocr/process`
- **Input**: Image file (receipt photo)
- **Output**: JSON with extracted vendor, date, cost, line items
- **Technology**: Tesseract OCR, OpenAI Vision API, or similar

#### MCP Market Scraper (To Implement)
- **Endpoint**: `POST /mcp/execute`
- **Tool**: `search_market_listings`
- **Input**: Make, model, year range, trim
- **Output**: List of comparable listings with prices
- **Sources**: Bring a Trailer, Cars & Bids, eBay Motors, Autotrader

## Implementation Status

### ✅ Completed (Phase 1-4)

**Phase 1: Project Infrastructure**
- ✅ Django project structure with config/
- ✅ Multi-environment settings (base, local, production, test)
- ✅ WSGI/ASGI entry points
- ✅ Celery configuration
- ✅ Environment variable management

**Phase 2: Application Code**
- ✅ Moved code to django_apps/my_garage/
- ✅ Service layer in api/ subdirectory
- ✅ Created admin.py with full CRUD
- ✅ Created forms.py for data entry
- ✅ Fixed all import paths

**Phase 3: Database**
- ✅ Fixed model typo (on_backend → on_delete)
- ✅ Created initial migration (0001_initial.py)
- ✅ Applied all migrations successfully
- ✅ SQLite configured for development

**Phase 4: Testing & Running**
- ✅ Updated pyproject.toml with dependencies
- ✅ Wired up URL configuration
- ✅ Created superuser (admin/admin)
- ✅ Verified server startup
- ✅ Admin interface fully functional

### ⏳ Remaining Work

**FastAPI OCR Service**
- Implement receipt image preprocessing
- Integrate OCR library (Tesseract or cloud API)
- Parse extracted text into structured data
- Return JSON with vendor, date, cost, line items

**MCP Market Intelligence**
- Implement web scraping with MCP protocol
- Support multiple auction/listing sites
- Extract prices and vehicle details
- Calculate median market value
- Handle rate limiting and errors

**Dashboard Views**
- Create homepage dashboard showing all vehicles
- Create vehicle detail page with financial summary
- Create service history timeline view
- Create upgrade tracker with status indicators
- Create condition report gallery

**Background Processing**
- Implement Celery task for OCR processing
- Implement Celery task for market updates
- Set up Celery Beat for scheduled updates
- Add task monitoring and error handling

**Additional Features**
- VIN decoder integration
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
- **OCR Service**: Tesseract, Google Cloud Vision, or similar
- **Web Scraping**: MCP-compatible tools

### Internal
- Must have user authentication system (Django built-in)
- Must have file upload capability (Django media files)
- Must have task queue (Celery)

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
**Risk**: Cloud OCR/vision APIs may be expensive at scale
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
- ✅ RESTRUCTURE_PLAN.md - Architecture decisions
- ✅ MIGRATION_GUIDE.md - Step-by-step setup
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

### Version 0.2.0 (Next)
- FastAPI OCR service
- Receipt upload and processing
- Dashboard views

### Version 0.3.0
- MCP market intelligence
- Automated valuation updates
- Equity tracking

### Version 1.0.0
- All core features implemented
- Comprehensive test coverage
- Production-ready deployment
- User documentation complete

---

**Status**: Living specification - update as requirements evolve
**Review Cadence**: After each major feature implementation
**Approval**: Development team consensus
