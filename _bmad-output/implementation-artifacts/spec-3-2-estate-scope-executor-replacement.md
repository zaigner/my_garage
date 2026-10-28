---
title: 'Story 3.2: Estate Scope & Executor Replacement'
type: 'feature'
created: '2026-10-28'
status: 'done'
route: 'dispatch'
baseline_commit: 'df641f3c9af425f472149979adf66b05390744f5'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-3-1-activation-snapshot-integrity.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** This story fixes three findings from the Epic 2 retro:
- **R7:** items in collections the owner deleted (soft-deleted, `CollectionType.is_active=False`) still appear in the estate: in activation snapshots, on the owner's estate pages, and in the executor portal. The rest of the app hides them.
- **R6:** typing a different person into the executor Update form leaves the previous executor's code live.
- **R8:** the portal labels the snapshot's purchase-price figures "Cost basis" and "Equity", which don't match the app's cost basis.

**Approach:**
- Every estate item query ignores soft-deleted collections.
- Saving the executor under a different name revokes the active code, after a confirm.
- The two snapshot labels are renamed. The data is unchanged.

## Boundaries & Constraints

**Always:**
- The soft-delete filter is `collection_type__is_active=True`, applied in a selector or service, never in a template.
- Revocation reuses `revoke_executor_access(user, request=request)`, so `TOKEN_REVOKED` is logged.
- A name change is detected by comparing names after trimming, collapsing whitespace and ignoring case. "jo  smith" and "Jo Smith" are the same person.
- Query counts stay the same: the portfolio at 2, the detail at 4, the estate dashboard at 3.
- Views keep calling selectors and services.

**Never:**
- Migrations or snapshot data changes.
- Changing labels outside the executor portal (owner pages, NFP).
- Beneficiary features.
- Revoking on a contact-only edit.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Activate with a soft-deleted collection | items in an active and an inactive collection | snapshots only for the active collection's items | — |
| Owner estate dashboard and profile card | same | totals, completeness % and the item list count only active-collection items | — |
| Assign overview | same | lists only active-collection items | — |
| Executor portfolio | same | inactive-collection items not listed and not counted | — |
| Executor item detail and photo | an inactive-collection item id | 404 | — |
| Soft-deleted after activation | a collection deactivated after its items were snapshotted | its items show as "Removed after activation" rows (stored name, activation value, no link), so "value at activation" is unchanged; detail returns 404 (decided 2026-10-28) | — |
| Executor name changed | active code, POST with a different name | executor saved; code revoked; `TOKEN_REVOKED` logged; message says the code was revoked | — |
| Name unchanged except case or spacing | active code, POST "jo  smith" for "Jo Smith" | saved; code kept | — |
| Contact-only edit | active code | saved; code kept | — |
| Name changed, no active code | no token or a revoked one | saved; nothing revoked; normal message | — |
| First designation | no executor yet | saved; nothing revoked | — |
| Confirm prompt | executor page with an active code | the Update form asks "this revokes the current access code" only when the name field differs from the stored name | without JS the server still revokes |
| Portal labels | item detail with a snapshot | "Purchase price" and "Value minus purchase price"; no "Cost basis" or "Equity" | — |

</frozen-after-approval>

## Code Map

- **Activation**, `src/my_garage/api/services.py:222`: the items loop inside `activate_estate_plan` filters `collection_type__is_active=True`.
- **Owner estate dashboard**, `src/my_garage/api/selectors.py:207-246` (`get_estate_dashboard_context`): add the filter to Q2. The profile card reads this same selector (`src/config/views.py:152`).
- **Assign overview**, `src/my_garage/estate_views.py:426-438` (`assign_overview`): it queries the ORM in the view. Move the query into a selector (`get_estate_assign_items(user)`) with the filter.
- **Executor portfolio**, `src/my_garage/api/selectors.py` (`get_executor_portfolio_context`, Q1 at about `:401`): add the filter to Q1. A snapshot whose item is not in Q1 (deleted, or in a collection soft-deleted after activation) becomes a removed row, the same as `item_id is None`. Build removed rows from `snapshots` minus the Q1 ids, using the stored `item_name`, with no extra queries.
- **Executor item lookup**, `get_executor_item` (`selectors.py:~318`): add the filter. This covers the detail page and the photo route.
- **Executor form**, `src/my_garage/estate_views.py:205-224` (`executor_view`):
  - Move the save into a service `save_executor(user, form, request) -> bool`, which returns whether a code was revoked.
  - Compare with `" ".join(name.split()).casefold()`, the old stored name against the new.
  - Message: "Executor updated. Their previous access code has been revoked." when a code was revoked; otherwise keep the existing message.
- **Confirm prompt**, `src/my_garage/templates/my_garage/estate/executor.html:49-78` (Update form): when an active code exists, add `data-current-name` and an `onsubmit` confirm that fires only when the trimmed and case-folded name differs. The view passes `has_active_code` from `get_executor_access_status`.
- **Portal labels**, `src/my_garage/templates/my_garage/estate/portal/item_detail.html:41,45`: "Cost basis" becomes "Purchase price", and "Equity" becomes "Value minus purchase price".
- **Tests:**
  - Grep `tests/` for "Cost basis" and "Equity" assertions on portal pages and update them.
  - Existing estate tests create collections with the default `is_active=True`, so they are unaffected.

## Tasks & Acceptance

**Execution:**
- [x] `src/my_garage/api/services.py`, `src/my_garage/api/selectors.py` -- the soft-delete filter in activation, the estate dashboard, the new assign selector, the portfolio (removed rows for out-of-scope snapshots) and `get_executor_item`; `save_executor` service.
- [x] `src/my_garage/estate_views.py` -- `assign_overview` uses the selector; `executor_view` uses `save_executor` and passes `has_active_code`.
- [x] `src/my_garage/templates/my_garage/estate/executor.html`, `portal/item_detail.html` -- the confirm prompt and the labels.
- [x] `tests/unit/test_estate_scope_selectors.py` (new) -- every scope row of the matrix, plus query counts.
- [x] `tests/functional/test_estate_story3_2.py` (new) -- the executor-replacement rows, the confirm attribute rendered only with an active code, labels, the detail and photo 404s, assign overview, and the profile card totals.

**Acceptance Criteria:**
- Given an owner who soft-deletes a collection before activating, when the executor opens the portal, then none of its items appear and the totals match what the owner sees in their collections.
- Given an active executor code, when the owner replaces the executor's name and saves, then the old code no longer opens the portal on its next request.

## Implementation Notes

- **Scope filter:** `collection_type__is_active=True` is in `activate_estate_plan`, `get_estate_dashboard_context` (Q2), the new `get_estate_assign_items(user)` (returns a list), `get_executor_portfolio_context` (Q1) and `get_executor_item`. The detail and photo routes both go through `get_executor_item`, so both return 404.
- **Removed rows:** the portfolio builds removed rows from the Q2 snapshots whose `item_id` is not in Q1. That covers a null item and an item whose collection was soft-deleted after activation. Several same-token rows for one out-of-scope item collapse to the newest, the same as current items. Query counts are unchanged: 2 for the portfolio, 4 for the detail, 3 for the dashboard.
- **`save_executor(user, form, request=None) -> bool`:** it reads the stored name inside `transaction.atomic()`, before saving. The bound ModelForm has already copied the new name onto the instance, so the stored name has to come from the database. It revokes through `revoke_executor_access` only when a stored name exists and its `" ".join(name.split()).casefold()` key differs.
- **Executor page:** `has_active_code` is true when the token returned by `get_executor_access_status` has `is_active` set. That matches what `revoke_executor_access` would revoke, including an expired code that is still flagged active. The Update form gets `data-current-name` and an `onsubmit` confirm that compares trimmed, whitespace-collapsed, lower-cased names. A hint under the name field reads "Saving a different name revokes the current access code." It is linked to the input with `aria-describedby`, so users without JS are told too. A revoking save shows "Executor updated. Their previous access code has been revoked — issue a new code from Activate Estate Access."
- **Assign POSTs:** `item_assign` and `item_assign_remove` look up the `CollectionType` with `is_active=True`, so an item in a soft-deleted collection returns 404 and nothing is written.
- **Snapshot ordering:** both Q2 queries use `.order_by("-created_at", "-pk")`, so "newest row wins" is deterministic.
- **Labels:** in the portal detail snapshot block, "Cost basis" became "Purchase price" and "Equity" became "Value minus purchase price". No tests asserted the old labels.
- **Existing test changed:** in `tests/functional/test_estate_story2_2.py`, `test_executor_update_keeps_token` posted a different name ("Jo" to "New") and expected the code to survive. That is the R6 bug. It is now `test_executor_contact_update_keeps_token` and edits only the contact info.
- **Gate:** 408 unit and 591 functional tests pass; no pending migrations; lint and format are clean.

## Spec Change Log

## Review Triage Log

**Code review pass 1 (2026-10-28).** Layers: blind (B), edge-case (E), verification-gap (V).

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| E4/B2 | `item_assign` / `item_assign_remove` still accept items in soft-deleted collections | low | Their `CollectionType` lookups have no `is_active` filter (`estate_views.py:265, :313`), so a direct POST writes an assignment and a change-log row for an out-of-scope item. **Patch:** filter plus a 404 test. |
| B5 | After a revoking name change, nothing tells the owner the new executor has no code | low | Real. **Patch:** the message points to Activate Estate Access. |
| B7 | The no-JS hint is untested, overstates the rule, and isn't tied to the input | low | **Patch:** reword it, add `aria-describedby`, and assert it. |
| B8 | The label test checks the whole page for "Cost basis" / "Equity" | low | Breaks the CLAUDE.md rule that "must not appear" checks are scoped to the element. **Patch:** scope it to the snapshot `<dl>`. |
| B10 | Newest-row dedupe relies on `-created_at` with no tie-breaker | low | Equal timestamps would make the dedupe and its test nondeterministic. **Patch:** `order_by("-created_at", "-pk")` in both selectors. |
| V1 | The confirm prompt's comparison logic is never run by a test | low | Pre-verified (V). There's no JS or browser harness, and server-side revocation is covered. **Defer** (`deferred-work.md`). |
| E5/B3 | The profile's `total_items` and the home portfolio totals still count soft-deleted items | low | This predates the story (non-estate counts). The profile now shows two counts that can differ. **Defer** (`deferred-work.md`). |
| E1/B6/V-o1 | The JS and Python name normalisation differ (`casefold` vs `toLowerCase`, U+FEFF) | low | Exotic input only, and the server decides. Aligning them needs a custom whitespace set. Rejected; folded into the V1 deferral. |
| E3 | `has_active_code` is true for an expired token that is still `is_active` | low | That matches what `revoke_executor_access` deactivates, and the implementer chose it deliberately. The message stays true. Rejected. |
| E2 | Two concurrent first designations hit the `OneToOne` IntegrityError | low | The old view behaved the same way. It needs two simultaneous first saves. Rejected. |
| B9 | `save_executor` doesn't lock against a concurrent activation | low | Needs the owner to activate in another tab within the same request window. Rejected. |
| B4 | `executor_view` runs the 3-query status selector just to get one boolean | low | Two extra queries on an owner settings page. Rejected. |
| B1 | Sprint status says in-progress while the spec says in-review | false | Step 5 of the workflow moves it to `review`. |

## Verification

**Commands:**
- `pixi run pytest tests/unit/ -x -q` -- expected: all pass
- `pixi run pytest tests/functional/ -x -q` -- expected: all pass
- `pixi run manage makemigrations --check --dry-run` -- expected: "No changes detected"
- `pixi run lint` -- expected: zero errors
- `pixi run -- ruff format --check .` -- expected: zero diffs
