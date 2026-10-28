---
title: 'Story 3.5: Beneficiary Item Detail View'
type: 'feature'
created: '2026-10-28'
status: 'done'
baseline_commit: '1d2f605569ccc073d15040a0c4986d5950ded0f6'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-3-4-beneficiary-portal-session.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The beneficiary portal (Story 3.4) lists the designated items as name, collection and current value only. A beneficiary cannot see an item's details, photo, the owner's wishes for it, or its value at activation (FR29).

**Approach:**
- `/estate/beneficiary/items/<item_id>/` renders one designated item, read-only, behind `beneficiary_required`.
- `/estate/beneficiary/items/<item_id>/photo/` serves its photo privately.
- Portal rows link to the detail page.
- Isolation reuses the Story 3.4 assignment filter in the ORM, so any other item returns 404.

## Boundaries & Constraints

**Always:**
- Detail and photo resolve the item only through the beneficiary's assignment: `beneficiary=link.beneficiary`, `is_charitable=False`, `item__owner=link.owner`, `item__collection_type__is_active=True`, `item_id=<id>`. Anything else gets the same bare uncached 404 as the portal (`_beneficiary_not_found`).
- Page content follows FR29:
  - name, collection type, and photo or a "No photo" placeholder
  - current value, purchase price and purchase date
  - custom fields (`get_item_display_custom_fields`), item notes, and service records (date, vendor, category, cost, description; newest first)
  - the assignment's `conditional_note`, shown prominently when non-blank
  - the activation snapshot bound to `link.issued_by_token`: snapshot date, value at activation, "Purchase price" and "Value minus purchase price". With no snapshot it reads "Added after activation".
- Both views are `require_safe`. On GET only, the detail page logs `BENEFICIARY_VIEW` with `item=`, `beneficiary=` and `token=link.issued_by_token`, after render. The photo route logs nothing.
- Photo: `static_serve` from `MEDIA_ROOT` with `Cache-Control: private, no-store`. No photo or a missing file returns 404.
- The detail selector's query count is fixed whatever the number of service records.

**Never:**
- Valuation history, receipt images, attachments, the beneficiary designation line, other beneficiaries' data, or links to owner/executor pages.
- New `EstateAccessLog` event choices or any migration.
- Changes to executor-portal behaviour or rendered output, claim/session logic, or link issuing.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Own item | session, GET own designated item with snapshot, 2 service records, note, custom field | 200 with every FR29 field, snapshot figures, note; `BENEFICIARY_VIEW` logged once with item name and beneficiary name | — |
| Added after activation | own item, no snapshot for this token | "Added after activation" | — |
| Snapshot of older token | only an older token's snapshot exists | "Added after activation" | — |
| Other / unassigned / charitable / soft-deleted collection / other owner / nonexistent | GET detail or photo | 404, identical body to portal 404 | no log |
| No / dead session | GET detail or photo | 404; dead session's beneficiary keys cleared | — |
| HEAD detail | own item | 200, nothing logged | — |
| POST detail or photo | own item | 405 | — |
| Photo | own item with photo | 200 bytes, `private, no-store` | no photo / missing file → 404 |
| Portal | session with items | each row's name links to its detail URL | — |

</frozen-after-approval>

## Code Map

- `src/my_garage/api/selectors.py:430` -- `get_beneficiary_assignments`. Extract its filter into `_beneficiary_assignment_qs(link)` and keep the ordering in the list function.
  - New `get_beneficiary_assignment(link, item_id) -> BeneficiaryAssignment | None`: `_beneficiary_assignment_qs(link).filter(item_id=item_id).select_related("item__collection_type").first()`.
  - New `get_beneficiary_item_detail_context(link, item_id) -> dict | None`, in 3 queries: assignment; the snapshot as `get_executor_item_detail_context:654` does, with `token=link.issued_by_token, owner=link.owner`; service records `order_by("-date", "-pk")`.
  - Return: `item`, `row` (`in_snapshot`, `snapshot_value`, `current_value`), `snapshot`, `conditional_note` (stripped), `custom_fields` (pass the loaded `collection_type`) and `service_records`.
- `src/my_garage/estate_views.py:276` (after `beneficiary_portal`) -- add `beneficiary_item_detail` and `beneficiary_item_photo`.
  - Order the decorators `require_safe` then `beneficiary_required`, as on the portal.
  - A None context returns `_beneficiary_not_found(request)`, not `raise Http404`; see the 3.4 note on `never_cache`.
  - The photo route mirrors `portal_item_photo:312`. Catch `Http404` from `static_serve` and return `_beneficiary_not_found`.
- `src/my_garage/estate_urls.py` -- `beneficiary/items/<int:item_id>/` → `beneficiary_item_detail`; `…/photo/` → `beneficiary_item_photo`.
- `src/my_garage/templates/my_garage/estate/portal/item_detail.html:28-50`:
  - Move the snapshot `<dl>` into a new `portal/_snapshot_detail.html` (takes `snapshot`). Include it from here, so the executor's rendered output stays the same.
  - The beneficiary page reuses it.
- `…/estate/beneficiary/item_detail.html` (new) -- extends `beneficiary/_base.html`.
  - Back link to `estate:beneficiary_portal`.
  - Section layout and classes as in `portal/item_detail.html`. Drop the Beneficiary and Valuation-history sections.
  - The note box ("Owner's wishes for this item") sits directly under the header.
- `…/estate/beneficiary/portal.html:22` -- wrap `a.item.name` in a link to `estate:beneficiary_item_detail`, with the same link classes as the back link.
- Reuse the fixtures from `tests/functional/test_estate_story3_4.py` (`owner`, `cars`, `ann`, `token`, `raw`, `ben`, `_assign`) and the photo-test pattern from `test_estate_story2_4.py:236-275` (`tmp_path` MEDIA_ROOT override, `ContentFile`).

## Tasks & Acceptance

**Execution:**
- [x] `src/my_garage/api/selectors.py` -- shared assignment queryset, `get_beneficiary_assignment` and `get_beneficiary_item_detail_context`.
- [x] `src/my_garage/estate_views.py`, `src/my_garage/estate_urls.py` -- the detail and photo views and their routes.
- [x] templates -- `portal/_snapshot_detail.html` (extracted), `beneficiary/item_detail.html`, and the portal links.
- [x] `tests/unit/test_beneficiary_item_detail_selector.py` (new):
  - context fields
  - every excluded case → None
  - token-bound snapshot selection
  - fixed query count at 1 and 3 service records
- [x] `tests/functional/test_estate_story3_5.py` (new):
  - every matrix row through the client
  - the 404 body equals the portal's no-session 404 body
  - the portal row's rendered `href` reaches the detail page (retro item 4)
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` -- `3-4` → done (PR #35 merged), `3-5` → in-progress.

**Acceptance Criteria:**
- Given the executor revokes the link mid-session, when the beneficiary requests a detail or photo URL, then it returns 404 and the session's beneficiary keys are gone.
- Given the existing executor item-detail tests, when the snapshot block is extracted, then they pass unchanged.

## Implementation Notes

- Implemented directly in the main session, not by a subagent.
- The photo route catches `Http404` from `static_serve` (missing file) and returns `_beneficiary_not_found`, so every 404 body is identical and uncached.
- A 404 on someone else's item leaves the beneficiary session intact; only a dead link clears the keys (as in `beneficiary_required`).
- `TestExecutorUnchanged` adds a direct check that the executor page still renders the extracted snapshot block; the existing Story 2.4 tests pass unchanged.
- Gate (pass 1): 462 unit and 667 functional tests pass; no pending migrations; lint and format are clean.
- Review patches:
  - E1: `item__pk` lookup.
  - B1/V-o1: `row` dropped from the context.
  - V1/B2: current and snapshot figures checked separately, with values moved after activation, plus section-scoped asserts.
  - V2/B3: service-record fields.
  - V3: the log row's token.
  - B8: no-photo 404 body and cache.
  - Mutation-checked: reverting to `item_id=` fails `test_404[huge_id]`; pointing "Current value" at the snapshot fails `test_every_field`.
- Gate after patches: 463 unit and 668 functional tests pass; no pending migrations; lint and format are clean.

## Spec Change Log

## Review Triage Log

**Code review pass 1 (2026-10-28).** Layers: blind (B), edge-case (E), verification-gap (V).

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| E1 | An item id above 2^63 → `OverflowError` 500 instead of the uniform 404 | low | Probed: `item_id=` raises on SQLite and `item__pk=` returns None. Production is Postgres. **Patch:** `item__pk`, plus a `huge_id` case in both isolation tests. |
| V1/B2 | Current value, Details purchase price and the snapshot figures can't be told apart: the fixtures keep equal values | low | Pre-verified. **Patch:** move values after activation and assert per section, including the snapshot date and the difference. |
| V2/B3 | Service-record date, category, cost and description are unchecked | low | Pre-verified. **Patch:** added to `test_every_field`. |
| V3 | The `token` on the `BENEFICIARY_VIEW` row is unchecked | low | Pre-verified. **Patch:** `entry.token == token`. |
| B1/V-o1 | The context's `row` is never read by the template | low | Confirmed: the template reads `snapshot` and `item` directly. It is a dead contract that the tests pinned. **Patch:** deleted it. |
| B8 | The no-photo 404 test checks only the status; the missing-file test skips `Cache-Control` | low | **Patch:** body and cache asserts added. |
| E2 | A photo name with a missing file shows a broken image, not the placeholder | low | Real, and the executor page does the same. The fix adds a storage check per render. Rare in everyday use. Rejected. |
| B10 | "Purchase price" appears in both the snapshot block and Details; they diverge if the price is edited | low | The snapshot block's label sits under the "Value at activation" heading, and the label is mandated (epic, frozen). The executor page is the same. Purchase prices rarely change after activation. Rejected; the user is told. |
| B6 | The selector doesn't guard `issued_by_token=None` (would match NULL-token snapshots) | low | Unreachable: `get_beneficiary_session_link` rejects a None token before any view runs. The fix adds a branch. Rejected. |
| E3 | The portal row link lacks the back link's `text-sm` | false | The Code Map's "same link classes" means the link styling (colour, underline, focus ring), and all of it is present. `text-sm` is sizing for the back link's secondary role; the row title keeps its size. |
| B4 | The photo route's `Cache-Control` line has no effect under `never_cache`, so its test proves nothing | false | `patch_cache_control` merges into the header, so the final header carries `private` and `no-store` either way. The outcome the spec requires holds. The line mirrors `portal_item_photo`. |
| B5 | No test has one item with both a current-token and an older-token snapshot | false | The existing test fails if the `token=` filter is dropped: the older snapshot would render "$777" and be returned as `snapshot`. |
| B7 | sprint-status says in-progress while the spec is in-review | false | Sprint status moves to review at presentation (step 5), as in 3.4 triage B11. |
| B9 | The Code Map's line numbers are off | false | The fix edits this spec, which triage rules out. |
| B11 | The executor page's HTML whitespace changed after the extraction | false | Whitespace inside the markup doesn't change the rendered page; the Story 2.4 tests pass unchanged. |

## Design Notes

- **Why reuse `BENEFICIARY_VIEW` with `item=`:** the log row's `item_name` tells portal views and item views apart, as Story 4.3's audit PDF needs. A new choice would add a migration for no behavioural gain.
- **Why no valuation history:** FR29 and the epic AC list the fields exactly, and history is not among them. The executor keeps it.

## Verification

**Commands:**
- `pixi run pytest tests/unit/ -x -q` -- expected: all pass
- `pixi run pytest tests/functional/ -x -q` -- expected: all pass
- `pixi run manage makemigrations --check --dry-run` -- expected: "No changes detected"
- `pixi run lint` -- expected: zero errors
- `pixi run -- ruff format --check .` -- expected: zero diffs
