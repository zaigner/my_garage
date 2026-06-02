# Story 1.1: NFP Calculation, Cached Field, and Signal Handlers

Status: review

## Story

As a collector,
I want the system to calculate and store my net financial position for every item automatically,
So that my financial data is always accurate and instantly available without manual calculation.

## Acceptance Criteria

1. **Given** a `DynamicCollectionItem` has `purchase_price`, `GenericServiceRecord` entries, and COMPLETED `GenericUpgrade` entries **When** any associated `GenericServiceRecord` or `GenericUpgrade` is created, updated, or deleted **Then** `DynamicCollectionItem.net_financial_position` is recalculated as `Market Value − (Purchase Price + Σ GenericServiceRecord.total_cost + Σ GenericUpgrade.cost [status=COMPLETED])` **And** the recalculated value is persisted within the HTTP request/response cycle

2. **Given** a `DynamicCollectionItem` has `current_market_value = null` **When** NFP is calculated **Then** `net_financial_position` is stored as null — not zero, not an error

3. **Given** a `DynamicCollectionItem` has no `GenericServiceRecord` or `GenericUpgrade` entries **When** NFP is calculated **Then** `net_financial_position = current_market_value − purchase_price`

4. **Given** a `GenericServiceRecord` is deleted from a `DynamicCollectionItem` **When** the deletion completes **Then** `DynamicCollectionItem.net_financial_position` is recalculated via `post_delete` signal **And** the stale value from before the deletion is no longer present

5. **Given** a `GenericUpgrade` with status WISHLIST, ORDERED, or IN_PROGRESS exists for an item **When** NFP is calculated **Then** that upgrade's cost is NOT included in the cost basis — only COMPLETED status counts

6. **Given** new code is submitted **When** the quality gate runs **Then** unit tests pass for: nominal case, null market value, zero service records, zero upgrades, post-delete cache refresh, non-COMPLETED upgrade excluded **And** `pixi run pytest tests/unit/ -x -q` passes **And** ruff check and ruff format --check report zero errors

7. **Given** a `GenericUpgrade` is linked via the `content_type`/`object_id` GenericForeignKey (not the `item` FK) to a `DynamicCollectionItem` **When** that upgrade is created, updated, or deleted **Then** the linked item's `net_financial_position` is also recalculated correctly

## Tasks / Subtasks

- [x] Task 1: Add `net_financial_position` field to `DynamicCollectionItem` and generate migration (AC: 1, 2, 3)
  - [x] 1.1: Add nullable `DecimalField(max_digits=12, decimal_places=2)` named `net_financial_position` to `DynamicCollectionItem` in `src/my_garage/models.py`
  - [x] 1.2: Run `pixi run manage makemigrations` to generate `0012_dynamiccollectionitem_net_financial_position.py`
  - [x] 1.3: Run `pixi run manage migrate` to apply the migration

- [x] Task 2: Create `get_item_nfp_breakdown` selector (AC: 1, 2, 3, 5)
  - [x] 2.1: Add `get_item_nfp_breakdown(item)` to `src/my_garage/api/selectors.py` — returns dict with keys: `purchase_price`, `service_total`, `upgrade_total`, `cost_basis`, `market_value`, `net_position`
  - [x] 2.2: Uses `aggregate(Sum('total_cost'))` for service total and Q-filter over both FK and GFK paths for upgrade total
  - [x] 2.3: Returns `net_position = None` when `current_market_value` is null

- [x] Task 3: Create `refresh_item_nfp` service function (AC: 1, 2, 3)
  - [x] 3.1: Added `refresh_item_nfp(item)` to `src/my_garage/api/services.py`
  - [x] 3.2: Uses `update_fields=['net_financial_position']` — no full save; null market value stores null

- [x] Task 4: Wire Django signals for cache invalidation (AC: 1, 4, 7)
  - [x] 4.1: Created `src/my_garage/signals.py` with `post_save` and `post_delete` handlers for `GenericServiceRecord` and `GenericUpgrade`
  - [x] 4.2: `GenericServiceRecord` handler: queries item via `DynamicCollectionItem.objects.filter(pk=instance.item_id).first()` for CASCADE safety
  - [x] 4.3: `GenericUpgrade` handler: resolves item via direct FK first, then GFK (`content_type_id` + `object_id`) fallback
  - [x] 4.4: Updated `src/my_garage/apps.py` `ready()` to import signals
  - [x] 4.5: Verified via full test suite (331 passed)

- [x] Task 5: Create `nfp_display` template filter (AC: 6)
  - [x] 5.1: Added `nfp_display` filter to `src/my_garage/templatetags/my_garage_extras.py`
  - [x] 5.2: Filter returns formatted string; styling is Tailwind class via companion filter
  - [x] 5.3: Added `nfp_color_class` filter returning `text-green-400` / `text-red-400` / `text-gray-400`

- [x] Task 6: Write unit tests (AC: 6)
  - [x] 6.1: Created `tests/unit/test_nfp_calculation.py` — 27 tests
  - [x] 6.2: `get_item_nfp_breakdown`: nominal, null market value, zero records, zero upgrades, non-COMPLETED excluded, null purchase price
  - [x] 6.3: `refresh_item_nfp`: field saved, null market value stores null, only NFP field updated
  - [x] 6.4: `GenericServiceRecord` post_save and post_delete signals verified
  - [x] 6.5: `GenericUpgrade` post_save and post_delete signals verified; status change to COMPLETED triggers recalc
  - [x] 6.6: `nfp_display` filter: positive, negative, null, zero, large values with commas
  - [x] 6.7: `nfp_color_class` filter: all four cases
  - [x] GFK path (AC: 7): upgrade via content_type/object_id triggers NFP refresh on create and delete

- [x] Task 7: Run quality gates
  - [x] 7.1: `pixi run pytest tests/unit/ tests/functional/ -x -q` — 331 passed
  - [x] 7.2: `pixi run -- ruff check . --fix && pixi run -- ruff format .` — clean
  - [x] 7.3: `pixi run -- ruff check .` — zero errors
  - [x] 7.4: `pixi run -- ruff format --check .` — zero diffs

## Dev Notes

### Architecture

- **Single asset model**: All assets (vehicles, timepieces, custom collections) are `DynamicCollectionItem` in `src/my_garage/models.py`
- **Service records**: `GenericServiceRecord` (FK `item` → `DynamicCollectionItem`, `related_name="service_records"`)
- **Upgrades**: `GenericUpgrade` has dual link mechanism:
  - `item` FK (direct, `null=True, blank=True`) — used by all current views/tests
  - `content_type` + `object_id` GenericForeignKey — exists but not actively used yet
  - Signal handler must resolve the item from whichever path is populated
- **Upgrade statuses**: WISHLIST, ORDERED, IN_PROGRESS, COMPLETED, CANCELLED — only COMPLETED counts toward cost basis

### Selector pattern

Existing selectors in `src/my_garage/api/selectors.py` use `from django.db.models import Q` and `from my_garage.models import DynamicCollectionItem, PortfolioSnapshot`. New selector follows the same import pattern. Use `aggregate(Sum(...))` — never iterate per-record.

### Service pattern

Existing services in `src/my_garage/api/services.py` are plain functions with docstrings. `refresh_item_nfp` follows this pattern. Use `item.save(update_fields=['net_financial_position'])` — not a full `.save()`.

### Signal wiring

`src/my_garage/apps.py` must have a `ready()` method that imports signals. Django signal handlers must use `dispatch_uid` to prevent duplicate registration. Pattern:

```python
# src/my_garage/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from my_garage.models import GenericServiceRecord, GenericUpgrade, DynamicCollectionItem

@receiver(post_save, sender=GenericServiceRecord, dispatch_uid="nfp_service_record_save")
@receiver(post_delete, sender=GenericServiceRecord, dispatch_uid="nfp_service_record_delete")
def handle_service_record_change(sender, instance, **kwargs):
    from my_garage.api.services import refresh_item_nfp
    if instance.item_id:
        refresh_item_nfp(instance.item)
```

### Template filter

`src/my_garage/templatetags/my_garage_extras.py` already contains `replace` and `get_item` filters. Add `nfp_display` and `nfp_color_class` to the same file. No new module needed.

### Migration

Latest migration is `0011_portfolio_snapshot.py`. New migration will be `0012_nfp_field.py`. Field: `models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)`.

### Test structure

Unit tests live in `tests/unit/`. New file: `tests/unit/test_nfp_calculation.py`. Use `pytest-django` with `@pytest.mark.django_db`. Create fixtures with `DynamicCollectionItem.objects.create(...)` directly (factory-boy not required for unit tests). Settings: `DJANGO_SETTINGS_MODULE=config.settings.test`.

### Project Structure Notes

- `src/my_garage/models.py` — add field to `DynamicCollectionItem`
- `src/my_garage/api/selectors.py` — add `get_item_nfp_breakdown`
- `src/my_garage/api/services.py` — add `refresh_item_nfp`
- `src/my_garage/signals.py` — new file
- `src/my_garage/apps.py` — wire signals in `ready()`
- `src/my_garage/templatetags/my_garage_extras.py` — add filters
- `src/my_garage/migrations/0012_nfp_field.py` — generated
- `tests/unit/test_nfp_calculation.py` — new file

### References

- [Source: src/my_garage/models.py] `DynamicCollectionItem`, `GenericServiceRecord`, `GenericUpgrade`
- [Source: src/my_garage/api/selectors.py] existing selector pattern with `aggregate(Sum(...))`
- [Source: src/my_garage/api/services.py] existing service function pattern
- [Source: src/my_garage/templatetags/my_garage_extras.py] existing template filter module
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-1] story spec

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Added `net_financial_position` nullable DecimalField to `DynamicCollectionItem`; migration `0012_dynamiccollectionitem_net_financial_position.py` generated and applied
- `get_item_nfp_breakdown` selector handles both direct FK and GFK upgrade paths using a Q-filter union to avoid double-counting
- Signal handlers use `DynamicCollectionItem.objects.filter(pk=...).first()` instead of cached FK access for CASCADE safety
- `nfp_display` uses Unicode minus sign (U+2212 `−`) not ASCII hyphen for negative values
- 27 new unit tests; 331 total suite (0 regressions)

### File List

- `src/my_garage/models.py` — added `net_financial_position` field to `DynamicCollectionItem`
- `src/my_garage/migrations/0012_dynamiccollectionitem_net_financial_position.py` — generated migration
- `src/my_garage/api/selectors.py` — added `get_item_nfp_breakdown`
- `src/my_garage/api/services.py` — added `refresh_item_nfp`
- `src/my_garage/signals.py` — new file; post_save/post_delete handlers for GenericServiceRecord and GenericUpgrade
- `src/my_garage/apps.py` — wired signals in `ready()`
- `src/my_garage/templatetags/my_garage_extras.py` — added `nfp_display` and `nfp_color_class` filters
- `tests/unit/test_nfp_calculation.py` — new file; 27 unit tests

### Change Log

- 2026-06-02: Story 1.1 implemented — NFP calculation, cached field, signal handlers, template filters (27 tests, 331 suite passed)
