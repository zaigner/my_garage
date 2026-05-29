---
stepsCompleted: [step-01-init, step-02-discovery, step-02b-vision, step-02c-executive-summary, step-03-success, step-04-journeys, step-05-domain-skipped, step-06-innovation-skipped, step-07-project-type, step-08-scoping, step-09-functional, step-10-nonfunctional, step-11-polish, step-12-complete]
status: complete
completedAt: '2026-05-29'
inputDocuments:
  - _bmad/_memory/project-context.md
  - docs/IMPLEMENTATION_PLAN.md
  - docs/SERVICE_RECORDS_GUIDE.md
  - docs/UPGRADES_KANBAN_GUIDE.md
  - docs/UX-enhancement.md
  - docs/schemas/FIELD_TYPES.md
  - _bmad-output/planning-artifacts/epics-ux-enhancement-suite.md
workflowType: prd
project: my_garage
author: Zaigner77
date: '2026-05-29'
classification:
  projectType: web_app
  domain: personal_finance_asset_management
  complexity: medium
  projectContext: brownfield
---

# Product Requirements Document — my_garage

**Feature:** Net Financial Position (NFP)
**Author:** Zaigner77
**Date:** 2026-05-29

---

## Executive Summary

my_garage is a Django 5.2 personal asset management platform tracking vehicles, timepieces, and user-defined dynamic collections as financial investments. This PRD defines the **Net Financial Position (NFP)** feature — a cross-cutting financial clarity layer replacing the platform's incomplete `equity` calculation (`current_market_value - purchase_price`) with a true, all-in cost basis: purchase price plus every dollar spent on services and completed upgrades.

**NFP formula:**

```
Total Cost Basis = Purchase Price
                 + Σ(service record costs)
                 + Σ(upgrade costs | status = INSTALLED or COMPLETED)

Net Position     = Current Market Value − Total Cost Basis
                   positive = gain  |  negative = loss
```

The feature surfaces NFP at three levels:

1. **List views** — per-row mini breakdown: Cost Basis / Market Value / Net Position, colour-coded and symbol-prefixed, across all asset type list pages
2. **Detail views** — full itemised financial breakdown on each asset's detail page
3. **Portfolio level** — aggregate NFP on the home dashboard (`/`) and Insights page (`/insights/`)

**Asset type coverage:**

| Asset Type | Service Costs | Upgrade Costs | NFP Completeness |
|---|---|---|---|
| Vehicle | `ServiceRecord` (existing) | `Upgrade` INSTALLED (existing) | Full |
| DynamicCollectionItem | `GenericServiceRecord` (existing) | `GenericUpgrade` COMPLETED (existing) | Full |
| Timepiece | Deferred to migration story | `GenericUpgrade` COMPLETED via new `GenericRelation` | Partial — upgrades only |

Timepiece service record tracking is deferred to a separate migration story that will refactor `GenericServiceRecord` to a true `GenericForeignKey` and unify all asset types under a single service record model — avoiding new Timepiece-specific models and maintaining a single pattern across the application.

### What Makes This Special

Most asset trackers show collectors what their assets are worth. my_garage's NFP feature shows what they *truly cost* — surfacing the gap between purchase price and all-in ownership spend. This transforms the platform from a valuation dashboard into an honest investment ledger.

The core insight: a vehicle up $8,000 in market value but requiring $12,000 in service and upgrades tells a different investment story than one requiring $2,000. Seeing that difference at a glance — in list rows and in depth on detail pages — is the feature's value.

---

## Project Classification

| Attribute | Value |
|---|---|
| Project Type | Web App — Django MPA (templates + Alpine.js + Tailwind CSS) |
| Domain | Personal Finance / Asset Management (no regulatory compliance) |
| Complexity | Medium — cross-cutting calculation across 3 asset types, multiple views and templates across 3 URL namespaces |
| Project Context | Brownfield — mature codebase, established selector/service pattern, 304+ passing tests, financial fields present on all models |

---

## Success Criteria

### User Success

- Every asset list view shows a mini financial breakdown — Cost Basis / Market Value / Net Position — without additional navigation.
- Net Position uses dual signalling: `+$4,450` in green for gain, `−$4,400` in red for loss, `—` neutral for unavailable. Legible without reading the numbers.
- Every asset detail page shows a full financial breakdown: Purchase Price, Service Costs Total, Upgrade Costs Total, Cost Basis, Current Market Value, Net Position.
- The home dashboard and Insights page show aggregate NFP summing correctly across all Vehicles, Timepieces, and DynamicCollectionItems.
- Timepiece upgrade tracking UI is identical to the DynamicCollectionItem upgrade UI — no inconsistency between asset types.
- A user with real assets, real service records, and real completed upgrades sees numbers that honestly reflect their total investment without manual calculation.

### Personal Success

- The platform is an honest investment ledger, not just a valuation dashboard.
- The Insights page aggregate NFP answers: "Is my collection worth what I've put into it?"

### Technical Success

- `net_financial_position` is a nullable `DecimalField` cached on each asset model, recalculated synchronously via `post_save` and `post_delete` signals on all supporting models.
- Cache invalidation triggers:
  - Vehicle: `ServiceRecord` CUD + `Upgrade` CUD
  - DynamicCollectionItem: `GenericServiceRecord` CUD + `GenericUpgrade` CUD
  - Timepiece: `GenericUpgrade` CUD (service records deferred to migration story)
- `GenericRelation` added to `Timepiece` model pointing to `GenericUpgrade` — no new Timepiece-specific models required.
- List pages serve NFP from the cached field — no aggregation queries at render time.
- Existing 304-test suite passes without regression.
- Unit tests cover NFP for all three asset types including: null market value, zero service records, zero upgrades, post-delete cache refresh.

### Measurable Outcomes

| Outcome | Measure |
|---|---|
| NFP in all asset list views | All 3 list page templates show mini breakdown |
| NFP on all asset detail pages | All 3 detail page templates show full breakdown |
| Portfolio aggregate correct | Home + Insights show sum matching per-asset NFP totals |
| Timepiece upgrade tracking | GenericUpgrade UI available on Timepiece detail, NFP reflects COMPLETED upgrades |
| No regression | 304+ tests pass, ruff clean |
| Cache accuracy | NFP field updates on every service/upgrade CUD operation |

---

## Product Scope

### MVP — Minimum Viable Product

**Models & Migrations**
- `net_financial_position` nullable `DecimalField` added to `Vehicle`, `Timepiece`, `DynamicCollectionItem`
- `GenericRelation` added to `Timepiece` model pointing to `GenericUpgrade` (no migration — GenericFK lives on `GenericUpgrade`)
- Django admin updated to surface upgrade management for Timepieces

**Calculation Layer (`api/selectors.py`)**
- `get_vehicle_nfp_breakdown(vehicle)` → dict: purchase_price, service_total, upgrade_total, cost_basis, market_value, net_position
- `get_timepiece_nfp_breakdown(timepiece)` → dict: purchase_price, upgrade_total, cost_basis, market_value, net_position
- `get_collection_item_nfp_breakdown(item)` → dict: purchase_price, service_total, upgrade_total, cost_basis, market_value, net_position
- `get_portfolio_nfp_summary(user)` → aggregate NFP + per-type breakdown, max 3 queries

**Service Layer (`api/services.py`)**
- `refresh_asset_nfp(asset)` — recalculates and saves `net_financial_position`. Registered as `post_save` and `post_delete` signal handler on: `ServiceRecord`, `Upgrade`, `GenericServiceRecord`, `GenericUpgrade`.

**List View UI**
- Mini NFP row component: Cost Basis / Market Value / Net Position with `+`/`−` prefix and green/red colour coding. Consistent across all 3 asset type list pages. Responsive: inline on desktop, stacked on mobile.

**Detail View UI**
- Financial Position card: itemised cost components → cost basis → net position (gain/loss styled).
- Null-safe: `—` with tooltip "Add a valuation to calculate net position" when market value unset.

**Timepiece Upgrade UI**
- Upgrade add/edit/delete views for Timepieces matching the DynamicCollectionItem upgrade UI.
- Status flow: Wishlist → Ordered → In Progress → Completed → Cancelled.

**Portfolio Level**
- Home dashboard: aggregate NFP card alongside existing portfolio value.
- Insights page: NFP KPI card + per-asset-type NFP breakdown rows.

**Tests**
- Unit: NFP calculation for all 3 asset types, all edge cases including post-delete cache refresh.
- Functional: NFP display in list views, detail views, home, and Insights. Portfolio aggregate query count assertion.

### Growth Features (Post-MVP)

- NFP-based sorting and filtering in list views
- "Top/bottom performers by NFP" widget on Insights page
- NFP comparison chart across asset types

### Vision (Future)

- Historical NFP time series as market values and costs change over time
- PDF/CSV export of complete financial position
- NFP-based alerts when total costs exceed current market value

---

## User Journeys

### Journey 1: The Honest Reckoning (Primary — First NFP View)

**Persona:** Zaigner77 — meticulous collector tracking every acquisition and service record. Has used my_garage for a year but has never seen the full cost picture in one place.

**Opening Scene:**
Zaigner77 opens my_garage after seeing a similar BMW sell for $48,000 at auction. He navigates to the Vehicles list expecting to confirm his investment is up.

**Rising Action:**
Each vehicle row now shows a mini financial breakdown. His BMW row:
`Cost Basis: $52,400 | Market Value: $48,000 | Net Position: −$4,400` (red, `−` prefixed)

The number surprises him. He clicks through to the detail page.

**Climax:**
The Financial Position section:

```
Purchase Price:       $44,000
Service Records:       $5,200  (4 records: tires, oil, brakes, inspection)
Completed Upgrades:    $3,200  (carbon spoiler, performance air filter)
──────────────────────────────
Cost Basis:           $52,400
Current Market Value:  $48,000
Net Position:          −$4,400
```

He's in the red — but knows exactly why.

**Resolution:**
He opens Insights. His watch collection carries a positive NFP that offsets the vehicle loss. Total portfolio NFP: +$3,600. A complete, honest picture.

**Requirements:** FR1, FR4, FR6–FR8, FR12, FR15, FR17, FR21, FR22

---

### Journey 2: The Timepiece Project (Primary — Timepiece Upgrade Tracking)

**Persona:** Zaigner77 — wants to add a custom aftermarket strap to his Submariner and track the cost against its NFP.

**Opening Scene:**
He opens the Horology Salon, navigates to the Submariner detail page. For the first time, an "Upgrades" section is present — the same pattern he knows from his collection items.

**Rising Action:**
He clicks "+ Add Project": name "Milanese Mesh Strap," cost $180, status Wishlist. He saves. The NFP doesn't change — WISHLIST doesn't count. Three days later the strap arrives and he marks the upgrade COMPLETED.

**Climax:**
The Financial Position section updates:

```
Purchase Price:       $9,200
Completed Upgrades:     $180  ← strap now counts
──────────────────────────────
Cost Basis:           $9,380
Current Market Value:  $14,500
Net Position:          +$5,120  (was +$5,300)
```

**Resolution:**
The Submariner list row reflects the change. Only COMPLETED upgrades count — the rule is consistent across all asset types. The Timepiece upgrade UI is identical to what he uses for his wine collection.

**Requirements:** FR3, FR11, FR13, FR18, FR24–FR28

---

### Journey 3: The True Cost (Primary — Collection Item Service Record)

**Persona:** Zaigner77 — just had his wine cellar temperature system professionally serviced. $350 invoice.

**Opening Scene:**
He opens his Wine Collection, navigates to the cellar item, and clicks "+ Add Service."

**Rising Action:**
The GenericServiceRecord form: date, vendor, category Maintenance, cost $350. He saves.

**Climax:**
The item's Financial Position section updates:

```
Purchase Price:       $2,400
Service Records:        $350  ← just added
Completed Upgrades:       $0
──────────────────────────────
Cost Basis:           $2,750
Current Market Value:  $3,200
Net Position:          +$450  (was +$800)
```

The NFP dropped by exactly $350. The list row and Insights aggregate updated immediately.

**Resolution:**
Service costs count everywhere they should. The investment story gets more honest with every record added.

**Requirements:** FR2, FR9, FR14, FR19

---

### Journey 4: The Incomplete Asset (Edge Case — Missing Market Value)

**Persona:** Zaigner77 — recently acquired a Pomerol bottle, pending appraisal. No market value set.

**Opening Scene:**
He opens the Wine Collection list. The new bottle row appears with purchase price ($380) and one storage evaluation record ($25), but `current_market_value` is null.

**Climax:**
Mini breakdown shows: `Cost Basis: $405 | Market Value: — | Net Position: —`

No crash. No misleading $0. Tooltip on the `—`: "Market value not set — add a valuation to calculate net position."

**Resolution:**
He adds a valuation estimate. NFP populates immediately.

**Requirements:** FR5, FR16, FR20, FR29

---

### Journey Requirements Traceability

| Journey | FRs Covered |
|---|---|
| 1 — Honest Reckoning | FR1, FR4, FR6–FR8, FR12, FR15, FR17, FR21, FR22 |
| 2 — Timepiece Project | FR3, FR11, FR13, FR18, FR24–FR28 |
| 3 — True Cost | FR2, FR9, FR14, FR19 |
| 4 — Incomplete Asset | FR5, FR16, FR20, FR29 |

---

## Web App Specific Requirements

### Project-Type Overview

Django 5.2 MPA — all views server-rendered, enhanced with Alpine.js for interactivity. No SPA framework. NFP values are server-rendered; Alpine.js handles tooltip show/hide only. All calculations execute server-side with the cached field as the sole data source for list pages.

### Browser Matrix

| Browser | Support Level |
|---|---|
| Chrome / Chromium (latest 2 versions) | Full |
| Firefox (latest 2 versions) | Full |
| Safari (latest 2 versions) | Full |
| Edge (latest 2 versions) | Full |
| IE / Legacy | Not supported |

Tailwind CSS (CDN) and Alpine.js 3.x define the effective browser floor. No polyfills required.

### Responsive Design

- **Mobile (< 640px):** Mini breakdown stacks vertically — Cost Basis, Market Value, Net Position on separate lines. Net Position badge prominent.
- **Tablet (640px–1024px):** Inline if space permits; stacked fallback.
- **Desktop (> 1024px):** Full inline mini breakdown, three values in a row. Detail page financial section as a card with component rows.

Existing Tailwind responsive utilities apply. No new CSS frameworks or breakpoints.

### SEO

Not applicable — all views require `IsAuthenticated`. No public-facing pages added or modified.

### Implementation Considerations

- NFP display uses existing Tailwind utility classes and luxury token palette (`luxury-gold`, `luxury-black`, `luxury-card`). No new CSS.
- Custom template filter `nfp_display` registered in existing `my_garage_tags`: formats `DecimalField` with sign prefix, currency formatting, `—` null fallback.
- Performance targets and accessibility standards are governed by NFR1–NFR10.

---

## Functional Requirements

> **Capability contract for all downstream work.**
> UX designers, architects, and epic authors work only from this list. Any capability not listed here does not exist in the final product.

### Net Financial Position Calculation

- FR1: The system calculates NFP for any Vehicle: `Market Value − (Purchase Price + Σ ServiceRecord.total_cost + Σ Upgrade.cost [INSTALLED])`
- FR2: The system calculates NFP for any DynamicCollectionItem: `Market Value − (Purchase Price + Σ GenericServiceRecord.total_cost + Σ GenericUpgrade.cost [COMPLETED])`
- FR3: The system calculates NFP for any Timepiece: `Market Value − (Purchase Price + Σ GenericUpgrade.cost [COMPLETED])` — service costs excluded until migration story ships
- FR4: The system produces a cost-component breakdown per asset: purchase price, service costs total, upgrade costs total, cost basis, market value, net position
- FR5: The system represents NFP as null when market value is not set — no zero substitution, no error raised

### NFP Cache Management

- FR6: The system stores a cached `net_financial_position` value on each Vehicle, Timepiece, and DynamicCollectionItem
- FR7: The system refreshes a Vehicle's cached NFP when any associated ServiceRecord is created, updated, or deleted
- FR8: The system refreshes a Vehicle's cached NFP when any associated Upgrade is created, updated, or deleted
- FR9: The system refreshes a DynamicCollectionItem's cached NFP when any associated GenericServiceRecord is created, updated, or deleted
- FR10: The system refreshes a DynamicCollectionItem's cached NFP when any associated GenericUpgrade is created, updated, or deleted
- FR11: The system refreshes a Timepiece's cached NFP when any associated GenericUpgrade is created, updated, or deleted

### Asset List View Financial Display

- FR12: The collector can view a financial summary (cost basis, market value, net position) for each Vehicle in the Vehicle list
- FR13: The collector can view a financial summary for each Timepiece in the Timepiece list
- FR14: The collector can view a financial summary for each item in any DynamicCollectionItem list
- FR15: The collector can distinguish gain from loss on any list row via both colour and symbol simultaneously — not colour alone
- FR16: The collector sees NFP displayed as unavailable — not zero, not error — when market value is unset

### Asset Detail View Financial Display

- FR17: The collector can view a full financial breakdown on the Vehicle detail page: each cost component, cost basis, market value, net position
- FR18: The collector can view a full financial breakdown on the Timepiece detail page: purchase price, completed upgrade costs, cost basis, market value, net position
- FR19: The collector can view a full financial breakdown on the DynamicCollectionItem detail page: each cost component, cost basis, market value, net position
- FR20: The collector sees contextual guidance when market value is unset, directing them to add a valuation

### Portfolio-Level Financial Aggregation

- FR21: The collector can view an aggregate NFP across all assets on the home dashboard
- FR22: The collector can view aggregate NFP broken down by asset type on the Insights page
- FR23: The collector can view per-asset-type NFP totals alongside existing portfolio allocation metrics on the Insights page

### Timepiece Upgrade Tracking

- FR24: The collector can add a GenericUpgrade project to a Timepiece (name, brand, part number, status, cost, ordered date, completion date, notes)
- FR25: The collector can edit an existing Timepiece upgrade project
- FR26: The collector can delete a Timepiece upgrade project
- FR27: The collector can advance a Timepiece upgrade through: Wishlist → Ordered → In Progress → Completed → Cancelled
- FR28: The collector can view all upgrade projects for a Timepiece on the Timepiece detail page

### Display Accessibility & Formatting

- FR29: The system displays NFP values with sign prefix (`+`/`−`) and currency formatting; `—` when null
- FR30: NFP gain/loss signals use both colour and symbol — interpretable without colour perception
- FR31: All NFP monetary values have `aria-label` attributes describing value and meaning in plain language
- FR32: Interactive NFP elements (tooltips, hint links) are keyboard-navigable via `Tab` and activatable via `Enter`/`Space`

### Out of Scope — Separate Migration Story

> Tracked for a future story. NOT in scope for this PRD:
> - Service record tracking for Timepieces via `GenericServiceRecord`
> - Refactor `GenericServiceRecord.item` from FK to `GenericForeignKey`
> - Migrate Vehicle `ServiceRecord` + `Upgrade` to the generic pattern
> - Retire Vehicle-specific service/upgrade models

---

## Non-Functional Requirements

### Performance

- NFR1: Asset list pages must not exhibit perceptible load time increase after NFP display is added. NFP data served from cached field — no aggregation queries at list render time.
- NFR2: NFP cache refresh completes within the HTTP request/response cycle. Updated values visible on next page load without a separate user action.
- NFR3: Portfolio NFP aggregate uses `aggregate(Sum(...))` per asset type — max 3 queries total, not per-asset iteration. A query count regression test asserts this bound.
- NFR4: NFP breakdown selector on detail pages is permitted one additional aggregation query per render. Must be optimised before shipping if profiling shows user-perceptible degradation.

### Security

- NFR5: All views displaying NFP require `IsAuthenticated`. No NFP values accessible to unauthenticated users.
- NFR6: All ORM queries fetching assets for NFP filter by `owner=request.user`. No cross-user NFP visibility through any view, endpoint, or aggregate.
- NFR7: `refresh_asset_nfp` validates asset ownership before writing — does not accept arbitrary asset IDs from user input.

### Accessibility

- NFR8: NFP gain/loss indicators satisfy WCAG 2.1 SC 1.4.1 (Use of Colour) — dual signal (colour + symbol) required, per FR30.
- NFR9: All NFP monetary values rendered in HTML include `aria-label` describing value and meaning (e.g. `aria-label="Net Position: gain of $4,450"`).
- NFR10: Interactive NFP elements are keyboard-reachable (`Tab`) and activatable (`Enter`/`Space`) with visible Tailwind focus ring.

### Code Quality & Testability

- NFR11: All new code passes `pixi run -- ruff check .` (zero errors) and `pixi run -- ruff format --check .` (zero diffs).
- NFR12: Existing 304-test suite passes without regression (`pixi run pytest tests/unit/ tests/functional/ -x -q`).
- NFR13: Unit tests cover NFP calculation for all 3 asset types: nominal case, null market value, zero service records, zero upgrades, post-delete cache refresh.
- NFR14: Portfolio aggregate query bound (NFR3) verified by functional test using `django.test.utils.CaptureQueriesContext`.
- NFR15: All model changes accompanied by generated migrations committed in the same changeset.

---

## Project Scoping & Risk Analysis

### MVP Strategy

**Approach:** Problem-solving MVP — NFP must be honest and consistent across every asset type simultaneously. A partial rollout (Vehicles only, or NFP without Timepiece upgrade tracking) is not a valid shipping state.

**Resource profile:** Solo developer. Sequential: models → calculation layer → service layer → UI → tests.

**Timepiece boundary:** Timepieces use the existing `GenericUpgrade` model via a new `GenericRelation` — no new models introduced. Timepiece service record tracking ships in the separate migration story that will also unify Vehicles under the generic pattern.

### Risk Mitigation

**Cache invalidation completeness (High)**
- Risk: `post_delete` signal handlers missed — NFP goes stale after record deletion.
- Mitigation: `refresh_asset_nfp` registered as both `post_save` and `post_delete` handler for all supporting models. Test: create record → verify NFP → delete record → verify NFP recalculated correctly.

**Migration ordering (Low)**
- Risk: Dependency issues adding `net_financial_position` across 3 models simultaneously.
- Mitigation: `GenericRelation` on Timepiece requires no migration. Three `DecimalField` additions are independent. Single `makemigrations` run after all model changes in place.

**Portfolio aggregate N+1 (Low)**
- Risk: `get_portfolio_nfp_summary` iterates per asset rather than using bulk aggregation.
- Mitigation: `aggregate(Sum('net_financial_position'))` per asset type. Bounded by functional test using `CaptureQueriesContext`.

**Separate migration story (Scope control)**
The following are explicitly out of scope and tracked as a future story:
- `GenericServiceRecord` GenericFK refactor
- Vehicle model unification under generic pattern
- Timepiece service record tracking
