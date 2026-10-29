---
title: 'Epic 3 retro item 11: extract shared estate helpers before Epic 4'
type: 'refactor'
created: '2026-10-29'
status: 'done'
baseline_commit: '2c46c36741e61a169c91b64c7c12466a797edb31'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-retro-2026-10-29.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Epic 3 wrote four things twice: the token-bound single-item snapshot lookup, the item-photo serving block, the "designated item" rule (already diverged: the executor side has no `item__owner` filter), and the item-detail template body. Estate code is also about 60% of `api/selectors.py`. Epic 4's PDFs would be a third copy of each (retro F13, F14).

**Approach:** A behaviour-neutral refactor. Extract one helper per duplicate, have both executor and beneficiary callers use it, and move the estate selectors into a new `api/estate_selectors.py`. Every page, response, header, log row and query count stays the same.

## Boundaries & Constraints

**Always:**
- Existing test bodies don't change. Only their `import` lines may change, to the new module.
- The designated rule is one helper used by all three places. It includes `item__owner=<owner>`. Assignments are always same-owner (`item_assign` scopes the item to `request.user`, and `BeneficiaryAssignmentForm` scopes beneficiaries to the owner), so the executor side's new filter excludes nothing reachable.
- Query counts in selector docstrings and tests stay the same.
- One import direction: `estate_selectors` may import from `selectors` (`get_item_display_custom_fields`); `selectors` never imports `estate_selectors`.

**Never:**
- No re-export shim in `selectors.py` (it would be a circular import).
- No migrations, URL or template-name changes, no copy changes, no new features (Q2/Q3/Q4 ship in a later PR).
- Don't merge the executor and beneficiary 404 behaviour. The executor raises `Http404`; the beneficiary returns `_beneficiary_not_found`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected | Error handling |
|---|---|---|---|
| Beneficiary photo | own item, photo file present | 200, `Cache-Control: private, no-store` | — |
| Beneficiary photo, missing | no photo, file gone, or not their item | `_beneficiary_not_found` (uncached 404 page) | `Http404` from the helper is caught |
| Executor photo, missing | same cases | `Http404` raised | unchanged |
| Cross-owner assignment | beneficiary of owner A assigned owner B's item (only via ORM) | not counted for A's executor; not shown to A's beneficiary | — |

</frozen-after-approval>

## Code Map

- `src/my_garage/api/selectors.py` -- source. Estate code to move: `get_item_estate_assignment` (:73), `get_estate_dashboard_context` through `get_beneficiary_item_detail_context` (:210-534, including the `ESTATE_*`/`EXECUTOR_VIEW_EVENTS` constants), `_sum_or_none` (:536), and `get_executor_item` through `get_executor_item_detail_context` (:576-778). Stays: NFP, search, YoY, `_ENRICHMENT_KEYS`, `get_system_field_names`, `get_item_display_custom_fields` (the owner page uses them), and `media_file_owner_id`.
- Duplicate snapshot lookup -- `get_beneficiary_item_detail_context` (~:510) and `get_executor_item_detail_context` (~:748): `ValuationSnapshot.objects.filter(item, owner, snapshot_trigger="ESTATE_ACTIVATION", token).order_by("-created_at","-pk").first()`. The portfolio (~:660) uses the same filter without `item`.
- Duplicate designated rule -- `_designated_beneficiaries` (:329, `Count` over `assignments__`), `_executor_link_beneficiaries` (:348: `Exists` subquery plus the same `Count` Q), and `_beneficiary_assignment_qs` (:466, has `item__owner`).
- `src/my_garage/estate_views.py` -- `beneficiary_item_photo` (:369) and `portal_item_photo` (:403): both `static_serve` + `private, no-store`. Its imports (:25) move to `estate_selectors`.
- `src/my_garage/templates/my_garage/estate/{beneficiary,portal}/item_detail.html` -- identical identity header (the photo URL name differs), snapshot section, details section and service-records section. They differ in the back link, the conditional-note block, the executor's Beneficiary and Valuation history sections, and the base template. Existing partials: `portal/_snapshot_detail.html`, `_money.html`.
- Importers to repoint: `src/my_garage/views.py` (`get_item_estate_assignment` only; NFP and custom-field names stay), `src/config/views.py` (`get_estate_dashboard_context`), the two lazy imports in `src/my_garage/api/services.py` (:268 `get_claimable_beneficiary_link`; :39 stays), and the import lines of `tests/unit/test_estate_*`, `test_beneficiary_*` and `test_epic3_retro_fixes.py`. `test_estate_item_detail_selector.py` imports `get_item_display_custom_fields`, which stays in `selectors`.

## Tasks & Acceptance

**Execution:**
- [x] Scratch, before any edit -- render the beneficiary and executor item-detail pages (with photo, note, snapshot, custom field and service record) and save the HTML outside the repo as the "before" baseline.
- [x] `src/my_garage/api/estate_selectors.py` (new) -- move the estate code listed above, unchanged. Add `designated_assignment_q(owner, prefix="")`, a `Q` holding `is_charitable=False`, `item__owner=owner` and `item__collection_type__is_active=True` behind the prefix. Use it in all three designated sites. Add `activation_snapshots(owner, token)` (queryset) and `get_activation_snapshot(owner, token, item)` (newest or None), and use them in both detail selectors and the portfolio.
- [x] `src/my_garage/api/selectors.py` -- delete the moved code and the now-unused imports.
- [x] `src/my_garage/estate_views.py` -- add `_serve_item_photo(request, item)`: it raises `Http404` for None, no photo or a missing file, and otherwise returns the `static_serve` response with `private, no-store`. Both photo views call it; the beneficiary view catches `Http404` and returns `_beneficiary_not_found`. Repoint the imports.
- [x] `templates/my_garage/estate/portal/_item_header.html`, `_item_activation.html`, `_item_provenance.html` (new) -- the shared header (it takes `photo_url`), the snapshot section, and the details plus service-records sections. Both detail templates include them.
- [x] Other importers -- repoint the imports listed in the Code Map.
- [x] `tests/unit/test_estate_shared_helpers.py` (new) -- tests for `designated_assignment_q` and `get_activation_snapshot`. Include the cross-owner row from the matrix for the executor list, `get_executor_beneficiary` and the beneficiary portal; and a newer snapshot under another token, which must not be picked.

**Acceptance Criteria:**
- Given the baseline, when the same pages render after the refactor, then the HTML is identical once whitespace is collapsed.
- Given the full suite, when it runs, then it passes with only import lines changed in existing tests.
- Given `api/selectors.py`, when grepped, then it has no estate code and no import of `estate_selectors`.

## Design Notes

`designated_assignment_q` serves two query shapes:

```python
BeneficiaryAssignment.objects.filter(designated_assignment_q(owner), beneficiary=OuterRef("pk"))
Count("assignments", filter=designated_assignment_q(owner, "assignments__"), distinct=True)
```

The partials live under `portal/`, next to `_snapshot_detail.html`, which the beneficiary page already includes.

## Verification

**Commands:**
- `pixi run pytest tests/unit/ -x -q`, `pixi run pytest tests/functional/ -x -q` -- all pass
- `pixi run lint`, `pixi run -- ruff format --check .` -- clean
- `command grep -n "estate\|Beneficiary\|ValuationSnapshot" src/my_garage/api/selectors.py` -- only the import block and the non-estate selectors remain
- the scratch "after" render, diffed against the baseline with whitespace collapsed -- no differences

## Implementation Notes

- **Test-body deviation (2 lines):** `tests/unit/test_beneficiary_claim_service.py` monkeypatches the dotted path `"my_garage.api.selectors.get_claimable_beneficiary_link"` inside two test bodies (`test_stale_read_cannot_double_claim`, `test_beneficiary_deleted_mid_claim`). With the function moved and no shim allowed, `monkeypatch.setattr` would raise, so both strings now name `my_garage.api.estate_selectors`. The change is a module path only, like an import line; no assertion changed.
- **Render baseline:** a scratch pytest module (outside the repo) rendered both detail pages for three items (photo + note + snapshot + custom fields + service record + valuation history; no photo; added after activation) and the photo endpoints (served, no photo, file deleted) for both roles. Before and after are identical once whitespace is collapsed. The one raw diff was the executor's valuation-history timestamp (`auto_now`, minutes apart between runs), masked in the comparison.
- **Mutation check:** dropping `item__owner` from `designated_assignment_q` fails 5 of the 9 new tests (every cross-owner case).
- `activation_snapshots` keeps the original `order_by("-created_at", "-pk")`; `get_activation_snapshot` adds `.filter(item=item).first()` on it, so the detail selectors still run one query each and the docstring counts (3 and 4) hold.
- `templates/.../portal/item_detail.html` keeps its `{% load my_garage_extras %}` line (harmless; removing it is out of scope).

## Spec Change Log

## Review Triage Log

Pass 1 (2026-10-29; blind B, edge-case E, verification-gap V on Opus). V: no gaps.

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| E1/E2/B10 | `_item_header.html` gets a pre-resolved `photo_url`: `{% url … as %}` swallows NoReverseMatch, and a caller that forgets it renders `<img src="">` | low | Real: Django's `as` form never raises. Tests assert the `src`, so a rename would be caught, but the partial is now shared. Direct fix → **patch**: the partial takes `photo_route` and resolves it itself |
| B9 | Partials' required context undocumented; Django renders a missing variable as empty | low | Real for a new includer. One comment line each → **patch** |
| B13 | `designated_assignment_q` through a to-many prefix duplicates rows in `.filter()` | low | Real; current callers use it only inside `Count(…, distinct=True)`. Docstring sentence → **patch** |
| B17 | `_serve_item_photo(item)` untyped | low | Cosmetic; one annotation → **patch** |
| E3/B15 | Two monkeypatch target strings inside test bodies changed, against the frozen "only import lines" rule | low | Real and disclosed in Implementation Notes. There is only one workable reading (no shim is allowed, so the string must follow the module), so not an intent gap. Fix would edit this spec → rejected. **Human (2026-10-29): accepted.** |
| B1a | `get_executor_access_status` docstring still says TOKEN_*/CODE_* | low | Pre-existing, moved unchanged; already recorded in `deferred-work.md` (F16, PR #40). Rejected as tracked |
| B1b | `get_item_display_custom_fields` docstring omits the beneficiary caller | low | Pre-existing since Story 3.5 → **defer** |
| B2 | `ESTATE_VIEW_EVENTS` is dead / `EXECUTOR_VIEW_EVENTS` hand-copied | false | Used by `test_event_groups_cover_every_event_type`; Story 4.3 is its reader. Rejected in the Epic 3 retro (EC11/ADV8): per the repeat-rejection rule, raised with the human. **Human (2026-10-29): reject again;** a comment at the constant now records why it stays, so reviews stop flagging it |
| B3 | Snapshot helpers match unbound rows when `token=None` | low | Same filter as before the refactor; both callers pass a non-None token (`get_beneficiary_session_link` and `executor_required` reject None). A guard for an undemonstrated state → rejected |
| B4 | "Live link" and token-usable rules still written several ways | low | Pre-existing and outside the four duplicates in the intent; fix adds a helper; Epic 4 doesn't read links → rejected |
| B5 | Owner dashboard counts an item whose beneficiary was deleted (`SET_NULL`) as assigned; the executor portal counts it unassigned | medium | Real (`models.py` BeneficiaryAssignment.beneficiary is SET_NULL; dashboard uses `Exists(assignment)`). Pre-existing → **defer** |
| B6 | `get_item_estate_assignment` checks `collection_type.owner`, not `item.owner` | false | The only caller (`views.py`) passes an item already scoped to `request.user`; no wrong outcome. Rejected |
| B7 | No test guards the import direction / estate-free `selectors.py` | low | A cycle fails loudly at import; fix adds a test for a style rule → rejected |
| B8 | Before/after render comparison not committed | false | V confirmed both pages' functional tests assert inside each moved section (headings, placeholders, photo `src`, current value). Rejected |
| B11 | Partials hard-code element ids; repeated if included per item in one document | low | No page includes them twice; Epic 4's PDF library is undecided. Rejected |
| B12 | Detail selectors still differ (`collection_type` arg) and repeat the service-records query | low | Both items have `collection_type` select_related, so the arg changes no query; outside the intent's four duplicates; fix adds a helper → rejected |
| B14 | No cross-owner test for a link-holder with only a cross-owner assignment | false | The `counted` filter is pinned by Ann's `item_count == 1` in `TestCrossOwnerAssignment`; dropping `item__owner` there makes it 2 (Ann also holds a cross-owner row). Rejected |
| B16 | CLAUDE.md §2/§6 don't mention `api/estate_selectors.py` | low | Edits an agent-context file → **defer** |
