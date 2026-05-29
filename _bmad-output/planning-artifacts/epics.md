---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics, step-03-epic1-approved, step-03-epic2-approved, step-03-epic3-approved, step-03-epic4-approved, step-04-final-validation]
status: complete
completedAt: '2026-05-29'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
---

# my_garage — Net Financial Position (NFP): Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the **Net Financial Position (NFP)** feature of my_garage, decomposing requirements from the PRD into implementable stories. No Architecture or UX design documents exist; technical decisions are captured in the PRD scoping section and follow established codebase patterns.

**Tech Stack:** Django 5.2, Tailwind CSS (CDN), Alpine.js 3.x, PostgreSQL, existing selector/service/serializer pattern.

---

## Requirements Inventory

### Functional Requirements

- FR1: The system calculates NFP for any Vehicle: `Market Value − (Purchase Price + Σ ServiceRecord.total_cost + Σ Upgrade.cost [INSTALLED])`
- FR2: The system calculates NFP for any DynamicCollectionItem: `Market Value − (Purchase Price + Σ GenericServiceRecord.total_cost + Σ GenericUpgrade.cost [COMPLETED])`
- FR3: The system calculates NFP for any Timepiece: `Market Value − (Purchase Price + Σ GenericUpgrade.cost [COMPLETED])` — service costs excluded until migration story ships
- FR4: The system produces a cost-component breakdown per asset: purchase price, service costs total, upgrade costs total, cost basis, market value, net position
- FR5: The system represents NFP as null when market value is not set — no zero substitution, no error raised
- FR6: The system stores a cached `net_financial_position` value on each Vehicle, Timepiece, and DynamicCollectionItem
- FR7: The system refreshes a Vehicle's cached NFP when any associated ServiceRecord is created, updated, or deleted
- FR8: The system refreshes a Vehicle's cached NFP when any associated Upgrade is created, updated, or deleted
- FR9: The system refreshes a DynamicCollectionItem's cached NFP when any associated GenericServiceRecord is created, updated, or deleted
- FR10: The system refreshes a DynamicCollectionItem's cached NFP when any associated GenericUpgrade is created, updated, or deleted
- FR11: The system refreshes a Timepiece's cached NFP when any associated GenericUpgrade is created, updated, or deleted
- FR12: The collector can view a financial summary (cost basis, market value, net position) for each Vehicle in the Vehicle list
- FR13: The collector can view a financial summary for each Timepiece in the Timepiece list
- FR14: The collector can view a financial summary for each item in any DynamicCollectionItem list
- FR15: The collector can distinguish gain from loss on any list row via both colour and symbol simultaneously — not colour alone
- FR16: The collector sees NFP displayed as unavailable — not zero, not error — when market value is unset
- FR17: The collector can view a full financial breakdown on the Vehicle detail page: each cost component, cost basis, market value, net position
- FR18: The collector can view a full financial breakdown on the Timepiece detail page: purchase price, completed upgrade costs, cost basis, market value, net position
- FR19: The collector can view a full financial breakdown on the DynamicCollectionItem detail page: each cost component, cost basis, market value, net position
- FR20: The collector sees contextual guidance when market value is unset, directing them to add a valuation
- FR21: The collector can view an aggregate NFP across all assets on the home dashboard
- FR22: The collector can view aggregate NFP broken down by asset type on the Insights page
- FR23: The collector can view per-asset-type NFP totals alongside existing portfolio allocation metrics on the Insights page
- FR24: The collector can add a GenericUpgrade project to a Timepiece (name, brand, part number, status, cost, ordered date, completion date, notes)
- FR25: The collector can edit an existing Timepiece upgrade project
- FR26: The collector can delete a Timepiece upgrade project
- FR27: The collector can advance a Timepiece upgrade through: Wishlist → Ordered → In Progress → Completed → Cancelled
- FR28: The collector can view all upgrade projects for a Timepiece on the Timepiece detail page
- FR29: The system displays NFP values with sign prefix (`+`/`−`) and currency formatting; `—` when null
- FR30: NFP gain/loss signals use both colour and symbol — interpretable without colour perception
- FR31: All NFP monetary values have `aria-label` attributes describing value and meaning in plain language
- FR32: Interactive NFP elements (tooltips, hint links) are keyboard-navigable via `Tab` and activatable via `Enter`/`Space`

### Non-Functional Requirements

- NFR1: Asset list pages must not exhibit perceptible load time increase. NFP served from cached field — no aggregation at list render time.
- NFR2: NFP cache refresh completes within HTTP request/response cycle. Updated values visible on next page load.
- NFR3: Portfolio NFP aggregate uses `aggregate(Sum(...))` per asset type — max 3 queries total. Query count regression test required.
- NFR4: NFP breakdown selector on detail pages permitted one additional aggregation query. Must optimise before shipping if user-perceptible degradation detected.
- NFR5: All views displaying NFP require `IsAuthenticated`. No NFP accessible to unauthenticated users.
- NFR6: All ORM queries filter by `owner=request.user`. No cross-user NFP visibility.
- NFR7: `refresh_asset_nfp` validates asset ownership before writing.
- NFR8: NFP gain/loss indicators satisfy WCAG 2.1 SC 1.4.1 — dual signal (colour + symbol) required.
- NFR9: All NFP monetary values include `aria-label` with value and meaning in plain language.
- NFR10: Interactive NFP elements keyboard-reachable and activatable with visible focus ring.
- NFR11: All new code passes ruff check and format (zero errors/diffs).
- NFR12: Existing 304-test suite passes without regression.
- NFR13: Unit tests cover NFP calculation for all 3 asset types: 5 edge case scenarios.
- NFR14: Portfolio aggregate query bound verified by functional test using `CaptureQueriesContext`.
- NFR15: All model changes accompanied by generated migrations in the same changeset.

### Additional Requirements

- `net_financial_position` nullable `DecimalField` added to `Vehicle`, `Timepiece`, `DynamicCollectionItem` models
- `GenericRelation` added to `Timepiece` model pointing to `GenericUpgrade` — no migration required (GenericFK lives on GenericUpgrade)
- Django signal handlers registered: `post_save` + `post_delete` on `ServiceRecord`, `Upgrade`, `GenericServiceRecord`, `GenericUpgrade`
- Cache refresh is synchronous within the HTTP request cycle (no Celery task)
- Portfolio aggregate: `aggregate(Sum('net_financial_position'))` per asset type (max 3 queries)
- Custom template filter `nfp_display` registered in existing `my_garage_tags` module
- All new UI uses existing Tailwind utility classes + luxury token palette — no new CSS
- Alpine.js for tooltip show/hide only — NFP values are server-rendered
- Timepiece service record tracking is explicitly out of scope (separate migration story)
- Brownfield project — existing selector/service/serializer architecture must be followed
- No starter template — work directly in the existing codebase

### FR Coverage Map

| FR | Epic | Summary |
|---|---|---|
| FR1 | Epic 1 | Vehicle NFP formula |
| FR2 | Epic 2 | DynamicCollectionItem NFP formula |
| FR3 | Epic 2 | Timepiece NFP formula (upgrades only) |
| FR4 | Epic 1+2 | Cost-component breakdown (established Epic 1, extended Epic 2) |
| FR5 | Epic 1 | Null NFP when market value absent (established for all) |
| FR6 | Epic 1+2 | Cached field — Vehicle in Epic 1, Collection+Timepiece in Epic 2 |
| FR7 | Epic 1 | Vehicle ServiceRecord CUD refresh |
| FR8 | Epic 1 | Vehicle Upgrade CUD refresh |
| FR9 | Epic 2 | DynamicCollectionItem GenericServiceRecord CUD refresh |
| FR10 | Epic 2 | DynamicCollectionItem GenericUpgrade CUD refresh |
| FR11 | Epic 2 | Timepiece GenericUpgrade CUD refresh |
| FR12 | Epic 1 | Vehicle list mini breakdown |
| FR13 | Epic 2 | Timepiece list mini breakdown |
| FR14 | Epic 2 | DynamicCollectionItem list mini breakdown |
| FR15 | Epic 1 | Dual signal colour+symbol (established for all) |
| FR16 | Epic 1 | Unavailable display (established for all) |
| FR17 | Epic 1 | Vehicle detail full breakdown |
| FR18 | Epic 2 | Timepiece detail full breakdown |
| FR19 | Epic 2 | DynamicCollectionItem detail full breakdown |
| FR20 | Epic 1 | Market value missing guidance (established for all) |
| FR21 | Epic 4 | Home dashboard aggregate NFP |
| FR22 | Epic 4 | Insights page NFP by asset type |
| FR23 | Epic 4 | Insights per-type NFP totals |
| FR24 | Epic 3 | Timepiece upgrade add |
| FR25 | Epic 3 | Timepiece upgrade edit |
| FR26 | Epic 3 | Timepiece upgrade delete |
| FR27 | Epic 3 | Timepiece upgrade status flow |
| FR28 | Epic 3 | Timepiece detail Projects tab |
| FR29 | Epic 1 | nfp_display template filter (established for all) |
| FR30 | Epic 1 | WCAG dual signal (established for all) |
| FR31 | Epic 1 | aria-labels (established for all) |
| FR32 | Epic 1 | Keyboard navigation (established for all) |

---

## Epic List

1. **Epic 1: Vehicle Financial Position** — Collectors can see the true, all-in financial position for every Vehicle in list rows and on detail pages. Establishes NFP calculation, caching, signal handlers, and all display/accessibility patterns reused by subsequent epics.
2. **Epic 2: Collection & Timepiece Financial Position** — Collectors see the same honest financial clarity for every DynamicCollectionItem and Timepiece that they see for Vehicles.
3. **Epic 3: Timepiece Upgrade Tracking** — Collectors can add, manage, and track upgrade projects for Timepieces — identical experience to DynamicCollectionItem upgrades.
4. **Epic 4: Portfolio Financial Aggregation** — Collectors see a single honest aggregate Net Financial Position across their entire portfolio on the home dashboard and Insights page.

---

## Epic 1: Vehicle Financial Position

Collectors can see the true, all-in financial position for every Vehicle — in list rows and on detail pages. This epic establishes the NFP calculation layer, cache mechanism, signal handlers, and display/accessibility patterns that all subsequent epics extend.

**FRs covered:** FR1, FR4, FR5, FR6 (Vehicle), FR7, FR8, FR12, FR15, FR16, FR17, FR20, FR29, FR30, FR31, FR32

---

### Story 1.1: Vehicle NFP Calculation and Cache

As a collector,
I want the system to calculate and store my vehicle's net financial position automatically,
So that my financial data is always accurate and instantly available without manual calculation.

**Acceptance Criteria:**

**Given** a Vehicle has purchase_price, ServiceRecord entries, and INSTALLED Upgrade entries
**When** any associated ServiceRecord or Upgrade is created, updated, or deleted
**Then** Vehicle.net_financial_position is recalculated as: Market Value − (Purchase Price + Σ ServiceRecord.total_cost + Σ Upgrade.cost [status=INSTALLED])
**And** the recalculated value is persisted within the HTTP request/response cycle

**Given** a Vehicle has current_market_value = null
**When** NFP is calculated
**Then** net_financial_position is stored as null — not zero, not an error

**Given** a Vehicle has no ServiceRecord or Upgrade entries
**When** NFP is calculated
**Then** net_financial_position = current_market_value − purchase_price

**Given** a ServiceRecord is deleted from a Vehicle
**When** the deletion completes
**Then** Vehicle.net_financial_position is recalculated via post_delete signal
**And** the stale value from before the deletion is no longer present

**Given** new code is submitted
**When** the quality gate runs
**Then** unit tests pass for: nominal case, null market value, zero service records, zero upgrades, and post-delete cache refresh
**And** `pixi run pytest tests/unit/ -x -q` passes with zero failures
**And** ruff check and ruff format --check report zero errors

**Technical notes:**
- Add `net_financial_position` nullable DecimalField to Vehicle model + migration
- Create `get_vehicle_nfp_breakdown(vehicle)` selector in `api/selectors.py`
- Create `refresh_asset_nfp(asset)` service function in `api/services.py`
- Register `post_save` + `post_delete` signal handlers on ServiceRecord and Upgrade
- Create `nfp_display` template filter in `my_garage_tags` (sign prefix, currency format, `—` null fallback) — reused by all subsequent epics

---

### Story 1.2: Vehicle List Financial Display

As a collector,
I want to see a financial summary for each vehicle in my vehicle list,
So that I can compare financial performance across my fleet at a glance.

**Acceptance Criteria:**

**Given** the collector views the Vehicle list page
**When** the page renders
**Then** each vehicle row displays a mini financial breakdown: Cost Basis / Current Market Value / Net Position

**Given** a vehicle has a positive net position
**When** the row renders
**Then** Net Position shows a `+` prefix and renders in green (e.g. `+$4,450`)
**And** the element has `aria-label="Net Position: gain of $4,450"`

**Given** a vehicle has a negative net position
**When** the row renders
**Then** Net Position shows a `−` prefix and renders in red (e.g. `−$4,400`)
**And** the element has `aria-label="Net Position: loss of $4,400"`

**Given** a vehicle has null current_market_value
**When** the row renders
**Then** Market Value and Net Position each display `—`
**And** no zero values or errors appear
**And** the aria-label reads "Net Position: not calculated — market value not set"

**Given** the collector views the list on a mobile screen (< 640px)
**When** the page renders
**Then** the mini breakdown stacks vertically with Net Position badge remaining prominent

**Given** new code is submitted
**When** the quality gate runs
**Then** a functional test GETs the vehicle list with at least one vehicle having real ServiceRecord rows and asserts the mini breakdown is present in the response
**And** `pixi run pytest tests/functional/ -x -q` passes

---

### Story 1.3: Vehicle Detail Financial Breakdown

As a collector,
I want to see a full financial breakdown on my vehicle's detail page,
So that I understand exactly what has contributed to my true cost of ownership.

**Acceptance Criteria:**

**Given** the collector views a Vehicle detail page
**When** the Financial Position section renders
**Then** it shows: Purchase Price / Service Costs Total / Completed Upgrades Total / Cost Basis / Current Market Value / Net Position

**Given** a vehicle has 4 service records totalling $5,200
**When** the detail page renders
**Then** Service Costs Total shows $5,200

**Given** a vehicle has INSTALLED upgrades totalling $3,200 and WISHLIST upgrades totalling $1,500
**When** the detail page renders
**Then** Completed Upgrades Total shows $3,200
**And** the $1,500 wishlist amount is not included

**Given** a vehicle has null current_market_value
**When** the detail page renders
**Then** Market Value and Net Position show `—`
**And** a tooltip reads "Add a valuation to calculate net position"
**And** the tooltip trigger is keyboard-accessible (tabindex="0", role="tooltip")

**Given** new code is submitted
**When** the quality gate runs
**Then** a functional test GETs the vehicle detail page with real ServiceRecord and Upgrade rows and asserts HTTP 200 with correct NFP breakdown values
**And** `pixi run pytest tests/functional/ -x -q` passes

---

## Epic 2: Collection & Timepiece Financial Position

Collectors see the same honest financial clarity for every DynamicCollectionItem and Timepiece that they see for Vehicles. The `nfp_display` filter and display patterns from Epic 1 are reused throughout.

**FRs covered:** FR2, FR3, FR4 (extension), FR6 (Collection+Timepiece), FR9, FR10, FR11, FR13, FR14, FR18, FR19

---

### Story 2.1: DynamicCollectionItem NFP Calculation and Cache

As a collector,
I want the system to calculate and store the net financial position for every item in my collections,
So that my collection investments reflect the true cost including services and completed upgrades.

**Acceptance Criteria:**

**Given** a DynamicCollectionItem has purchase_price, GenericServiceRecord entries, and COMPLETED GenericUpgrade entries
**When** any associated GenericServiceRecord or GenericUpgrade is created, updated, or deleted
**Then** DynamicCollectionItem.net_financial_position is recalculated as: Market Value − (Purchase Price + Σ GenericServiceRecord.total_cost + Σ GenericUpgrade.cost [status=COMPLETED])
**And** the recalculated value is persisted within the HTTP request/response cycle

**Given** a DynamicCollectionItem has current_market_value = null
**When** NFP is calculated
**Then** net_financial_position is stored as null

**Given** a GenericServiceRecord is deleted from a DynamicCollectionItem
**When** the deletion completes
**Then** DynamicCollectionItem.net_financial_position recalculates via post_delete signal

**Given** a GenericUpgrade with status WISHLIST, ORDERED, or IN_PROGRESS exists for an item
**When** NFP is calculated
**Then** that upgrade's cost is NOT included
**And** only COMPLETED upgrades contribute to cost basis

**Given** new code is submitted
**When** the quality gate runs
**Then** unit tests pass for: nominal case, null market value, zero records, zero upgrades, post-delete cache refresh
**And** `pixi run pytest tests/unit/ -x -q` passes

**Technical notes:**
- Add `net_financial_position` nullable DecimalField to DynamicCollectionItem + migration
- Create `get_collection_item_nfp_breakdown(item)` selector in `api/selectors.py`
- Register `post_save` + `post_delete` on GenericServiceRecord and GenericUpgrade (filtered by content_type to DynamicCollectionItem)

---

### Story 2.2: Timepiece NFP Calculation and Cache

As a collector,
I want the system to calculate and store the net financial position for every timepiece based on purchase price and completed upgrade costs,
So that my watch investments show an honest cost basis even before full service record tracking is available.

**Acceptance Criteria:**

**Given** a Timepiece has purchase_price and COMPLETED GenericUpgrade entries via GenericRelation
**When** any associated GenericUpgrade is created, updated, or deleted
**Then** Timepiece.net_financial_position is recalculated as: Market Value − (Purchase Price + Σ GenericUpgrade.cost [status=COMPLETED])
**And** the recalculated value is persisted within the HTTP request/response cycle

**Given** a Timepiece has no COMPLETED GenericUpgrade entries
**When** NFP is calculated
**Then** net_financial_position = current_market_value − purchase_price

**Given** a Timepiece has current_market_value = null
**When** NFP is calculated
**Then** net_financial_position is stored as null

**Given** a GenericUpgrade linked to a Timepiece is deleted
**When** the deletion completes
**Then** Timepiece.net_financial_position recalculates via post_delete signal

**Given** new code is submitted
**When** the quality gate runs
**Then** unit tests pass for: nominal case, null market value, zero upgrades, post-delete cache refresh
**And** `pixi run pytest tests/unit/ -x -q` passes

**Technical notes:**
- Add `net_financial_position` nullable DecimalField to Timepiece + migration
- Add `GenericRelation` to Timepiece model pointing to GenericUpgrade (no migration — GenericFK lives on GenericUpgrade)
- Create `get_timepiece_nfp_breakdown(timepiece)` selector
- Register `post_save` + `post_delete` on GenericUpgrade filtered by content_type to Timepiece

---

### Story 2.3: DynamicCollectionItem List and Detail Financial Display

As a collector,
I want to see a financial summary per item in my collection lists and a full breakdown on each item's detail page,
So that I can assess financial performance of every collection item at a glance and in depth.

**Acceptance Criteria:**

**Given** the collector views a DynamicCollectionItem list page
**When** the page renders
**Then** each item row displays a mini financial breakdown: Cost Basis / Current Market Value / Net Position with `+`/`−` prefix and green/red colour coding

**Given** an item has null current_market_value
**When** the list row renders
**Then** Market Value and Net Position display `—` with appropriate aria-labels

**Given** the collector views a DynamicCollectionItem detail page
**When** the Financial Position section renders
**Then** it shows: Purchase Price / Service Costs Total / Completed Upgrades Total / Cost Basis / Current Market Value / Net Position

**Given** an item has 1 service record ($25) and 1 COMPLETED upgrade ($180)
**When** the detail page renders
**Then** Service Costs Total = $25, Completed Upgrades Total = $180, Cost Basis = Purchase Price + $205

**Given** an item has null current_market_value
**When** the detail page renders
**Then** a tooltip "Add a valuation to calculate net position" is displayed and keyboard-accessible

**Given** new code is submitted
**When** the quality gate runs
**Then** functional tests cover list view (mini breakdown present) and detail view (full breakdown with correct values) with real GenericServiceRecord and GenericUpgrade rows
**And** `pixi run pytest tests/functional/ -x -q` passes

---

### Story 2.4: Timepiece List and Detail Financial Display

As a collector,
I want to see a financial summary per timepiece in my Horology Salon list and a full breakdown on each timepiece's detail page,
So that I can track watch investment performance alongside my other assets.

**Acceptance Criteria:**

**Given** the collector views the Timepiece list page
**When** the page renders
**Then** each timepiece row displays a mini financial breakdown: Cost Basis / Current Market Value / Net Position with `+`/`−` prefix and green/red colour coding

**Given** a timepiece has null current_market_value
**When** the list row renders
**Then** Market Value and Net Position display `—`

**Given** the collector views a Timepiece detail page
**When** the Financial Position section renders
**Then** it shows: Purchase Price / Completed Upgrades Total / Cost Basis / Current Market Value / Net Position
**And** there is no Service Costs row (service record tracking not yet available for Timepieces)

**Given** a timepiece has a COMPLETED upgrade of $180
**When** the detail page renders
**Then** Completed Upgrades Total = $180
**And** Cost Basis = Purchase Price + $180

**Given** a timepiece has null current_market_value
**When** the detail page renders
**Then** a tooltip "Add a valuation to calculate net position" is displayed

**Given** new code is submitted
**When** the quality gate runs
**Then** functional tests cover Timepiece list view (mini breakdown present) and detail view (correct breakdown, no Service Costs row) with real GenericUpgrade rows
**And** `pixi run pytest tests/functional/ -x -q` passes

---

## Epic 3: Timepiece Upgrade Tracking

Collectors can add, manage, and track upgrade projects for Timepieces using the exact same UI pattern as DynamicCollectionItem upgrades. The GenericRelation established in Story 2.2 is the data foundation; this epic builds the complete interaction layer on top.

**FRs covered:** FR24, FR25, FR26, FR27, FR28

---

### Story 3.1: Add and View Timepiece Upgrade Projects

As a collector,
I want to add upgrade projects to my timepieces and see them on the detail page,
So that I can plan and track modifications to my watches the same way I do for my other collections.

**Acceptance Criteria:**

**Given** the collector is on a Timepiece detail page
**When** they view the page
**Then** a Projects section is visible with an "+ Add Project" button

**Given** the collector clicks "+ Add Project" on a Timepiece detail page
**When** the form renders
**Then** it includes fields: name, brand, part number, status (Wishlist / Ordered / In Progress / Completed / Cancelled), cost, ordered date, completion date, notes
**And** the form layout and styling matches the DynamicCollectionItem upgrade form

**Given** the collector submits a valid upgrade form for a Timepiece
**When** the form saves
**Then** the upgrade appears in the Projects section of the Timepiece detail page
**And** a success toast notification confirms "Project added"
**And** the Timepiece's net_financial_position does NOT change (new projects default to Wishlist — not COMPLETED)

**Given** the collector views the Timepiece detail page
**When** the Projects section renders
**Then** all upgrade projects for that Timepiece are listed with: name, status badge, cost, ordered date, completion date

**Given** new code is submitted
**When** the quality gate runs
**Then** a functional test POSTs a new upgrade for a Timepiece and asserts HTTP 302 redirect and the upgrade appears in the detail page response
**And** `pixi run pytest tests/functional/ -x -q` passes

**Technical notes:**
- Add upgrade add view at `/timepieces/<id>/add-upgrade/`
- Uses existing GenericUpgrade model via GenericRelation on Timepiece — no model changes required

---

### Story 3.2: Edit, Delete, and Status Progression for Timepiece Upgrades

As a collector,
I want to edit, delete, and advance the status of my timepiece upgrade projects,
So that I can keep my project tracker current as I research, order, and complete modifications.

**Acceptance Criteria:**

**Given** the collector clicks "Edit" on a Timepiece upgrade project
**When** the edit form renders
**Then** it is pre-populated with all existing field values

**Given** the collector changes the upgrade status from IN_PROGRESS to COMPLETED and saves
**When** the save completes
**Then** the upgrade status updates to COMPLETED
**And** the Timepiece's net_financial_position is recalculated to include this upgrade's cost
**And** the updated NFP is visible on the Timepiece detail page on reload

**Given** the collector changes a COMPLETED upgrade status back to IN_PROGRESS
**When** the save completes
**Then** the Timepiece's net_financial_position recalculates to EXCLUDE this upgrade's cost

**Given** the collector confirms deletion of a Timepiece upgrade
**When** the deletion completes
**Then** the upgrade is removed from the Projects section
**And** if the deleted upgrade was COMPLETED, the Timepiece's net_financial_position recalculates to exclude its cost
**And** a success toast confirms "Project deleted"

**Given** an upgrade moves through: Wishlist → Ordered → In Progress → Completed → Cancelled
**When** each status change saves
**Then** only COMPLETED status causes the cost to count toward NFP
**And** CANCELLED status does NOT count toward NFP

**Given** new code is submitted
**When** the quality gate runs
**Then** functional tests cover: edit saves correctly, COMPLETED status triggers NFP recalculation, deletion of COMPLETED upgrade reduces NFP
**And** `pixi run pytest tests/functional/ -x -q` passes

**Technical notes:**
- Add upgrade edit view: `/timepieces/<id>/upgrade/<upgrade-id>/edit/`
- Add upgrade delete view: `/timepieces/<id>/upgrade/<upgrade-id>/delete/`
- Signal handler from Story 2.2 covers post_save/post_delete on GenericUpgrade — NFP refresh is automatic, no additional backend work required

---

## Epic 4: Portfolio Financial Aggregation

Collectors see a single honest aggregate Net Financial Position across their entire portfolio on the home dashboard and Insights page. Depends on the `net_financial_position` cached field being present on all three asset models (Epics 1 and 2). Uses efficient bulk aggregation — never per-asset iteration.

**FRs covered:** FR21, FR22, FR23

---

### Story 4.1: Home Dashboard Aggregate NFP Card

As a collector,
I want to see my total net financial position on the home dashboard,
So that I can immediately understand whether my overall portfolio is gaining or losing value relative to everything I've spent on it.

**Acceptance Criteria:**

**Given** an authenticated collector opens the home dashboard at `/`
**When** the page renders
**Then** an aggregate NFP card is visible showing the total Net Financial Position across all Vehicles, Timepieces, and DynamicCollectionItems

**Given** the collector's portfolio has a positive aggregate NFP
**When** the home page renders
**Then** the aggregate NFP displays with a `+` prefix in green
**And** the aria-label reads "Total Net Financial Position: gain of $X"

**Given** the collector's portfolio has a negative aggregate NFP
**When** the home page renders
**Then** the aggregate NFP displays with a `−` prefix in red

**Given** the collector has no assets with market values set
**When** the home page renders
**Then** the aggregate NFP card shows `—` without error

**Given** the home page view executes the portfolio NFP query
**When** measured with CaptureQueriesContext
**Then** the NFP aggregation uses at most 3 queries total (one per asset type)
**And** the query count does not grow as the number of assets increases

**Given** new code is submitted
**When** the quality gate runs
**Then** a functional test asserts the aggregate NFP card is present in the authenticated home page response
**And** a query count test using CaptureQueriesContext asserts NFP queries are bounded at 3
**And** `pixi run pytest tests/functional/ -x -q` passes

**Technical notes:**
- Add `get_portfolio_nfp_summary(user)` selector using `aggregate(Sum('net_financial_position'))` per asset type
- Update home view to pass NFP summary to template context
- Add NFP card to `templates/pages/home.html` alongside existing portfolio value

---

### Story 4.2: Insights Page NFP Breakdown

As a collector,
I want to see my net financial position broken down by asset type on the Insights page,
So that I can understand which parts of my collection are performing well as investments and which are costing more than they're worth.

**Acceptance Criteria:**

**Given** an authenticated collector navigates to `/insights/`
**When** the page renders
**Then** a Net Financial Position KPI card shows the portfolio-wide aggregate NFP

**Given** the collector has assets across Vehicles, Timepieces, and DynamicCollectionItems
**When** the Insights page renders
**Then** each asset type shows its NFP total alongside existing allocation metrics (value, count, equity, percentage)

**Given** a specific asset type has a positive NFP total
**When** the Insights page renders
**Then** that asset type's NFP shows `+` prefix in green

**Given** a specific asset type has a negative NFP total
**When** the Insights page renders
**Then** that asset type's NFP shows `−` prefix in red

**Given** an asset type has no assets with market values set
**When** the Insights page renders
**Then** that asset type's NFP shows `—` without error or zero

**Given** the collector has no items
**When** the Insights page renders
**Then** all NFP values show `—` and no division errors occur (existing zero-asset guard preserved)

**Given** new code is submitted
**When** the quality gate runs
**Then** a functional test GETs `/insights/` and asserts the NFP KPI card and per-type NFP values are present
**And** `pixi run pytest tests/functional/ -x -q` passes
