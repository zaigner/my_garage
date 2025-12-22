Project Architecture & Layering
In your my_garage app directory, we will organize the code into four distinct layers:

Model Layer (models.py): Pure data definitions and database constraints.

Selector Layer (selectors.py): For data retrieval and complex queries (Application Layer).

Service Layer (services.py): For business logic, AI integrations, and data mutations.

View Layer (views.py): Orchestrates the selectors and services to return a response.

"My Garage" Feature Roadmap
Here is the functional breakdown of the features needed to make "My Garage" a powerhouse for car enthusiasts.

1. Digital Vehicle Vault (Core)
VIN Decoder Integration: Automatically pull year, make, model, engine code, and factory specs when a user adds a car.

Asset Overview: A dashboard showing the "Total Investment" (Purchase Price + Upgrades) vs. "Current Market Value."

Ownership Timeline: A visual history of the car, including purchase dates, major milestones, and service intervals.

2. The "Paperless" Service Catalog
AI Document Digitization: An upload tool that uses FastAPI + OCR to read physical service receipts. It should extract:

Date and Shop Name.

Parts used (e.g., "5W-30 Synthetic Oil").

Labor cost vs. Part cost.

Automated Categorization: Tagging services as Maintenance, Repair, or Performance Upgrade.

PDF Provenance Export: One-click generation of a "Vehicle History Report" to show potential buyers.

3. Upgrade Project Manager
Build Stages: Group upgrades into "Stages" (e.g., Stage 1: Intake/Exhaust, Stage 2: Turbo/Intercooler).

The "Wishlist" Optimizer: A tool to track parts you want to buy, with real-time price tracking via the Web MCP.

Installation Tracking: Log DIY hours vs. Shop hours for every upgrade to track the "true cost" of a build.

4. Market Intelligence Engine (Web MCP)
Real-time Comping: Use the Model Context Protocol to browse sites like Bring a Trailer, Cars & Bids, and eBay Motors.

Mod-Adjusted Valuation: A logic engine that understands that a "Stage 2" upgrade might increase value to an enthusiast but decrease it for a purist.

Market Alerts: Notify the user when a car similar to theirs sells for a record high (or low).

5. Visual Condition & Grading
Photo Inspection Guide: A guided UI that asks users to take specific photos (Engine bay, Undercarriage, Seat bolsters).

AI Grade Assessment: Using computer vision to detect paint chips, curb rash on wheels, or interior leather wear.

Value Impact Report: Specifically showing how much a "Grade B" interior is hurting the car's potential resale value compared to a "Grade A" car.

Recommended Directory Structure
Plaintext

my_garage/
├── migrations/
├── tests/
├── models.py          # Database schemas (Vehicle, Receipt, Part)
├── selectors.py       # get_vehicle_valuation(), list_pending_upgrades()
├── services.py        # process_receipt_with_ai(), calculate_market_drift()
├── tasks.py           # Celery tasks for background AI processing
├── urls.py
└── views.py           # Standard Django


Design Highlights
Financial Tracking: Every ServiceRecord and Upgrade contributes to the vehicle's total "spent" amount, which you'll compare against the current_market_value in your Service layer.

JSONField for OCR: By storing ocr_raw_data as a JSONField, you can keep the full output from your FastAPI OCR service without needing a rigid schema for every type of receipt.

Decoupled Grading: ConditionReport allows for multiple assessments over time (e.g., before and after a detail or restoration).

## Selectors Design Notes
Why this pattern works
Coalesce Utility: We use Coalesce to ensure that if a car has zero records, the selector returns 0.00 instead of None, preventing TypeError during math operations.

Decoupled Logic: Your Django Template or View just calls vehicle_get_build_summary(id). It doesn't need to know how equity is calculated or which database tables are involved.

Performance: All heavy lifting (Summation, Filtering) happens at the database level rather than in Python loops.

## Services Design NOtes

Key Service Principles Applied
Atomic Transactions (@transaction.atomic): We ensure that if we update a car's condition grade, the corresponding change to the current_market_value also happens. If one fails, the database rolls back both.

Error Handling: Using custom exceptions like VehicleServiceError allows your views to catch specific "business logic" errors and show helpful messages to the user.

Thin Views, Fat Services: Your Django views will now be incredibly simple. They will just grab a Vehicle and call vehicle_update_market_valuation(vehicle).