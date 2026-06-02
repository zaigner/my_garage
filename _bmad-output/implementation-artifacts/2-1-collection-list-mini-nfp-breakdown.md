# Story 2.1: Collection List Mini NFP Breakdown

Status: review

## Story

As a collector,
I want to see a financial summary for each item in my collection lists,
So that I can compare financial performance across my collection at a glance without clicking into each item.

## Acceptance Criteria

1. **Given** the collector views any collection list page **When** the page renders **Then** each item card displays a mini financial breakdown: Cost Basis / Current Market Value / Net Position

2. **Given** an item has a positive net position **When** the card renders **Then** Net Position shows a `+` prefix in green (e.g. `+$4,450`) **And** the element has `aria-label="Net Position: gain of $4,450"`

3. **Given** an item has a negative net position **When** the card renders **Then** Net Position shows a `−` prefix in red (e.g. `−$4,400`) **And** the element has `aria-label="Net Position: loss of $4,400"`

4. **Given** an item has null `current_market_value` **When** the card renders **Then** Market Value and Net Position each display `—` **And** Cost Basis still shows the known cost (purchase_price + services + completed upgrades) **And** the aria-label reads "Net Position: not calculated — market value not set"

5. **Given** the collector views the list on a mobile screen (< 640px) **When** the page renders **Then** the mini breakdown stacks vertically with Net Position badge prominent

6. **Given** new code is submitted **When** the quality gate runs **Then** a functional test GETs a collection list with at least one item having real `GenericServiceRecord` and `GenericUpgrade` rows and asserts the mini breakdown values are present in the response **And** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes **And** ruff clean

## Tasks / Subtasks

- [x] Task 1: Add `total_cost_basis` cached field + extend `refresh_item_nfp` (AC: 1, 4)
  - [x] 1.1: Added `total_cost_basis` nullable DecimalField to `DynamicCollectionItem`
  - [x] 1.2: Migration `0013_dynamiccollectionitem_total_cost_basis.py` generated and applied
  - [x] 1.3: `refresh_item_nfp` now saves both `net_financial_position` and `total_cost_basis`
  - [x] 1.4: Unit tests extended with `total_cost_basis` assertions; added `DynamicCollectionItem` post_save signal with loop guard; 3 new unit tests for item-save signal and recursion guard

- [x] Task 2: Write functional tests for list view (RED) (AC: 1, 2, 3, 4, 5, 6)
  - [x] 2.1: Created `tests/functional/test_nfp_list_display.py` — 8 tests
  - [x] 2.2: Tests cover positive/negative NFP, cost_basis, market_value in response
  - [x] 2.3: Tests cover null market_value: `—` present, cost_basis still shown

- [x] Task 3: Update `collection_list.html` mini breakdown (AC: 1, 2, 3, 4, 5)
  - [x] 3.1: Replaced the single price block with three-value mini breakdown
  - [x] 3.2: Cost Basis: `currency_display` filter (new filter added to `my_garage_extras.py`)
  - [x] 3.3: Market Value: `currency_display` filter, `—` if null
  - [x] 3.4: Net Position: `nfp_display` + `nfp_color_class` filters
  - [x] 3.5: `aria-label` on Net Position for gain/loss/null cases
  - [x] 3.6: `flex-col sm:flex-row` responsive layout

- [x] Task 4: Run quality gates
  - [x] 4.1: 349 passed
  - [x] 4.2: Zero ruff errors
  - [x] 4.3: Zero format diffs

## Dev Notes

### Cost Basis display note
Cost Basis in the mini breakdown is an absolute cost (always positive or zero), not a signed gain/loss. Display as `$X,XXX` without `+`/`−` prefix. Use `floatformat:0` with `$` prefix, or add a simple `cost_display` approach inline in the template. Do NOT use `nfp_display` (which adds sign) for cost basis.

### `total_cost_basis` derivation
`total_cost_basis = (purchase_price or 0) + service_total + upgrade_total` — same as `cost_basis` key from `get_item_nfp_breakdown`. Always a non-negative value (or None if all three sources are null/zero — but treat as Decimal("0.00") when purchase_price is null).

### Template filter note
`nfp_display` adds sign prefix — use only for Net Position. For Cost Basis: `${{ item.total_cost_basis|floatformat:0 }}` with comma formatting via a template approach, or add a separate `currency_display` filter if needed. The existing templates use `|floatformat:0` with a `$` prefix inline — follow that pattern.

### Files to touch
- `src/my_garage/models.py` — add field
- `src/my_garage/migrations/0013_...py` — generated
- `src/my_garage/api/services.py` — extend refresh_item_nfp
- `src/my_garage/templates/my_garage/collection_list.html` — mini breakdown
- `tests/unit/test_nfp_calculation.py` — add total_cost_basis assertions
- `tests/functional/test_nfp_list_display.py` — new functional test

### References
- [Source: src/my_garage/templates/my_garage/collection_list.html:124-133] current price block to replace
- [Source: src/my_garage/api/services.py] `refresh_item_nfp`
- [Source: src/my_garage/templatetags/my_garage_extras.py] `nfp_display`, `nfp_color_class`
- [Source: _bmad-output/planning-artifacts/epics.md#Story-2.1] story spec

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `total_cost_basis` as a second cached field so list view can show cost basis without extra queries even when market_value is null
- Added `currency_display` template filter for comma-formatted absolute dollar amounts (used for cost basis and market value in list/detail)
- Added `DynamicCollectionItem` post_save signal with loop guard (`update_fields <= _NFP_FIELDS`) to prevent infinite recursion when `refresh_item_nfp` saves; this also ensures new items get NFP calculated on create
- 3 new unit tests for item-save signal + recursion guard; 8 new functional tests for list display; 349 total suite

### File List

- `src/my_garage/models.py` — added `total_cost_basis` field
- `src/my_garage/migrations/0013_dynamiccollectionitem_total_cost_basis.py` — generated migration
- `src/my_garage/api/services.py` — `refresh_item_nfp` saves both NFP fields
- `src/my_garage/signals.py` — added `DynamicCollectionItem` post_save signal with loop guard
- `src/my_garage/templatetags/my_garage_extras.py` — added `currency_display` filter
- `src/my_garage/templates/my_garage/collection_list.html` — mini NFP breakdown in item cards
- `tests/unit/test_nfp_calculation.py` — extended with total_cost_basis + item-save signal tests
- `tests/functional/test_nfp_list_display.py` — 8 functional tests

### Change Log

- 2026-06-02: Story 2.1 implemented — list mini NFP breakdown, total_cost_basis cached field, item-save signal (349 suite)
