---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics, step-03-epic1-approved, step-03-epic2-approved, step-03-epic3-approved, step-04-final-validation]
status: complete
completedAt: '2026-06-02'
revisedAt: '2026-06-02'
revisionNote: >
  Revised to match actual codebase architecture (Phase 5 completed).
  Vehicle, Timepiece, and DynamicCollectionItem are all DynamicCollectionItem.
  GenericServiceRecord and GenericUpgrade serve all asset types via item FK.
  Epic 3 (Timepiece Upgrade Tracking) removed — upgrade CRUD already exists for
  all collection types via the collections: namespace. Epic count reduced from 4 to 3.
inputDocuments:
  - _bmad-output/planning-artifacts/prd-nfp.md
---

# my_garage — Net Financial Position (NFP): Epic Breakdown (Revised)

## Overview

This document provides the complete epic and story breakdown for the **Net Financial Position (NFP)** feature of my_garage. It supersedes the original version, which was written against a legacy architecture that was retired in Phase 5.

**Architectural reality (Phase 5 completed):**

| PRD assumption | Actual codebase |
|---|---|
| Separate `Vehicle`, `Timepiece`, `DynamicCollectionItem` ORM models | All assets are `DynamicCollectionItem` |
| Vehicle-specific `ServiceRecord` and `Upgrade` models | `GenericServiceRecord` (FK `item` → `DynamicCollectionItem`) |
| Timepiece needs GenericRelation for upgrades | `GenericUpgrade` (FK `item` → `DynamicCollectionItem`) already works for all items |
| Epic 3 (Timepiece upgrade tracking) needed | Upgrade CRUD fully exists for all collection types via `collections:` namespace |

**Active templates:** `collection_list.html`, `collection_item_detail.html`
**Template tags module:** `src/my_garage/templatetags/my_garage_extras.py`
**Upgrade views:** `src/my_garage/views.py` → `collection_item_add_upgrade`, `collection_item_edit_upgrade`, `collection_item_delete_upgrade`
**Active URL namespace:** `collections:`

**Tech Stack:** Django 5.2, Tailwind CSS (CDN), Alpine.js 3.x, PostgreSQL, existing selector/service/serializer pattern.

---

## Requirements Inventory

### Functional Requirements

- FR1: The system calculates NFP for any asset: `Market Value − (Purchase Price + Σ GenericServiceRecord.total_cost + Σ GenericUpgrade.cost [status=COMPLETED])`
- FR2: FR2 merged into FR1 — all DynamicCollectionItem use the same formula
- FR3: FR3 merged into FR1 — all DynamicCollectionItem use the same formula
- FR4: The system produces a cost-component breakdown per asset: purchase price, service costs total, upgrade costs total, cost basis, market value, net position
- FR5: The system represents NFP as null when market value is not set — no zero substitution, no error raised
- FR6: The system stores a cached `net_financial_position` value on `DynamicCollectionItem`
- FR7: The system refreshes cached NFP when any associated `GenericServiceRecord` is created, updated, or deleted
- FR8: The system refreshes cached NFP when any associated `GenericUpgrade` is created, updated, or deleted
- FR9: FR9 merged into FR7 — same signal handler covers all DynamicCollectionItem
- FR10: FR10 merged into FR8 — same signal handler covers all DynamicCollectionItem
- FR11: FR11 merged into FR8 — same signal handler covers all DynamicCollectionItem
- FR12: The collector can view a financial summary (cost basis, market value, net position) for each item in every collection list view
- FR13: FR13 merged into FR12
- FR14: FR14 merged into FR12
- FR15: The collector can distinguish gain from loss on any list row via both colour and symbol simultaneously — not colour alone
- FR16: The collector sees NFP displayed as unavailable — not zero, not error — when market value is unset
- FR17: The collector can view a full financial breakdown on each item's detail page: purchase price, service costs total, upgrade costs total, cost basis, market value, net position
- FR18: FR18 merged into FR17
- FR19: FR19 merged into FR17
- FR20: The collector sees contextual guidance when market value is unset, directing them to add a valuation
- FR21: The collector can view an aggregate NFP across all assets on the home dashboard
- FR22: The collector can view aggregate NFP broken down by collection type on the Insights page
- FR23: The collector can view per-collection-type NFP totals alongside existing portfolio allocation metrics on the Insights page
- FR24–FR28: **Removed** — Timepiece upgrade tracking via `GenericUpgrade` already fully implemented. All collection types, including Horology Salon, already have add/edit/delete/status upgrade views via `collections:collection_item_add_upgrade` etc.
- FR29: The system displays NFP values with sign prefix (`+`/`−`) and currency formatting; `—` when null
- FR30: NFP gain/loss signals use both colour and symbol — interpretable without colour perception
- FR31: All NFP monetary values have `aria-label` attributes describing value and meaning in plain language
- FR32: Interactive NFP elements (tooltips, hint links) are keyboard-navigable via `Tab` and activatable via `Enter`/`Space`

### Non-Functional Requirements

- NFR1: Collection list pages must not exhibit perceptible load time increase. NFP served from cached field — no aggregation at list render time.
- NFR2: NFP cache refresh completes within HTTP request/response cycle. Updated values visible on next page load.
- NFR3: Portfolio NFP aggregate uses a single `aggregate(Sum('net_financial_position'))` query over all `DynamicCollectionItem` for the user. Per-type breakdown uses `values('collection_type__name').annotate(...)`. Max 2 queries total. Query count regression test required.
- NFR4: NFP breakdown selector on detail pages permitted one additional aggregation query. Must optimise before shipping if user-perceptible degradation detected.
- NFR5: All views displaying NFP require `IsAuthenticated`. No NFP accessible to unauthenticated users.
- NFR6: All ORM queries filter by `owner=request.user`. No cross-user NFP visibility.
- NFR7: `refresh_item_nfp` validates asset ownership before writing.
- NFR8: NFP gain/loss indicators satisfy WCAG 2.1 SC 1.4.1 — dual signal (colour + symbol) required, per FR30.
- NFR9: All NFP monetary values rendered in HTML include `aria-label` with value and meaning in plain language.
- NFR10: Interactive NFP elements are keyboard-reachable (`Tab`) and activatable (`Enter`/`Space`) with visible Tailwind focus ring.
- NFR11: All new code passes `pixi run -- ruff check .` (zero errors) and `pixi run -- ruff format --check .` (zero diffs).
- NFR12: Existing test suite passes without regression (`pixi run pytest tests/unit/ tests/functional/ -x -q`).
- NFR13: Unit tests cover NFP calculation for all edge cases: nominal case, null market value, zero service records, zero upgrades, post-delete cache refresh.
- NFR14: Portfolio aggregate query bound (NFR3) verified by functional test using `CaptureQueriesContext`.
- NFR15: All model changes accompanied by generated migrations committed in the same changeset.

### Additional Implementation Notes

- `net_financial_position` nullable DecimalField added to `DynamicCollectionItem` + migration (next: `0012_nfp_field.py`)
- Signal handlers registered: `post_save` + `post_delete` on `GenericServiceRecord` and `GenericUpgrade`
- Cache refresh is synchronous within the HTTP request cycle (no Celery task)
- Portfolio aggregate: single `Sum('net_financial_position')` over `DynamicCollectionItem` owned by user
- Per-type breakdown: `values('collection_type__name').annotate(Sum('net_financial_position'))`
- Custom template filter `nfp_display` added to existing `my_garage_extras.py` — no new module
- All new UI uses existing Tailwind utility classes + luxury token palette — no new CSS
- Alpine.js for tooltip show/hide only — NFP values are server-rendered
- Brownfield project — existing selector/service architecture must be followed

### FR Coverage Map

| FR | Epic | Summary |
|---|---|---|
| FR1 | Epic 1 | Unified NFP formula for all DynamicCollectionItem |
| FR4 | Epic 1 | Cost-component breakdown selector |
| FR5 | Epic 1 | Null NFP when market value absent |
| FR6 | Epic 1 | Cached field on DynamicCollectionItem |
| FR7 | Epic 1 | GenericServiceRecord CUD refresh |
| FR8 | Epic 1 | GenericUpgrade CUD refresh |
| FR12 | Epic 2 | Collection list mini breakdown (all types) |
| FR15 | Epic 2 | Dual signal colour+symbol |
| FR16 | Epic 2 | Unavailable display |
| FR17 | Epic 2 | Detail page full breakdown |
| FR20 | Epic 2 | Market value missing guidance |
| FR29 | Epic 1 | nfp_display template filter |
| FR30 | Epic 1+2 | WCAG dual signal |
| FR31 | Epic 1+2 | aria-labels |
| FR32 | Epic 1+2 | Keyboard navigation |
| FR21 | Epic 3 | Home dashboard aggregate NFP |
| FR22 | Epic 3 | Insights page NFP by collection type |
| FR23 | Epic 3 | Insights per-type NFP totals |

---

## Epic List

1. **Epic 1: NFP Calculation, Cache, and Display Infrastructure** — The system calculates, caches, and auto-refreshes Net Financial Position for every `DynamicCollectionItem`. Establishes the `nfp_display` template filter and signal handlers that all subsequent epics depend on.
2. **Epic 2: Financial Display on List and Detail Views** — Collectors see per-item financial clarity in the collection list view and the item detail view. Depends on Epic 1.
3. **Epic 3: Portfolio Financial Aggregation** — Collectors see a single honest aggregate Net Financial Position on the home dashboard and a per-type breakdown on the Insights page. Depends on Epic 1.

---

## Epic 1: NFP Calculation, Cache, and Display Infrastructure

The system calculates, caches, and auto-refreshes Net Financial Position for every `DynamicCollectionItem`. This epic establishes the data layer and display primitives that all subsequent epics consume.

**FRs covered:** FR1, FR4, FR5, FR6, FR7, FR8, FR29, FR30, FR31, FR32
**NFRs covered:** NFR1, NFR2, NFR5, NFR6, NFR7, NFR11, NFR12, NFR13, NFR15

---

### Story 1.1: NFP Calculation, Cached Field, and Signal Handlers

As a collector,
I want the system to calculate and store my net financial position for every item automatically,
So that my financial data is always accurate and instantly available without manual calculation.

**Acceptance Criteria:**

**Given** a `DynamicCollectionItem` has `purchase_price`, `GenericServiceRecord` entries, and COMPLETED `GenericUpgrade` entries
**When** any associated `GenericServiceRecord` or `GenericUpgrade` is created, updated, or deleted
**Then** `DynamicCollectionItem.net_financial_position` is recalculated as:
`Market Value − (Purchase Price + Σ GenericServiceRecord.total_cost + Σ GenericUpgrade.cost [status=COMPLETED])`
**And** the recalculated value is persisted within the HTTP request/response cycle

**Given** a `DynamicCollectionItem` has `current_market_value = null`
**When** NFP is calculated
**Then** `net_financial_position` is stored as null — not zero, not an error

**Given** a `DynamicCollectionItem` has no `GenericServiceRecord` or `GenericUpgrade` entries
**When** NFP is calculated
**Then** `net_financial_position = current_market_value − purchase_price`

**Given** a `GenericServiceRecord` is deleted from a `DynamicCollectionItem`
**When** the deletion completes
**Then** `DynamicCollectionItem.net_financial_position` is recalculated via `post_delete` signal
**And** the stale value from before the deletion is no longer present

**Given** a `GenericUpgrade` with status WISHLIST, ORDERED, or IN_PROGRESS exists for an item
**When** NFP is calculated
**Then** that upgrade's cost is NOT included in the cost basis

**Given** new code is submitted
**When** the quality gate runs
**Then** unit tests pass for: nominal case, null market value, zero service records, zero upgrades, post-delete cache refresh, non-COMPLETED upgrade excluded
**And** `pixi run pytest tests/unit/ -x -q` passes with zero failures
**And** ruff check and ruff format --check report zero errors

**Technical notes:**
- Add `net_financial_position` nullable `DecimalField(max_digits=12, decimal_places=2)` to `DynamicCollectionItem` in `src/my_garage/models.py`
- Run `pixi run manage makemigrations` → creates `0012_nfp_field.py`
- Create `get_item_nfp_breakdown(item)` selector in `src/my_garage/api/selectors.py` → returns dict: `purchase_price`, `service_total`, `upgrade_total`, `cost_basis`, `market_value`, `net_position`
- Create `refresh_item_nfp(item)` service function in `src/my_garage/api/services.py` → recalculates and saves `net_financial_position`
- Register `post_save` + `post_delete` signal handlers on `GenericServiceRecord` and `GenericUpgrade` in `src/my_garage/api/services.py` (or a new `signals.py` in `src/my_garage/`)
- Wire signals in `src/my_garage/apps.py` `ready()` method
- `GenericUpgrade` has both `item` FK and a `content_type`/`object_id` GenericForeignKey — signal handler must handle both: check `instance.item` first, then fall back to `instance.content_object` if it's a `DynamicCollectionItem`
- Create `nfp_display` template filter in `src/my_garage/templatetags/my_garage_extras.py`: formats `Decimal` with sign prefix (`+`/`−`), currency formatting (`$X,XXX`), returns `—` for null — this filter is reused by Epic 2 templates

---

### Story 1.2: Backfill NFP for Existing Items

As a collector,
I want all existing items in my collection to have their NFP calculated when I deploy the feature,
So that I see accurate financial data immediately without needing to trigger a save on every item.

**Acceptance Criteria:**

**Given** the NFP migration has been applied and existing `DynamicCollectionItem` records have null `net_financial_position`
**When** the backfill management command runs
**Then** all `DynamicCollectionItem` records owned by any user have their `net_financial_position` calculated and saved
**And** items with null `current_market_value` remain null (not forced to zero)

**Given** the backfill command runs on an empty database
**When** it completes
**Then** it exits without error (zero items processed is a valid outcome)

**Given** new code is submitted
**When** the quality gate runs
**Then** a unit test verifies the backfill logic: create items with service records and upgrades, call the backfill function, assert `net_financial_position` is correct on each
**And** `pixi run pytest tests/unit/ -x -q` passes

**Technical notes:**
- Add `pixi run manage backfill_nfp` management command: `src/my_garage/management/commands/backfill_nfp.py`
- Command iterates all `DynamicCollectionItem` and calls `refresh_item_nfp(item)` for each
- Can use `--dry-run` flag to preview counts without writing
- This is a one-time deployment step; not scheduled

---

## Epic 2: Financial Display on List and Detail Views

Collectors see per-item financial clarity in the collection list view and full financial breakdown on the item detail view. The `nfp_display` filter from Epic 1 is used throughout. Epic 1 must be complete before this epic begins.

**FRs covered:** FR12, FR15, FR16, FR17, FR20, FR29, FR30, FR31, FR32
**NFRs covered:** NFR1, NFR4, NFR8, NFR9, NFR10, NFR11, NFR12

---

### Story 2.1: Collection List Mini NFP Breakdown

As a collector,
I want to see a financial summary for each item in my collection lists,
So that I can compare financial performance across my collection at a glance without clicking into each item.

**Acceptance Criteria:**

**Given** the collector views any collection list page (`/collections/<slug>/`)
**When** the page renders
**Then** each item row displays a mini financial breakdown: Cost Basis / Current Market Value / Net Position

**Given** an item has a positive net position
**When** the row renders
**Then** Net Position shows a `+` prefix and renders in green (e.g. `+$4,450`)
**And** the element has `aria-label="Net Position: gain of $4,450"`

**Given** an item has a negative net position
**When** the row renders
**Then** Net Position shows a `−` prefix and renders in red (e.g. `−$4,400`)
**And** the element has `aria-label="Net Position: loss of $4,400"`

**Given** an item has null `current_market_value`
**When** the row renders
**Then** Market Value and Net Position each display `—`
**And** the `aria-label` reads "Net Position: not calculated — market value not set"

**Given** the collector views the list on a mobile screen (< 640px)
**When** the page renders
**Then** the mini breakdown stacks vertically with Net Position badge remaining prominent

**Given** new code is submitted
**When** the quality gate runs
**Then** a functional test GETs a collection list with at least one item having real `GenericServiceRecord` and `GenericUpgrade` rows and asserts the mini breakdown is present in the response
**And** `pixi run pytest tests/functional/ -x -q` passes

**Technical notes:**
- Edit `src/my_garage/templates/my_garage/collection_list.html`
- NFP values come from the cached `item.net_financial_position` field — no extra queries
- Use the `nfp_display` filter from `my_garage_extras` for all value rendering
- Responsive: `sm:flex-row flex-col` stacking via Tailwind — no new CSS

---

### Story 2.2: Item Detail Full Financial Breakdown

As a collector,
I want to see a full financial breakdown on each item's detail page,
So that I understand exactly what has contributed to my true cost of ownership.

**Acceptance Criteria:**

**Given** the collector views any item detail page
**When** the Financial Position section renders
**Then** it shows: Purchase Price / Service Costs Total / Completed Upgrades Total / Cost Basis / Current Market Value / Net Position

**Given** an item has 4 service records totalling $5,200
**When** the detail page renders
**Then** Service Costs Total shows $5,200

**Given** an item has COMPLETED upgrades totalling $3,200 and WISHLIST upgrades totalling $1,500
**When** the detail page renders
**Then** Completed Upgrades Total shows $3,200
**And** the $1,500 wishlist amount is not included

**Given** an item has null `current_market_value`
**When** the detail page renders
**Then** Market Value and Net Position show `—`
**And** a tooltip reads "Add a valuation to calculate net position"
**And** the tooltip trigger is keyboard-accessible (`tabindex="0"`, `role="tooltip"`)

**Given** new code is submitted
**When** the quality gate runs
**Then** a functional test GETs the item detail page with real `GenericServiceRecord` and `GenericUpgrade` rows and asserts HTTP 200 with correct NFP breakdown values present in the response
**And** `pixi run pytest tests/functional/ -x -q` passes

**Technical notes:**
- Edit `src/my_garage/templates/my_garage/collection_item_detail.html`
- The detail view (`collection_item_detail` in `views.py`) must pass `nfp_breakdown` dict to template context by calling `get_item_nfp_breakdown(item)` from the selector
- Null-safe tooltip: Alpine.js `x-data` / `x-show` for tooltip visibility, `tabindex="0"` trigger span
- Use the `nfp_display` filter for all value rendering

---

## Epic 3: Portfolio Financial Aggregation

Collectors see a single honest aggregate Net Financial Position on the home dashboard and a per-collection-type breakdown on the Insights page. Uses efficient bulk aggregation — never per-item iteration. Epic 1 must be complete before this epic begins.

**FRs covered:** FR21, FR22, FR23
**NFRs covered:** NFR3, NFR11, NFR12, NFR14

---

### Story 3.1: Home Dashboard Aggregate NFP Card

As a collector,
I want to see my total net financial position on the home dashboard,
So that I can immediately understand whether my overall portfolio is gaining or losing value relative to everything I've spent on it.

**Acceptance Criteria:**

**Given** an authenticated collector opens the home dashboard at `/`
**When** the page renders
**Then** an aggregate NFP card is visible showing the total Net Financial Position across all `DynamicCollectionItem` owned by the user

**Given** the collector's portfolio has a positive aggregate NFP
**When** the home page renders
**Then** the aggregate NFP displays with a `+` prefix in green
**And** the `aria-label` reads "Total Net Financial Position: gain of $X"

**Given** the collector's portfolio has a negative aggregate NFP
**When** the home page renders
**Then** the aggregate NFP displays with a `−` prefix in red

**Given** the collector has no assets with market values set
**When** the home page renders
**Then** the aggregate NFP card shows `—` without error

**Given** the home page view executes the portfolio NFP query
**When** measured with `CaptureQueriesContext`
**Then** the NFP aggregation uses at most 1 additional query (a single `Sum` over `DynamicCollectionItem`)
**And** the query count does not grow as the number of items increases

**Given** new code is submitted
**When** the quality gate runs
**Then** a functional test asserts the aggregate NFP card is present in the authenticated home page response
**And** a query count test using `CaptureQueriesContext` asserts the NFP query is a single `Sum` aggregate
**And** `pixi run pytest tests/functional/ -x -q` passes

**Technical notes:**
- Add `get_portfolio_nfp_summary(user)` selector in `src/my_garage/api/selectors.py` using `DynamicCollectionItem.objects.filter(owner=user).aggregate(total=Sum('net_financial_position'))`
- Update home view to pass `portfolio_nfp` to template context
- Add NFP card to `src/my_garage/templates/pages/home.html` (or the active home template) alongside existing portfolio value card
- Confirm active home template path before editing

---

### Story 3.2: Insights Page NFP Breakdown by Collection Type

As a collector,
I want to see my net financial position broken down by collection type on the Insights page,
So that I can understand which parts of my collection are performing well as investments and which are costing more than they're worth.

**Acceptance Criteria:**

**Given** an authenticated collector navigates to `/insights/`
**When** the page renders
**Then** a Net Financial Position KPI card shows the portfolio-wide aggregate NFP

**Given** the collector has items across multiple collection types
**When** the Insights page renders
**Then** each collection type shows its NFP total alongside existing allocation metrics

**Given** a specific collection type has a positive NFP total
**When** the Insights page renders
**Then** that collection type's NFP shows `+` prefix in green

**Given** a specific collection type has a negative NFP total
**When** the Insights page renders
**Then** that collection type's NFP shows `−` prefix in red

**Given** a collection type has no items with market values set
**When** the Insights page renders
**Then** that collection type's NFP shows `—` without error or zero

**Given** the collector has no items
**When** the Insights page renders
**Then** all NFP values show `—` and no division errors occur (existing zero-asset guard preserved)

**Given** new code is submitted
**When** the quality gate runs
**Then** a functional test GETs `/insights/` and asserts the NFP KPI card and per-type NFP values are present in the response
**And** `pixi run pytest tests/functional/ -x -q` passes

**Technical notes:**
- Extend `get_portfolio_nfp_summary(user)` or add a companion selector that uses `.values('collection_type__name').annotate(nfp=Sum('net_financial_position'))` for the per-type breakdown
- Update the insights view to pass the per-type NFP breakdown to template context
- Edit `src/my_garage/templates/pages/insights.html` (confirm path) to add NFP KPI card and per-type NFP rows
