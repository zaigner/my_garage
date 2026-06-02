# Story 1.2: Backfill NFP for Existing Items

Status: review

## Story

As a collector,
I want all existing items in my collection to have their NFP calculated when I deploy the feature,
So that I see accurate financial data immediately without needing to trigger a save on every item.

## Acceptance Criteria

1. **Given** the NFP migration has been applied and existing `DynamicCollectionItem` records have null `net_financial_position` **When** the backfill management command runs **Then** all `DynamicCollectionItem` records have their `net_financial_position` calculated and saved **And** items with null `current_market_value` remain null (not forced to zero)

2. **Given** the backfill command runs on an empty database **When** it completes **Then** it exits without error and reports zero items processed

3. **Given** a `--dry-run` flag is passed **When** the command runs **Then** it reports counts without writing any `net_financial_position` values to the database

4. **Given** new code is submitted **When** the quality gate runs **Then** unit tests verify the backfill logic across multiple items with service records, upgrades, and null market values **And** `pixi run pytest tests/unit/ -x -q` passes **And** ruff check and ruff format --check report zero errors

## Tasks / Subtasks

- [x] Task 1: Write failing unit tests (RED) (AC: 1, 2, 3, 4)
  - [x] 1.1: Created `tests/unit/test_backfill_nfp.py` — 6 tests covering all ACs

- [x] Task 2: Implement `backfill_nfp` management command (AC: 1, 2, 3)
  - [x] 2.1: Created `src/my_garage/management/commands/backfill_nfp.py`
  - [x] 2.2: Iterates all `DynamicCollectionItem` via `.iterator()` for memory efficiency, calls `refresh_item_nfp(item)`
  - [x] 2.3: `--dry-run` flag reports count without writing
  - [x] 2.4: Outputs total processed, updated, skipped (null market value)

- [x] Task 3: Run quality gates
  - [x] 3.1: `pixi run pytest tests/unit/ tests/functional/ -x -q` — 337 passed
  - [x] 3.2: `pixi run -- ruff check .` — zero errors
  - [x] 3.3: `pixi run -- ruff format --check .` — zero diffs

## Dev Notes

### Architecture

- Management commands live in `src/my_garage/management/commands/`
- Existing commands for reference: `build_knowledge_index.py`, `refresh_bmad_context.py`
- `refresh_item_nfp` is in `src/my_garage/api/services.py` — import it directly
- `DynamicCollectionItem` in `src/my_garage/models.py`

### Command pattern

Use Django's `BaseCommand` with `self.stdout.write(self.style.SUCCESS(...))` for output.
`--dry-run` adds `action='store_true'` argument. Iterate with `.iterator()` for memory efficiency on large datasets.

### Test pattern

Follow `tests/unit/test_portfolio_yoy_selector.py` — `pytestmark = pytest.mark.django_db`, fixtures via `DynamicCollectionItem.objects.create(...)`.

To test that dry-run does NOT write, check `net_financial_position` is still null after calling the command with `dry_run=True`.

Call the command logic directly (import and call the function) rather than via `call_command` to keep unit tests focused on logic, not CLI parsing. Or use `call_command('backfill_nfp', '--dry-run')` — either approach is acceptable.

### References

- [Source: src/my_garage/management/commands/] existing command examples
- [Source: src/my_garage/api/services.py] `refresh_item_nfp`
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.2] story spec

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Command uses `.iterator()` on the queryset for memory efficiency on large datasets
- `refresh_item_nfp` + `item.refresh_from_db(fields=['net_financial_position'])` used to check post-write value for the skipped/updated count — avoids double-query by only refreshing the one field
- Tests wipe `net_financial_position` via bulk `update()` after fixture creation (signals fire on create) so the backfill has something to do
- 6 new unit tests; 337 total suite (0 regressions)

### File List

- `src/my_garage/management/commands/backfill_nfp.py` — new management command
- `tests/unit/test_backfill_nfp.py` — 6 unit tests

### Change Log

- 2026-06-02: Story 1.2 implemented — backfill_nfp management command (6 tests, 337 suite passed)
