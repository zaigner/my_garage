# My Garage - Automotive Asset Management Platform

## Project Overview

My Garage is an automotive asset management and valuation platform designed for car enthusiasts. It helps users track their vehicles as financial assets, manage service history, plan upgrades, and understand their car's market value through AI-powered tools and real-time market intelligence.

## Core Features

1. **Digital Vehicle Vault**: Track vehicles with VIN decoding, purchase price, current market value, and comprehensive metadata
2. **Paperless Service Catalog**: AI-powered OCR for digitizing service receipts and categorizing maintenance/repairs/upgrades
3. **Upgrade Project Manager**: Track modifications from wishlist to installation with cost tracking
4. **Market Intelligence Engine**: Real-time market valuation using Web MCP to browse comparable listings
5. **Visual Condition Grading**: AI-powered condition assessment with value impact analysis

## Technology Stack

- **Backend Framework**: Django 5.2 LTS
- **Async Processing**: Celery with Redis
- **AI/OCR Service**: FastAPI (separate service)
- **Database**: PostgreSQL
- **Image Processing**: Pillow
- **External Integration**: Model Context Protocol (MCP) for web scraping and market data
- **Environment Management**: Pixi
- **Python Version**: 3.12+

## Project Architecture

This project follows a **strict layered architecture** pattern to maintain separation of concerns and testability:

### 1. Model Layer (models.py)
- **Purpose**: Pure data definitions and database constraints
- **Contains**: Django ORM models, field definitions, validators, model methods
- **Rules**:
  - No business logic
  - No external API calls
  - Only database schema and simple computed properties

**Key Models**:
- `Vehicle`: Core asset with financials (purchase_price, current_market_value)
- `ServiceRecord`: Service history with OCR data (JSONField for flexibility)
- `Upgrade`: Modification tracking (WISHLIST → ORDERED → INSTALLED)
- `ConditionReport`: AI-graded visual assessments with value adjustments

### 2. Selector Layer (selectors.py)
- **Purpose**: Data retrieval and complex queries (Read operations)
- **Contains**: Functions that SELECT data from the database
- **Rules**:
  - Read-only operations
  - No mutations or saves
  - All aggregation happens at DB level (use Django ORM aggregation)
  - Use `Coalesce` to prevent None returns in Sum operations
  - Return QuerySets, model instances, or dictionaries

**Key Patterns**:
```python
def vehicle_get_build_summary(vehicle_id: int) -> Dict[str, Any]:
    """Returns comprehensive financial summary for dashboard"""

def vehicle_list_wishlist_items(vehicle: Vehicle) -> QuerySet[Upgrade]:
    """Returns filtered QuerySet for wishlist parts"""
```

### 3. Service Layer (services.py)
- **Purpose**: Business logic, AI integrations, and data mutations (Write operations)
- **Contains**: Functions that CREATE, UPDATE, or DELETE data
- **Rules**:
  - Use `@transaction.atomic` for operations affecting multiple records
  - Raise custom exceptions (e.g., `VehicleServiceError`) for business logic failures
  - Handle external API calls (FastAPI OCR, Web MCP)
  - Perform complex calculations and state transitions
  - Call selectors when needing to read data

**Key Patterns**:
```python
@transaction.atomic
def vehicle_update_market_valuation(vehicle: Vehicle) -> Decimal:
    """Calls Web MCP and updates vehicle.current_market_value"""

def service_record_create_from_ocr(vehicle: Vehicle, receipt_image: Any) -> ServiceRecord:
    """Creates record and triggers OCR processing"""
```

### 4. View Layer (views.py)
- **Purpose**: Orchestration and HTTP response handling
- **Contains**: Django views (Function-Based or Class-Based)
- **Rules**:
  - Thin views - minimal logic
  - Call selectors for data retrieval
  - Call services for mutations
  - Handle HTTP concerns (request validation, response formatting)
  - Catch service exceptions and return appropriate HTTP responses

**Key Pattern**:
```python
def vehicle_detail_view(request, vehicle_id):
    summary = vehicle_get_build_summary(vehicle_id)  # Selector
    return render(request, 'my_garage/dashboard.html', summary)
```

### 5. Task Layer (tasks.py)
- **Purpose**: Background job processing with Celery
- **Contains**: Async tasks for time-consuming operations
- **Rules**:
  - Use for OCR processing, image analysis, market scraping
  - Call services and selectors as needed
  - Handle retries and error logging

## Coding Conventions

### Naming Conventions
- **Selectors**: `{model}_get_{description}`, `{model}_list_{description}`
  - Examples: `vehicle_get_total_maintenance_cost()`, `vehicle_list_wishlist_items()`
- **Services**: `{model}_{action}_{description}`
  - Examples: `vehicle_update_market_valuation()`, `service_record_create_from_ocr()`
- **Tasks**: `{action}_{description}_async`
  - Examples: `process_receipt_ocr_async()`, `update_market_values_async()`

### Type Hints
- Always use type hints for function parameters and return values
- Use `Optional[Type]` for nullable values
- Import types from `typing` module

### Decimal Handling
- Use `Decimal` type for all financial calculations
- Never use floats for money
- Use `Coalesce` with `Decimal('0.00')` in aggregations to prevent None

### Error Handling
- Create custom exceptions in services.py (e.g., `VehicleServiceError`)
- Use `@transaction.atomic` for multi-record operations
- Let views catch and convert service exceptions to HTTP responses

## Key Design Decisions

1. **JSONField for OCR Data**: The `ServiceRecord.ocr_raw_data` field stores raw OCR output as JSON, allowing flexible schema without rigid database migrations

2. **Condition Reports Over Time**: `ConditionReport` is separate from `Vehicle` to allow multiple assessments (before/after detailing, restoration progress)

3. **Status-Driven Workflows**: The `Upgrade.status` field (WISHLIST → ORDERED → INSTALLED) enables tracking the full lifecycle of modifications

4. **Value Adjustments**: `ConditionReport.value_adjustment` allows AI to directly impact `Vehicle.current_market_value` based on visual condition

5. **External Service Integration**: FastAPI handles compute-intensive OCR/AI tasks, keeping Django focused on application logic

## Development Workflow

### Running the Application
```bash
pixi run migrate      # Run database migrations
pixi run server       # Start Django development server
pixi run worker       # Start Celery worker
```

### Adding New Features
1. Define models in `models.py` (if needed)
2. Create migrations: `python manage.py makemigrations`
3. Add selectors in `selectors.py` for data retrieval
4. Add services in `services.py` for business logic
5. Add views in `views.py` for HTTP handling
6. Add async tasks in `tasks.py` (if needed)
7. Wire up URLs in `urls.py`

## Integration Points

### FastAPI OCR Service
- **Base URL**: Configured via `settings.FASTAPI_BASE_URL`
- **Purpose**: Document OCR, image analysis, condition grading
- **Communication**: HTTP POST with JSON payloads

### Model Context Protocol (MCP)
- **Endpoint**: `{FASTAPI_BASE_URL}/mcp/execute`
- **Purpose**: Web scraping for market listings, price comparisons
- **Tool**: `search_market_listings` - finds comparable vehicles on auction sites

## Financial Calculations

### Total Investment
```python
total_investment = (
    vehicle.purchase_price +
    sum(verified_service_records.total_cost) +
    sum(installed_upgrades.cost)
)
```

### Equity
```python
equity = vehicle.current_market_value - total_investment
```

### Market Value Updates
- Triggered manually or via scheduled Celery tasks
- Queries comparable listings via Web MCP
- Calculates median price from results
- Updates `Vehicle.current_market_value` atomically

## Testing Guidelines

- Write tests for selectors to verify query logic and aggregations
- Write tests for services to verify business logic and transactions
- Mock external API calls (FastAPI, MCP) in service tests
- Use Django's TestCase for database-backed tests
- Use TransactionTestCase for testing atomic operations

## Common Patterns to Follow

### Reading Data
```python
# In views.py
summary = vehicle_get_build_summary(vehicle.id)
```

### Mutating Data
```python
# In views.py
try:
    new_value = vehicle_update_market_valuation(vehicle)
except VehicleServiceError as e:
    return HttpResponseServerError(str(e))
```

### Complex Operations
```python
# In services.py
@transaction.atomic
def complex_operation(vehicle: Vehicle) -> Result:
    # Multiple database operations
    # If any fails, all rollback
    pass
```

## Future Roadmap

1. **VIN Decoder Integration**: Automatic population of vehicle specs
2. **PDF Export**: Generate comprehensive vehicle history reports
3. **Price Tracking**: Monitor wishlist parts with alerts
4. **Installation Tracking**: Log DIY vs shop hours
5. **Mod-Adjusted Valuation**: Logic for how upgrades affect value differently for enthusiasts vs purists
6. **Market Alerts**: Notifications when similar vehicles sell

## File Structure
```
my_garage/
├── migrations/         # Django database migrations
├── tests/              # Unit and integration tests
├── templates/          # Django HTML templates
│   └── my_garage/
│       └── dashboard.html
├── config/             # Configuration and routing
│   ├── urls.py
│   └── api_router.py
├── models.py           # Database schemas
├── selectors.py        # Read operations (Application Layer)
├── services.py         # Write operations (Business Logic)
├── tasks.py            # Celery background tasks
├── urls.py             # URL routing
├── views.py            # HTTP request handlers
├── design.md           # Detailed design documentation
└── pyproject.toml      # Project dependencies
```

## Additional Resources

- See `design.md` for detailed feature specifications and architecture notes
- Django 5.2 Documentation: https://docs.djangoproject.com/
- Celery Documentation: https://docs.celeryq.dev/
