---
title: 'Story 2.4: Executor Item Detail View'
type: 'feature'
created: '2026-10-27'
status: 'done'
baseline_commit: 'dfebf14ddcc3eb7a5b5e92a77a5e57dd095a055f'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-2-3-executor-portfolio-view.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The executor can see the whole portfolio but can't open an item to check its provenance, its value at activation, or the owner's wishes for it.

**Approach:** Each portfolio row links to a read-only `/estate/portal/items/<id>/` page. It shows:
- name, collection, photo (or a placeholder), purchase price and date, owner notes, and custom fields;
- the activation snapshot: date, market value, cost basis, equity;
- the beneficiary (or charity, or Unassigned) and its conditional note;
- the item's service records (date, vendor, category, description, cost) and valuation history (date, value), as text lists, newest first. Decided 2026-10-27 to meet the PRD's FR23; receipt images and attachments are excluded.

An item outside the session's estate returns 404. Each view logs `ITEM_VIEW`. The photo is served by a portal route behind `executor_required`, because the owner-only `serve_media` would send an executor to the login page.

## Boundaries & Constraints

**Always:**
- Reuse 2.2 and 2.3 patterns: `require_safe` outermost, then `executor_required` (which carries `never_cache`); log after render, GET only; `_money.html` for money; `_designation.html` for the beneficiary.
- Snapshot values come only from the session token's `ESTATE_ACTIVATION` snapshot (`created_at >= token.issued_at`). If there is none, show "Added after activation".
- Every lookup filters by `owner=request.estate_owner`. A mismatch is a 404, never a 403, so item IDs can't be enumerated across estates.
- The photo route serves only `item.photo` of an owned item, through `static_serve` with `Cache-Control: private`, and lives under `/estate/portal/`.

**Never:**
- Any write, edit control, or owner chrome.
- Receipt images or attachments.
- The PDF export (Story 4.2).
- Executor sign-out (deferred).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Owned item | valid session, item of the estate owner | 200, all fields above, `ITEM_VIEW` logged with item + token | — |
| Other owner's item | item_id from another estate | 404, nothing logged | — |
| Unknown item | nonexistent id | 404 | — |
| No session | GET detail | 302 → `/estate/portal/` | — |
| No photo | `photo` empty | placeholder element, no `<img>` | — |
| Photo request | GET `…/items/<id>/photo/` for an owned item with a photo | file bytes, `Cache-Control` private and not stored | 404 when the item isn't owned, has no photo, or the file is missing |
| Added after activation | no snapshot for this activation | snapshot block reads "Added after activation" | — |
| Null snapshot values | snapshot exists with nulls | "—" per field; a real 0 shows "$0" | — |
| Conditional note | assignment with a note | note shown prominently | omitted when blank |
| Service records / valuations | item has records | both lists render newest first; the service cost uses `_money.html` | an empty list says "No service records" / "No valuation history" |
| HEAD | HEAD on detail | 200, nothing logged | — |
| POST | POST on detail or photo | 405 | — |

</frozen-after-approval>

## Code Map

- `src/my_garage/views.py:480-487` -- `display_custom_fields` is built inline in the owner `collection_item_detail` view (it skips system and enrichment keys and empty values). Move it to a selector `get_item_display_custom_fields(item)` and call it from both views, so the owner and the executor see the same fields.
- `src/my_garage/views.py:48-62` -- `serve_media` (owner-only, `static_serve`, private cache). The template for the portal photo view.
- `src/my_garage/api/selectors.py` -- next to `get_executor_portfolio_context`, add `get_executor_item_detail_context(owner, token, item_id)`. It returns `None` when the item isn't the owner's; otherwise the item (with `select_related` of collection type and assignment/beneficiary), the snapshot for this activation (or `None`), the designation fields shared with 2.3's rows, the conditional note, the custom fields, `service_records` (`GenericServiceRecord`, related name `service_records`, ordered `-date`) and `valuation_history` (`GenericValuationHistory`, related name `valuation_history`, already ordered `-date`). Both are lists, not QuerySets, and each is one query. Factor the designation logic out of `get_executor_portfolio_context` so both use one helper.
- `src/my_garage/estate_views.py` -- add `portal_item_detail` and `portal_item_photo`, following the `portal_dashboard` pattern.
- `src/my_garage/estate_urls.py` -- add `portal/items/<int:item_id>/` (`executor_item_detail`) and `portal/items/<int:item_id>/photo/` (`executor_item_photo`).
- `src/my_garage/templates/my_garage/estate/portal/item_detail.html` -- new. It extends `portal/_base.html` with a back link to the dashboard. The photo `<img>` has alt text set to the item name and points at the photo route.
- `src/my_garage/templates/my_garage/estate/portal/dashboard.html` -- link each item name, in both the table and the cards, to its detail page.
- `src/my_garage/models.py` -- `ValuationSnapshot` has `market_value`, `cost_basis`, `equity`, `snapshot_date`. `BeneficiaryAssignment.conditional_note`.
- Tests: follow `tests/functional/test_estate_story2_3.py` (`_executor_client`) and `tests/unit/test_estate_portfolio_selector.py` (`_ctx`).

## Tasks & Acceptance

**Execution:**
- [x] `src/my_garage/api/selectors.py` -- add `get_item_display_custom_fields`, a shared designation helper, and `get_executor_item_detail_context`.
- [x] `src/my_garage/views.py` -- the owner detail view calls `get_item_display_custom_fields`. No behaviour change.
- [x] `src/my_garage/estate_views.py` + `estate_urls.py` -- add the detail and photo views and their routes.
- [x] Templates -- `item_detail.html` (sections in a fixed order, WCAG AA, mobile); link the dashboard rows.
- [x] `tests/unit/test_estate_item_detail_selector.py` -- ownership `None`, snapshot scoping, designation states, custom fields parity with the owner view.
- [x] `tests/functional/test_estate_story2_4.py` -- every matrix row, plus the dashboard links.

**Acceptance Criteria:**
- Given the portfolio dashboard, when the executor clicks an item, then its detail page opens.
- Given a detail page, when the executor uses the back link, then they return to the dashboard.
- Given an owner viewing their own item page, when it renders, then its custom fields are unchanged by the selector move.

## Implementation Notes

- `get_item_display_custom_fields(item)` in `api/selectors.py` now holds the owner view's custom-field rules: skip system fields, enrichment keys (`specs`/`features`/`migrated`) and empty values. The owner view calls it. The view still builds `system_field_names` because its edit form uses it.
- `_designation_fields(item)` is shared by `get_executor_portfolio_context` (whose output is unchanged) and the new `get_executor_item_detail_context(owner, token, item_id)`. The detail selector runs 4 queries: item, this activation's snapshot, service records, valuation history. Both lists are newest first, ordered `-date, -pk`.
- `portal_item_detail` logs `ITEM_VIEW` after render, on GET only. `portal_item_photo` serves `item.photo` via `static_serve` with `Cache-Control: private, no-store`, plus `never_cache` from the decorator. It returns 404 when the item isn't owned, has no photo, or the file is missing.
- Page sections, in order: identity + photo/placeholder, value at activation (date, market value, cost basis, equity, then current value), beneficiary + "Owner's note", details (purchase, custom fields, notes), service records, valuation history.
- Dashboard item names now link to the detail page, in both the table and the cards.
- Gate run by me: unit 368, functional 539, lint and format clean, no migrations.

## Spec Change Log

## Review Triage Log

**Code review pass 1 (2026-10-27)** — layers: blind (B), edge-case (E), verification-gap (V).

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| V-o1 | Negative equity rendered as positive | medium | `currency_display` returns `abs()` → patch (signed `nfp_display` for equity) |
| V1/B3/B4/E5 | Snapshot cost basis / equity untested; "$60"/"$100"/"—" satisfied elsewhere on the page | medium | pre-verified (V) → patch (tests scoped to the snapshot section, distinctive values) |
| B1 | Photo-route ownership filter untested (404 came from "no photo") | medium | `test_other_owner…` used an item with no photo → patch (test) |
| B2 | Photo route: revoked token and HEAD untested | low | same decorator as the detail page; cheap → patch (tests) |
| B5 | `"<img" not in body` checks the whole page | low | breaks once the base gains an image → patch (assert the photo URL is absent) |
| B6 | `portal_item_photo` queries the ORM in the view | low | breaks the views-use-selectors rule; duplicates the ownership lookup → patch (`get_executor_item`) |
| B7 | System-field rule duplicated between the selector and the owner view | low | the owner edit form and the display can drift → patch (`get_system_field_names`) |
| E7 | Owner view gains a query (`item.collection_type` not cached) | low | `get_object_or_404` doesn't select_related → patch (optional `collection_type` param) |
| B8/E4 | Custom-field labels from keys; lists/dicts/bools shown as reprs | low | the owner page already behaves this way (pre-existing) → defer (`deferred-work.md`) |
| B9 | "Owner's note" vs "Owner notes" confusable | low | trivial copy → patch ("Owner's wishes for this item" / "Item notes") |
| B10/V-o2 | `activated_at` unused; unused load and row keys | low | → patch (drop `activated_at`; the load is now used by equity); row keys are harmless → reject |
| B11 | Rendered valuation order and the charitable detail untested | low | → patch (tests); owner-page parity is already covered by existing owner-view tests passing, plus the selector parity test |
| B12 | Same-day valuations look identical | low | `GenericValuationHistory.date` is a datetime → patch (show the time) |
| B13 | Diff omits the spec and sprint-status | false | by design: review layers get the code diff; the spec goes to the edge-case layer as the claims file |
| E1 | Photo name set but file missing → broken `<img>` | low | rare; the fix needs a storage check on every render → reject |
| E2/E3 | Non-dict `field_schema` / `custom_fields` → 500 | false | code moved unchanged from the owner view; forms and blueprints always write dicts; no path to a non-dict shown |
| E6 | Fixture uses an invalid `relationship="C"` | low | → patch ("Child") |

## Verification

**Commands:**
- `pixi run pytest tests/unit/ -x -q` -- expected: all pass
- `pixi run pytest tests/functional/ -x -q` -- expected: all pass
- `pixi run lint` -- expected: zero errors
- `pixi run -- ruff format --check .` -- expected: zero diffs
