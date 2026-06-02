# Story 3.1: Home Dashboard Aggregate NFP Card

Status: review

## Story

As a collector,
I want to see my total net financial position on the home dashboard,
So that I can immediately understand whether my overall portfolio is gaining or losing value relative to everything I've spent on it.

## Acceptance Criteria

1. **Given** an authenticated collector opens the home dashboard at `/` **When** the page renders **Then** an aggregate NFP card is visible showing the total Net Financial Position across all `DynamicCollectionItem` owned by the user

2. **Given** the collector's portfolio has a positive aggregate NFP **When** the home page renders **Then** the aggregate NFP displays with a `+` prefix in green **And** the `aria-label` reads "Total Net Financial Position: gain of $X"

3. **Given** the collector's portfolio has a negative aggregate NFP **When** the home page renders **Then** the aggregate NFP displays with a `−` prefix in red

4. **Given** the collector has no assets with market values set **When** the home page renders **Then** the aggregate NFP card shows `—` without error

5. **Given** the home page view executes the portfolio NFP query **When** measured with `CaptureQueriesContext` **Then** the NFP aggregation uses at most 1 additional query (a single `Sum` over `DynamicCollectionItem`)

6. **Given** new code is submitted **When** the quality gate runs **Then** a functional test asserts the aggregate NFP card is present in the authenticated home page response **And** a query count test asserts the NFP query is a single aggregate **And** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes **And** ruff clean

## Tasks / Subtasks

- [x] Task 1: Add `get_portfolio_nfp_summary` selector (AC: 1, 5)
  - [x] 1.1–1.3: Added to `src/my_garage/api/selectors.py`; single `Sum` aggregate query

- [x] Task 2: Add `portfolio_nfp` to home view context (AC: 1, 4)
  - [x] 2.1–2.2: Imported and called in `src/config/views.py`; `portfolio_nfp` in context dict

- [x] Task 3: Write functional tests (RED) (AC: 1, 2, 3, 4, 5, 6)
  - [x] 3.1–3.4: Created `tests/functional/test_nfp_home_display.py` — 5 tests including query count

- [x] Task 4: Add NFP card to `templates/pages/home.html` (AC: 1, 2, 3, 4)
  - [x] 4.1: NFP card added after YoY badge in hero section
  - [x] 4.2: `{% load my_garage_extras %}` added; `nfp_display` and `nfp_color_class` used
  - [x] 4.3: `aria-label` with gain/loss/null variants

- [x] Task 5: Quality gates — 370 passed, zero errors, zero diffs

## Dev Notes

### Selector
```python
def get_portfolio_nfp_summary(user) -> Optional[Decimal]:
    from django.db.models import Sum
    result = DynamicCollectionItem.objects.filter(owner=user).aggregate(
        total=Sum('net_financial_position')
    )
    return result['total']  # None if no items or all null
```

### Home view location
`src/config/views.py:29` — `def home(...)`. Add import and call inside `if request.user.is_authenticated` block at line ~85 alongside `yoy_pct_change`.

### Template
`templates/pages/home.html` is a standalone (no extends). Add `{% load my_garage_extras %}` after `{% load static %}`. Add NFP card in the hero section after the YoY badge (around line 123).

### Query count test
Use `django.test.utils.CaptureQueriesContext` — count queries during a GET `/` request, assert there is at most 1 query containing `SUM("net_financial_position")`.

### References
- [Source: src/config/views.py:29] home view
- [Source: templates/pages/home.html:103-123] YoY badge section — insert NFP card after
- [Source: _bmad-output/planning-artifacts/epics.md#Story-3.1] story spec

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- `get_portfolio_nfp_summary` and `get_portfolio_nfp_by_collection` added together since both are needed; reused in Story 3.2
- `home.html` is a standalone template (no extends), required adding `{% load my_garage_extras %}` after `{% load static %}`
- NFP card placed after the YoY badge in the hero section, inside `{% if user.is_authenticated %}` — unauthenticated visitors see no NFP
- Query count test uses `CaptureQueriesContext` to assert exactly 1 SUM query for `net_financial_position`
- 5 new functional tests; 370 total suite

### File List

- `src/my_garage/api/selectors.py` — `get_portfolio_nfp_summary`, `get_portfolio_nfp_by_collection`
- `src/config/views.py` — imports `get_portfolio_nfp_summary`, adds `portfolio_nfp` to context
- `templates/pages/home.html` — NFP card in hero section
- `tests/functional/test_nfp_home_display.py` — 5 functional tests

### Change Log

- 2026-06-02: Story 3.1 implemented — home dashboard aggregate NFP card (5 tests, 370 suite)
