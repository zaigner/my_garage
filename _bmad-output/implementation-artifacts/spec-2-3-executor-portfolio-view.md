---
title: 'Story 2.3: Executor Portfolio View'
type: 'feature'
created: '2026-10-26'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-2-2-executor-code-entry-session-revocation-access-log.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** An executor who enters a valid code lands on a placeholder page. They can't see what the estate holds, what it was worth when access was activated, or which assets have no beneficiary.

**Approach:** Replace the Story 2.2 stub at `/estate/portal/dashboard/` with the full read-only portfolio. The page shows:
- the owner's name and the activation date;
- a summary of total items, total snapshot value, total current value, and change since activation;
- every item the owner holds, with its collection type, snapshot value, current value, and beneficiary, or a prominent Unassigned badge (or the charity, for a charitable designation).

Null values show as "—". Each view writes a `PORTAL_VIEW` access-log entry. A new selector loads everything in at most three queries.

</frozen-after-approval>

## Implementation Notes

- `get_executor_portfolio_context(owner)` in `api/selectors.py` uses 2 queries:
  - items with `select_related` of collection type and assignment/beneficiary;
  - all of the owner's `ValuationSnapshot`s, newest first, keeping the first one per item.
- Item ordering matches the owner dashboard: collection type, then name. Items in inactive collection types are included, as they are on the owner dashboard.
- Designation:
  - A charitable assignment shows the organisation, or "Charitable bequest" when the name is blank, plus "(charitable)".
  - A beneficiary assignment shows the beneficiary's name.
  - No assignment, or an assignment whose beneficiary was deleted (SET_NULL), shows **Unassigned**.
  - When any item is unassigned, a banner uses the PRD's wording: "N asset(s) have no beneficiary designation … handled through the probate process."
- Totals:
  - The snapshot and current totals each sum only the values that are known.
  - The change since activation is summed only over items valued at both dates. When that's fewer than all items, a footnote says "Across X of Y items".
  - Delta exactly 0 renders "$0"; `nfp_display` would otherwise show "—". Individual values use `currency_display`, which also renders a genuine $0 value as "—".
- The activation date is the session token's `issued_at`. The snapshot for that token is created in the same transaction.
- A `PORTAL_VIEW` log entry is written on GET only. HEAD is allowed by `require_safe` but shows nothing to the executor, so it isn't logged.
- Templates:
  - `portal/_base.html` gains a `main_width` block. Code entry keeps `max-w-xl`; the dashboard uses `max-w-5xl`.
  - The dashboard extends the portal's own standalone base, not the owner chrome. That base is what "standalone" means in the epic.
  - Wide screens get a table with caption and `th scope`; narrow screens get stacked cards. Both use a shared `_designation.html` partial.
- Rows don't link anywhere yet; Story 2.4 adds item detail links.
- The Story 2.2 functional test that asserted the stub copy now asserts "Estate of".
- Tests: `tests/unit/test_estate_portfolio_selector.py` (11) and `tests/functional/test_estate_story2_3.py` (18), after review fixes.

- Post-review changes:
  - The selector now takes the session token and reads only that activation's `ESTATE_ACTIVATION` snapshots (`created_at >= token.issued_at`), fetching only `item_id` and `market_value`.
  - Rows carry `in_snapshot`, so items added later read "Added after activation". The context adds `snapshot_count` / `current_count` for "N of M items valued" notes.
  - Money renders through `portal/_money.html`: null → "—", 0 → "$0".
  - `PORTAL_VIEW` is logged after the page renders.

## Review Triage Log

Blind Hunter (one-shot route; edge-case and verification-gap layers not run):

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| 1 | "Value at activation" takes the newest snapshot of any trigger, not this activation's | medium | latent today: nothing creates `MANUAL` snapshots yet, but the model allows them and the header names a specific activation → patch (scope to the token + trigger) |
| 2 | Snapshot query unbounded, full rows | low | grows with items × activations → patch (folded into 1, `values_list`) |
| 3 | A real $0 renders "—", same as unknown | medium | `currency_display` returns "—" for 0 → patch (`_money.html`) |
| 4 | Sub-50-cent deltas render "+$0"; delta not coloured | low | valuations are whole dollars in practice; colour is cosmetic → reject |
| 5 | Value totals cover different item sets without a note | low | each total skips nulls separately → patch (count notes) |
| 6 | Items added after activation show "—" with no reason | low | the selector knows the item has no snapshot → patch (label) |
| 7 | No executor sign-out | medium | real, but a new feature outside 2.3 that needs a POST exception to the safe-methods rule → defer (`deferred-work.md`) |
| 8 | Rendered behaviours untested (0 / negative delta, charity fallback, deleted beneficiary, plural banner) | medium | → patch (tests added) |
| 9 | Loose assertions; query bound 3 vs promised 2 | low | → patch for the query count (exactly 2); other loose checks rejected as low-value |
| 10 | HEAD does full work; log written before render | low | → patch (log after render); the HEAD short-circuit is rejected (harmless, body stripped) |
