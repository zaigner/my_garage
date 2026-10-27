---
title: 'Story 3.1: Activation Snapshot Integrity'
type: 'feature'
created: '2026-10-27'
status: 'done'
route: 'dispatch'
baseline_commit: 'c69fe3e14d7c21fcac723f1e15e908a55da7c05e'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There are two gaps:
- Activation snapshots are matched to an executor code only by timestamp (`created_at >= token.issued_at`).
- A snapshot is CASCADE-deleted with its item.

So deleting an item after activation silently lowers the "value at activation", which breaks FR39 and NFR17. The dashboard and the detail page can also pick different rows (Epic 2 retro, R4).

**Approach:**
- Each snapshot gets a foreign key to the token it was taken for, and keeps the item's name. Item deletion only nulls `item`.
- Both portal selectors read the snapshots by `token`.
- The dashboard keeps removed items as "Removed after activation" rows: stored name, activation value, no link.
- A migration backfills existing rows and can be reversed.

## Boundaries & Constraints

**Always:**
- The app still issues no `update()` or `delete()` on `ValuationSnapshot`. `SET_NULL` on item deletion is the only change Django makes to a row.
- Views keep using selectors and services.
- The portfolio selector stays at 2 queries; the detail selector stays at 4.
- Owner cascade (FR41) is unchanged, so deleting the owner still removes their snapshots.
- The reverse migration is provided and tested (NFR19).

**Never:**
- Snapshot labels, soft-deleted collections, executor replacement (Story 3.2).
- Beneficiary features.
- Any change to `MANUAL` snapshots beyond the schema; they keep `token` null.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Activate | owner with 2 items | 2 snapshots, each with `token` = the new token and `item_name` = the item's name | the existing rollback-on-failure test still passes |
| Reactivate | second activation | the new rows carry the new token; the dashboard for the new session reads only those | — |
| Item deleted after activation | delete one of 2 items | the snapshot row remains with `item=None`; the dashboard lists a "Removed after activation" row with the stored name and its activation value, no link; "value at activation" total unchanged | — |
| Removed row in totals | as above | counted in `snapshot_total` and `snapshot_count`; not in `items_total`, `unassigned_count`, `current_total` or the delta; `removed_count` = 1 | — |
| Item added after activation | new item | "Added after activation", as today | — |
| Snapshot of another token | rows from an earlier activation | ignored by both selectors | — |
| Detail of a deleted item | GET the old item id | 404, as today | — |
| Backfill | existing ESTATE_ACTIVATION rows | `token` = the owner's latest token with `issued_at <= created_at`; `item_name` from the item; MANUAL rows keep `token` null | no matching token → `token` stays null |
| Reverse migration | rows with `item=None` exist | those rows are deleted (the old schema requires an item), then `item` goes back to CASCADE and the new fields are dropped | — |

</frozen-after-approval>

## Code Map

- `src/my_garage/models.py:618-649` (`ValuationSnapshot`):
  - Add `token = FK("EstateAccessToken", SET_NULL, null=True, blank=True, related_name="valuation_snapshots")` and `item_name = CharField(max_length=200, blank=True)`.
  - Change `item` to `SET_NULL, null=True, blank=True`.
  - `__str__` must not touch `self.item` (use `item_name`).
- `src/my_garage/migrations/0022_…` -- one migration:
  - `AddField` token and item_name, `AlterField` item, then `RunPython(backfill, reverse)`.
  - Reverse function: `ValuationSnapshot.objects.filter(item__isnull=True).delete()`, run before Django reverses the AlterField. RunPython operations reverse in the opposite order, so put the delete in the reverse of a RunPython that sits *after* the AlterField.
  - Match the style of `0021_backfill_estate_token_expiry.py` (`apps.get_model`).
- `src/my_garage/api/services.py:190-241` (`activate_estate_plan`): snapshots are built before the token exists. Set `token=new_token` on each (or build them after `create`) and `item_name=item.name`, still inside the atomic block with one `bulk_create`.
- `src/my_garage/api/selectors.py:368-441` (`get_executor_portfolio_context`):
  - Q2 becomes `.filter(owner=owner, snapshot_trigger="ESTATE_ACTIVATION", token=token)`, fetching `item_id`, `item_name`, `market_value`.
  - Build `rows` for current items as today, plus `removed_rows` (`item_id is None`) as `{"item": None, "item_name", "snapshot_value", "removed": True}`.
  - Return `removed_rows` and `removed_count`.
  - Update the docstring.
- `src/my_garage/api/selectors.py:446-490` (`get_executor_item_detail_context`): replace `created_at__gte=token.issued_at` with `token=token`.
- `src/my_garage/templates/my_garage/estate/portal/dashboard.html:78-110` -- after the item rows, render `removed_rows` in both the table and the cards:
  - the name with no link, plus a "Removed after activation" label;
  - collection "—";
  - value through `_money.html`;
  - current value "—";
  - beneficiary "—".
  - Mention `removed_count` next to the item total when it's non-zero.
- `src/my_garage/admin.py` -- if `ValuationSnapshot` is registered, check that its list display works with a null `item`.
- Tests that build snapshots by hand, which must now set `token`:
  - `tests/unit/test_estate_portfolio_selector.py:90`
  - `tests/unit/test_estate_item_detail_selector.py:68`
  - Earlier-activation cases currently rely on `created_at`. Re-express them with explicit tokens and keep their intent.
- `tests/unit/test_estate_activation_service.py` -- add token and item_name assertions.

## Tasks & Acceptance

**Execution:**
- [x] `src/my_garage/models.py` + `src/my_garage/migrations/0022_valuationsnapshot_token_item_name.py` -- fields, SET_NULL, backfill and reverse.
- [x] `src/my_garage/api/services.py` -- set token and item_name at activation.
- [x] `src/my_garage/api/selectors.py` -- token filtering, removed rows, removed_count.
- [x] `src/my_garage/templates/my_garage/estate/portal/dashboard.html` -- removed rows in the table and the cards.
- [x] `tests/unit/test_estate_snapshot_integrity.py` (new) -- activation fields, item delete keeps the row, both selectors by token, totals, query counts.
- [x] `tests/unit/test_estate_snapshot_migration.py` (new) -- forward backfill and reverse, with `django_db` migration-executor tests (`MigrationExecutor` migrate to 0021 → seed → 0022 → assert → back to 0021).
- [x] `tests/functional/test_estate_story3_1.py` (new) -- dashboard removed row (table and cards, no link), totals, detail 404.
- [x] Existing estate tests -- update the hand-built snapshots to carry `token`.

**Acceptance Criteria:**
- Given an executor session, when the owner deletes an item after activation, then the dashboard's "Value at activation" total is the same as before the deletion.
- Given the dashboard and the detail page for one item, when both render, then they show the same value at activation.
- Given `pixi run manage makemigrations --check`, when run after this change, then no migrations are pending.

## Implementation Notes

- **Model:** `ValuationSnapshot` has `token FK(EstateAccessToken, SET_NULL, null)` and `item_name CharField(200)`, and `item` is now `SET_NULL, null`. `__str__` uses `item_name`. Owner deletion still cascades.
- **Migration 0022:**
  - It adds the fields, alters `item`, and then runs `RunPython`, placed last so that its reverse runs first.
  - Forward: on ESTATE_ACTIVATION rows only, it sets `token` to the owner's newest token with `issued_at <= created_at` and `item_name` from the item. MANUAL rows are untouched.
  - Reverse: it deletes rows with `item=None`.
- **Activation:** `activate_estate_plan` reads the items and builds the snapshots inside `transaction.atomic()` after creating the token, with one `bulk_create`.
- **Selectors:** both filter `token=token`.
  - The portfolio selector returns `removed_rows` (sorted by name) and `removed_count`.
  - Removed rows count toward `snapshot_total` and `snapshot_count` only.
  - Duplicate same-token rows resolve to the newest in both selectors.
  - Query counts stay at 2 and 4.
- **Dashboard:**
  - Removed rows appear in the table and the cards, with no link and "—" for collection, current value and beneficiary.
  - The Items card shows "Plus N removed after activation", and the Current value card shows "Excludes N removed after activation".
  - The "N of M items valued" denominator includes removed items.
  - An estate whose items were all removed still lists them.
- **Migration tests:** the test settings disable migrations, so these tests fake-apply the graph, really migrate `my_garage` to 0021 and back, and always restore the leaf. They use `transaction=True`.
- **Gate:** unit 389, functional 573, full suite 1023; no pending migrations; lint and format clean.

## Spec Change Log

## Review Triage Log

**Code review pass 1 (2026-10-27).** Layers: blind (B), edge-case (E), verification-gap (V).

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| V1 | The migration test can't detect a missing `owner_id` filter in the backfill | medium | Pre-verified (V). The other owner's token is issued "now", after every seeded snapshot. **Patch:** seed it between two of this owner's events, and assert. |
| V2 | The `items_total + removed_count` denominator is untested | low | Pre-verified (V). Reverting it passes every test. **Patch:** a "1 of 2 items valued" test. |
| B2 | `"of 1 items valued" not in after` can't catch its target regression | low | That regression would render "1 of 2". **Patch:** assert `"items valued"` is absent. |
| B3 | The `item_name` backfill writes MANUAL rows, against the Never list | low | `ValuationSnapshot.objects.update(item_name=…)` hits every row. The spec is clear, so the code deviates. **Patch:** restrict it to ESTATE_ACTIVATION. |
| E1 | The portfolio dict keeps the oldest of two same-token rows; detail `.first()` keeps the newest | low | Needs duplicate rows, which activation never writes, but the fix is direct. **Patch:** keep the first occurrence. |
| E3/B9 | Items are read and snapshots built outside `atomic`, so a concurrent delete makes `bulk_create` fail on the FK | low | Present since 2.1. The spec's code map asks for the build inside the block, and the fix is moving lines. **Patch.** |
| E4 | The `at_0021` fixture runs `_migrate(BEFORE)` outside `try` | low | A failure there would leave the schema half-reverted for later tests. **Patch.** |
| B5 | The Value-at-activation and Current-value cards cover different item sets | low | Removed items are counted only in the first, and the hint sits on the Items card. **Patch:** a note on the Current value card. |
| B12 | Typo in `epic-3-context.md` ("an \"cannot…\"") | low | **Patch** (applied by the orchestrator). |
| E2 | Selectors called with `token=None` would match unbound rows | false | Every caller passes `request.estate_token`, which `executor_required` always sets to a real token (`estate_views.py:75-76`). |
| B1 | Story 3.2's soft-deleted exclusion will drop snapshot totals again | false | Not a defect in this diff: Q1 returns every owned item today. Story 3.2 must decide how snapshots of collections soft-deleted after activation count; noted for its planning. |
| B4 | Sprint status says in-progress while the spec says in-review | false | Step 5 of the workflow moves the story to `review`. |
| B6 | Removed rows have no collection or beneficiary stored | low | The intent defines removed rows as stored name plus value. The item no longer exists, so there's no designation to carry out. Storing more needs new fields. Rejected. |
| B7 | Bare "—" cells in removed rows lack screen-reader text | low | Same convention as the null values of Story 2.3 (`_money.html`), under labelled column headers. Rejected. |
| B8 | Append-only isn't enforced in code | low | The design dates from 2.1 (Epic 2 retro, accepted). A guard would add complexity. Rejected. |
| B10 | The reverse migration drops rows without reporting a count | low | Only on rollback, and production has no item-less rows. Rejected. |
| B11 | The backfill's `(-issued_at, -pk)` tie-break is untested | low | Equal `issued_at` (`auto_now_add`, microseconds) is practically unreachable. Rejected. |
| B13 | The spec isn't in the review diff | false | By design: it's the claims file. |

## Design Notes

The backfill maps each activation snapshot to the token it was taken for. `activate_estate_plan` creates the token and its snapshots in one transaction, so a snapshot's own token is the newest token of that owner with `issued_at <= created_at`. For the reverse migration, the old schema requires an item, so rows whose item was deleted can't come back. They're dropped, and the docstring says so.

## Verification

**Commands:**
- `pixi run pytest tests/unit/ -x -q` -- expected: all pass
- `pixi run pytest tests/functional/ -x -q` -- expected: all pass
- `pixi run manage makemigrations --check --dry-run` -- expected: "No changes detected"
- `pixi run lint` -- expected: zero errors
- `pixi run -- ruff format --check .` -- expected: zero diffs

**Manual checks:**
- Do not migrate the developer's `db.sqlite3`; the forward and reverse paths are covered by the migration test above.
