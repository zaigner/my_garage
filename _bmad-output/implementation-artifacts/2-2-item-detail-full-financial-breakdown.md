# Story 2.2: Item Detail Full Financial Breakdown

Status: review

## Story

As a collector,
I want to see a full financial breakdown on each item's detail page,
So that I understand exactly what has contributed to my true cost of ownership.

## Acceptance Criteria

1. **Given** the collector views any item detail page **When** the Financial Position section renders **Then** it shows: Purchase Price / Service Costs Total / Completed Upgrades Total / Cost Basis / Current Market Value / Net Position

2. **Given** an item has service records totalling $5,200 **When** the detail page renders **Then** Service Costs Total shows $5,200 and contributes to Cost Basis

3. **Given** an item has COMPLETED upgrades totalling $3,200 and WISHLIST upgrades totalling $1,500 **When** the detail page renders **Then** Completed Upgrades Total shows $3,200 **And** the $1,500 wishlist amount is not included in Cost Basis

4. **Given** an item has null `current_market_value` **When** the detail page renders **Then** Market Value and Net Position show `—` **And** Cost Basis still shows the known cost components **And** a tooltip reads "Add a valuation to calculate net position" **And** the tooltip trigger is keyboard-accessible (`tabindex="0"`, visible focus ring)

5. **Given** new code is submitted **When** the quality gate runs **Then** a functional test GETs the item detail page with real `GenericServiceRecord` and `GenericUpgrade` rows and asserts HTTP 200 with correct breakdown values present **And** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes **And** ruff clean

## Tasks / Subtasks

- [x] Task 1: Pass `nfp_breakdown` to detail view context (AC: 1, 2, 3)
  - [x] 1.1: Added `get_item_nfp_breakdown(item)` call in `collection_item_detail` view; `nfp_breakdown` in render context

- [x] Task 2: Write functional tests (RED) (AC: 1, 2, 3, 4, 5)
  - [x] 2.1: Created `tests/functional/test_nfp_detail_display.py` — 10 tests
  - [x] 2.2: Tests cover all breakdown values: purchase price, service total, upgrade total, cost basis, net position
  - [x] 2.3: Tests cover null market value: `—` present, tooltip text ("valuation") present

- [x] Task 3: Update `collection_item_detail.html` Financial Summary → Financial Position (AC: 1, 2, 3, 4)
  - [x] 3.1: Replaced "Financial Summary" sidebar card with "Financial Position" card
  - [x] 3.2: Rows: Purchase Price / Service Costs / Upgrades / Cost Basis (divider) / Market Value / Net Position
  - [x] 3.3: Net Position: `nfp_display` + `nfp_color_class` + `aria-label`
  - [x] 3.4: Null market value: Alpine.js tooltip with `tabindex="0"` keyboard-accessible trigger

- [x] Task 4: Run quality gates
  - [x] 4.1: 359 passed
  - [x] 4.2: Zero ruff errors
  - [x] 4.3: Zero format diffs

## Dev Notes

### View change
`collection_item_detail` view is at `src/my_garage/views.py:484`. Add before the `return render(...)`:
```python
from my_garage.api.selectors import get_item_nfp_breakdown
nfp_breakdown = get_item_nfp_breakdown(item)
```
Then include `"nfp_breakdown": nfp_breakdown` in the context dict.

### Template location of Financial Summary card
`src/my_garage/templates/my_garage/collection_item_detail.html` lines 318-346 — the `detail-card rounded-lg p-6 mb-6` div with header "Financial Summary". Replace entirely with Financial Position card.

### Null tooltip pattern
Use Alpine.js inline:
```html
<span x-data="{ show: false }" class="relative cursor-help" @mouseenter="show=true" @mouseleave="show=false"
      tabindex="0" @focus="show=true" @blur="show=false" role="tooltip">
  —
  <span x-show="show" class="absolute ...">Add a valuation to calculate net position</span>
</span>
```

### References
- [Source: src/my_garage/views.py:484] `collection_item_detail` view
- [Source: src/my_garage/templates/my_garage/collection_item_detail.html:318-346] Financial Summary card to replace
- [Source: src/my_garage/api/selectors.py] `get_item_nfp_breakdown`
- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.2] story spec

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- `nfp_breakdown` dict from `get_item_nfp_breakdown` is passed as context — avoids re-querying service/upgrade totals in the template
- Financial Position card replaces the old "Financial Summary" card which only showed equity (market - purchase), not true all-in cost
- Alpine.js tooltip on null net-position uses `tabindex="0"` + `@focus`/`@blur` for keyboard accessibility
- 10 new functional tests; 359 total suite

### File List

- `src/my_garage/views.py` — imports `get_item_nfp_breakdown`, passes `nfp_breakdown` to detail context
- `src/my_garage/templates/my_garage/collection_item_detail.html` — "Financial Position" card replacing "Financial Summary"
- `tests/functional/test_nfp_detail_display.py` — 10 functional tests

### Change Log

- 2026-06-02: Story 2.2 implemented — detail page financial position card (10 tests, 359 suite)
