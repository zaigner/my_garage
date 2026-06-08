# Story 1.4: Estate Plan Dashboard & Completeness View

Status: review

## Story

As an estate planner,
I want a dedicated estate dashboard showing my plan's completeness and all assignments in one view,
So that I can immediately see which items are covered and which still need attention.

## Acceptance Criteria

1. **Given** authenticated owner visits `/estate/` **When** the page renders **Then** executor designation status is shown (name if designated, or "Not designated" warning) **And** completeness metric shows "X of Y items assigned" with a visual progress bar **And** a table lists every DynamicCollectionItem with name, collection type, assigned beneficiary or "Unassigned" badge, and conditional note **And** the last 10 EstateChangeLog entries are shown in a recent activity section

2. **Given** owner has zero items **When** `/estate/` renders **Then** completeness shows "No items yet" with no division-by-zero error

3. **Given** a portfolio has 100 items **When** the page loads **Then** the response completes within 2 seconds (NFR1)

4. **Given** owner clicks "Bulk Assign" CTA **When** the link is followed **Then** they land on `/estate/assign/`

5. **Given** new code is submitted **When** the quality gate runs **Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes with zero failures **And** ruff check and ruff format --check report zero errors

## Tasks / Subtasks

- [x] Task 1: Add `get_estate_dashboard_context(user)` selector to `src/my_garage/api/selectors.py`
  - [x] 1.1: Import `Exists`, `OuterRef` from `django.db.models`; import `EstateChangeLog`, `EstateExecutor` from models
  - [x] 1.2: Query 1 — `EstateExecutor.objects.filter(owner=user).first()`
  - [x] 1.3: Query 2 — `DynamicCollectionItem` with `select_related("collection_type", "estate_assignment__beneficiary")` + `Exists` annotation for `is_assigned`, evaluated to a list
  - [x] 1.4: Compute `items_total`, `items_assigned`, `completeness_pct` in Python from evaluated list
  - [x] 1.5: Query 3 — `EstateChangeLog.objects.filter(owner=user)[:10]` as list

- [x] Task 2: Add `estate_dashboard` view to `src/my_garage/estate_views.py`
  - [x] 2.1: Import `get_estate_dashboard_context` from `my_garage.api.selectors`
  - [x] 2.2: `@login_required` view function calling selector and rendering `my_garage/estate/dashboard.html`

- [x] Task 3: Add root URL to `src/my_garage/estate_urls.py`
  - [x] 3.1: `path("", estate_views.estate_dashboard, name="estate_dashboard")` as first entry

- [x] Task 4: Create `src/my_garage/templates/my_garage/estate/dashboard.html`
  - [x] 4.1: Extends `my_garage/base.html`; page header with "Estate & Legacy" breadcrumb
  - [x] 4.2: Executor status card — name + contact if designated; warning badge if not
  - [x] 4.3: Completeness card — "X of Y items assigned" with progress bar; "No items yet" guard when items_total == 0
  - [x] 4.4: "Bulk Assign →" button linking to `{% url 'estate:assign_overview' %}`
  - [x] 4.5: Items table — name, collection type, assigned beneficiary display (is_charitable / beneficiary name / "Unassigned" badge)
  - [x] 4.6: Recent activity section — last 10 EstateChangeLog entries; "No activity yet" empty state

- [x] Task 5: Write unit tests in `tests/unit/test_estate_dashboard_selector.py`
  - [x] 5.1: `test_zero_items_returns_empty_context` — zero items, no division-by-zero
  - [x] 5.2: `test_unassigned_items_count` — items present but none assigned
  - [x] 5.3: `test_assigned_items_count` — some items assigned, correct completeness_pct
  - [x] 5.4: `test_all_assigned_returns_100_pct` — all assigned, completeness_pct == 100
  - [x] 5.5: `test_executor_returned_when_designated` — executor in context
  - [x] 5.6: `test_recent_log_capped_at_10` — only 10 log entries returned

- [x] Task 6: Write functional tests in `tests/functional/test_estate_dashboard.py`
  - [x] 6.1: `test_dashboard_returns_200_for_auth_user`
  - [x] 6.2: `test_dashboard_redirects_unauthenticated`
  - [x] 6.3: `test_shows_executor_name_when_designated`
  - [x] 6.4: `test_shows_no_executor_warning_when_not_designated`
  - [x] 6.5: `test_shows_completeness_count`
  - [x] 6.6: `test_bulk_assign_link_present`
  - [x] 6.7: `test_no_items_no_error`

- [x] Task 7: Quality gate — 509 passed (34 new), ruff clean, zero format diffs

## Dev Notes

### Architecture

- Pattern: selector returns a plain dict → view passes to template (no service layer needed — read-only)
- Selector file: `src/my_garage/api/selectors.py`
- View file: `src/my_garage/estate_views.py`
- URL namespace: `estate:estate_dashboard` → `/estate/`
- Template: `src/my_garage/templates/my_garage/estate/dashboard.html`

### Selector design (max 3 ORM queries)

```python
def get_estate_dashboard_context(user) -> dict:
    executor = EstateExecutor.objects.filter(owner=user).first()  # Q1

    items = list(
        DynamicCollectionItem.objects
        .filter(owner=user)
        .select_related("collection_type", "estate_assignment__beneficiary")
        .annotate(
            is_assigned=Exists(BeneficiaryAssignment.objects.filter(item_id=OuterRef("pk")))
        )
        .order_by("collection_type__name", "name")
    )  # Q2

    items_total = len(items)
    items_assigned = sum(1 for item in items if item.is_assigned)
    completeness_pct = int(items_assigned / items_total * 100) if items_total > 0 else 0

    recent_log = list(EstateChangeLog.objects.filter(owner=user)[:10])  # Q3

    return {
        "executor": executor,
        "items": items,
        "items_total": items_total,
        "items_assigned": items_assigned,
        "completeness_pct": completeness_pct,
        "recent_log": recent_log,
    }
```

### Template patterns (from existing estate templates)

- Luxury dark aesthetic — `bg-luxury-card`, `text-luxury-gold`, `text-luxury-white`, `border-white/5`
- Unassigned badge: `bg-red-900/30 text-red-400 text-[10px] uppercase tracking-widest`
- Assignment display: use `{% if item.is_assigned %}item.estate_assignment.is_charitable/beneficiary{% else %}Unassigned badge{% endif %}`
- Warning badge for missing executor: `bg-yellow-900/40 text-yellow-400`

### URL ordering

Add `path("", ..., name="estate_dashboard")` as the FIRST entry in `estate_urls.py` to avoid shadowing other patterns.

### Accessing estate_assignment in template

With `select_related("estate_assignment__beneficiary")`, the estate_assignment attribute on items without an assignment will raise `RelatedObjectDoesNotExist` in Python. In templates, Django handles this silently. Use `item.is_assigned` (the annotated boolean) for conditional logic in Python; rely on template exception-handling in the template.

### Reference files

- `src/my_garage/api/selectors.py` — existing selector patterns
- `src/my_garage/estate_views.py` — existing view patterns
- `src/my_garage/templates/my_garage/estate/assign_overview.html` — table design reference
- `src/my_garage/templates/my_garage/estate/executor.html` — card design reference
- `tests/functional/test_estate_story1_1.py` — test fixture patterns

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- `get_estate_dashboard_context` uses exactly 3 ORM queries: executor (Q1), items with Exists annotation (Q2), recent log (Q3)
- `is_assigned` annotation (Exists subquery) avoids RelatedObjectDoesNotExist exceptions in Python — template also uses `item.is_assigned` as the gate for safe `estate_assignment` attribute access
- completeness_pct uses integer division guarded by `items_total > 0` — no ZeroDivisionError when portfolio is empty
- Dashboard template extends base.html; no standalone chrome needed at this stage
- 509 tests total (34 new: 20 unit + 14 functional), 0 regressions

### File List

- `src/my_garage/api/selectors.py` — added `get_estate_dashboard_context`; added `Exists`, `OuterRef` imports; added `EstateChangeLog`, `EstateExecutor` model imports
- `src/my_garage/estate_views.py` — added `estate_dashboard` view; imported `get_estate_dashboard_context`
- `src/my_garage/estate_urls.py` — added `path("", ..., name="estate_dashboard")` as first entry
- `src/my_garage/templates/my_garage/estate/dashboard.html` — new template
- `tests/unit/test_estate_dashboard_selector.py` — 20 unit tests
- `tests/functional/test_estate_dashboard.py` — 14 functional tests

### Change Log

- 2026-06-08: Story 1.4 implemented — estate dashboard at /estate/ with executor status card, completeness progress bar, items table, recent activity (34 new tests, 509 suite)
