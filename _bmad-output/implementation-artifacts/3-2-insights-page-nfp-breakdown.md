# Story 3.2: Insights Page NFP Breakdown by Collection Type

Status: review

## Story

As a collector,
I want to see my net financial position broken down by collection type on the Insights page,
So that I can understand which parts of my collection are performing well as investments.

## Acceptance Criteria

1. **Given** an authenticated collector navigates to `/insights/` **When** the page renders **Then** a Net Financial Position KPI card shows the portfolio-wide aggregate NFP

2. **Given** the collector has items across multiple collection types **When** the Insights page renders **Then** each collection type shows its NFP total alongside existing allocation metrics

3. **Given** a specific collection type has a positive NFP total **When** the Insights page renders **Then** that collection type's NFP shows `+` prefix in green

4. **Given** a specific collection type has a negative NFP total **When** the Insights page renders **Then** that collection type's NFP shows `−` prefix in red

5. **Given** a collection type has no items with market values set **When** the Insights page renders **Then** that collection type's NFP shows `—` without error or zero

6. **Given** the collector has no items **When** the Insights page renders **Then** all NFP values show `—` and no errors occur (existing zero-asset guard preserved)

7. **Given** new code is submitted **When** the quality gate runs **Then** a functional test GETs `/insights/` and asserts the NFP KPI card and per-type NFP values are present **And** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes **And** ruff clean

## Tasks / Subtasks

- [x] Task 1: `get_portfolio_nfp_by_collection` selector added alongside `get_portfolio_nfp_summary` in `src/my_garage/api/selectors.py`

- [x] Task 2: `portfolio_insights` view updated
  - [x] 2.1–2.2: Both selectors imported and called
  - [x] 2.3: Per-type NFP merged into `category_list` as `c['nfp']`
  - [x] 2.4: `portfolio_nfp` in render context

- [x] Task 3: Created `tests/functional/test_nfp_insights_display.py` — 6 tests

- [x] Task 4: `portfolio_insights.html` updated
  - [x] 4.1: `{% load my_garage_extras %}` added
  - [x] 4.2: 4th KPI card "Net Financial Position"; grid changed to `sm:grid-cols-2 lg:grid-cols-4`
  - [x] 4.3: Per-category NFP line alongside equity in allocation rows
  - [x] 4.4: `nfp_display` + `nfp_color_class` throughout

- [x] Task 5: Quality gates — 370 passed, zero errors, zero diffs

## Dev Notes

### Selector
```python
def get_portfolio_nfp_by_collection(user) -> dict:
    rows = (
        DynamicCollectionItem.objects.filter(owner=user)
        .values('collection_type__name')
        .annotate(nfp=Sum('net_financial_position'))
    )
    return {row['collection_type__name']: row['nfp'] for row in rows}
```

### Insights view
`src/my_garage/views.py:738` — `def portfolio_insights(...)`. The view already builds `category_list` with per-type dicts. After building the list, merge NFP data:
```python
nfp_by_collection = get_portfolio_nfp_by_collection(request.user)
for c in category_list:
    c['nfp'] = nfp_by_collection.get(c['name'])
```

### Template load
`portfolio_insights.html` extends `my_garage/base.html`. Add `{% load my_garage_extras %}` near the top of the template (after `{% extends ... %}`).

### KPI card layout
The current 3 KPI cards use `grid-cols-1 md:grid-cols-3`. Change to `md:grid-cols-2 lg:grid-cols-4` (or add a second row) to accommodate the 4th NFP card.

### References
- [Source: src/my_garage/views.py:738] `portfolio_insights` view
- [Source: src/my_garage/templates/my_garage/portfolio_insights.html:40-73] KPI cards section
- [Source: src/my_garage/templates/my_garage/portfolio_insights.html:76-106] Category allocation rows
- [Source: _bmad-output/planning-artifacts/epics.md#Story-3.2] story spec

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- `portfolio_insights` view already iterated all items in Python — no ORM aggregate was used. NFP selectors replace the per-item NFP loop with two clean queries
- "Total Equity" KPI updated label from "Market value minus cost basis" → "Market value minus purchase price" since that's what it actually measures; NFP is now the true all-in cost metric
- KPI grid changed from `md:grid-cols-3` to `sm:grid-cols-2 lg:grid-cols-4` to fit 4 cards without breaking layout
- 6 new functional tests; 370 total suite

### File List

- `src/my_garage/views.py` — `portfolio_insights` view calls both NFP selectors, merges `c['nfp']` into category_list
- `src/my_garage/templates/my_garage/portfolio_insights.html` — 4th NFP KPI card + per-category NFP in allocation rows
- `tests/functional/test_nfp_insights_display.py` — 6 functional tests

### Change Log

- 2026-06-02: Story 3.2 implemented — insights NFP KPI card + per-category breakdown (6 tests, 370 suite)
