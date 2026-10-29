---
title: 'Epic 3 retrospective fixes'
type: 'bugfix'
created: '2026-10-29'
status: 'done'
baseline_commit: '79e7801bb6fd539b1e6f0fce7ddbd90078995c92'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-retro-2026-10-29.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Epic 3 retro (`epic-3-retro-2026-10-29.md`) found six defects at the seams between stories, F1–F5 and F8 (action items 1–6).
- Live beneficiary sessions that the executor cannot see or revoke.
- A first-activation race that creates two active codes.
- A bare Django 404 for beneficiaries.
- Owner copy that hides that ending a code ends beneficiary links.
- An expiry reset that shortens shared beneficiary sessions.
- Old-link revocations logged under the wrong token.

**Approach:** Six small fixes on one branch, each with a regression test. There are no migrations, no new routes, and no change to who may see what.

**Decisions (2026-10-29):** Keep all six in one spec and PR (as PR #30 did for Epic 2), even though it runs over the token guideline.

## Boundaries & Constraints

**Always:**
- **F1:**
  - An owner's beneficiary holding an active link issued under the current token is "link-holding".
  - The executor dashboard lists every designated or link-holding beneficiary.
  - Revoke and the issued page accept either kind.
  - Issuing a link still requires at least one designated item (the existing designated-only lookup).
  - A link-holding beneficiary with no designated items shows "0 items", their link status and Revoke, but no Issue control.
  - The dashboard's query count stays fixed.
- **F2:** `activate_estate_plan` locks the owner's user row (`select_for_update`) before it deactivates or creates any token, inside the existing atomic block.
- **F8:** every response from `_beneficiary_not_found` uses one estate-styled page:
  - status 404 and never-cache headers;
  - byte-identical for every dead link or session;
  - no flash messages and no estate, owner or beneficiary data;
  - heading "This link is no longer active", body "Please contact the estate's executor for a new link to view the items designated to you."
- **F3:** each of these owner-facing texts also says beneficiary links issued under the code stop working:
  - the executor form's name-change confirm and hint;
  - the Remove confirm;
  - the activate page's Revoke confirm and new-code warning/confirm;
  - the success messages after an executor update, executor removal and access revoke.

  The texts are unconditional, and existing tests are updated to the new strings.
- **F4:** the `executor_required` failure path resets the session expiry only when no beneficiary session keys are present, mirroring `beneficiary_required`.
- **F5:** each `LINK_REVOKED` row written by `_deactivate_active_links` carries that link's own `issued_by_token`.

**Never:**
- Ending beneficiary sessions when designations drop to zero (a 3.3 design decision: they see the empty state).
- Writing new `LINK_REVOKED` rows when a token deactivation ends links (deferred, retro item 8).
- Changing claim, session or isolation logic, snapshot code, or any other `deferred-work` item.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Emptied, link-holding | Ann claimed; her only item made charitable | Dashboard lists Ann, "0 items", "Opened …", Revoke, no Issue; revoke POST → 302 "Link revoked for Ann."; her next portal request → 404 | Issue POST for Ann → 404 |
| Issued page after designation removed | link issued, then last designation removed, then GET issued page with cookie | claim URL shown once | — |
| Never-eligible, no link | beneficiary with no items, no link | not listed; revoke/issue/issued → 404 | — |
| Old-token link | Ann holds only a link from an earlier activation; no designations | not listed; revoke → 404 | — |
| Double first activation | second `activate_estate_plan` while the first holds the owner lock | the second waits, then deactivates the first's token: one active token | — |
| Beneficiary 404 | any dead link, session, foreign item or no session | the F8 page, same bytes every case | a pending flash message is not rendered |
| Stale executor keys + live beneficiary | GET executor page | redirect to code entry; beneficiary keys and 30-day expiry kept; portal 200 | — |
| Beneficiary-only session | GET executor page | redirect; expiry unchanged | — |
| Reissue over old-token link | Ann active link under token A; owner reactivates (B); executor issues under B | that `LINK_REVOKED` row has token A | — |

</frozen-after-approval>

## Code Map

- `src/my_garage/api/selectors.py`:
  - `_designated_beneficiaries` (`:329`) and `get_executor_beneficiary` (`:343`) stay as they are; issuing uses them.
  - New `get_executor_link_beneficiary(owner, token, pk)` returns a beneficiary that is designated or link-holding, else None.
  - `get_executor_beneficiary_links(owner, token)` (`:361`) lists designated ∪ link-holding beneficiaries. Each row keeps `item_count` (possibly 0) and adds `can_issue = item_count > 0`.
  - The reverse FK name is `access_links` (`models.py:577`). Count designated items with `distinct=True`, so the link join does not inflate it.
- `src/my_garage/estate_views.py`:
  - `_eligible_beneficiary_or_404` (`:153`) stays for `portal_link_issue`.
  - Add a link-holding variant for `portal_link_revoke` (`:182`) and `_link_issued_response` (`:212`).
  - `_beneficiary_not_found` (`:239`) renders the new template with `status=404` and keeps `add_never_cache_headers`.
  - Guard `executor_required:104` with `BENEFICIARY_LINK_KEY not in request.session`.
  - Update the success messages at `:461`, `:493` and `:620`.
- `src/my_garage/api/services.py`:
  - In `activate_estate_plan:353`, call `get_user_model().objects.select_for_update().get(pk=user.pk)` as the first statement in the atomic block, as `issue_beneficiary_link:230` does.
  - In `_deactivate_active_links:208`, log with `token=link.issued_by_token`. The `token` parameter is then unused: drop it and update both callers.
- `src/my_garage/templates/my_garage/estate/portal/_base.html` -- wrap the `{% if messages %}` block in `{% block messages %}…{% endblock %}`. Executor pages render the same.
- `…/estate/beneficiary/not_found.html` (new) -- extends `beneficiary/_base.html`, empties `messages`, title "Link no longer active".
- `…/estate/portal/dashboard.html:64-95` -- hide the Issue form when `not row.can_issue`.
- `…/estate/executor.html:51,61,81` and `…/estate/activate.html:48,71,78` -- the F3 copy.
- Tests that assert the old copy:
  - `tests/functional/test_estate_story3_2.py:33,247,255`;
  - `test_estate_story2_2.py:226` (substring, still passes);
  - grep for "Not Found" (none found).
- No test exercises `select_for_update` today, and SQLite ignores it. Prove the F2 lock order by recording calls: patch the user manager's `select_for_update` and `EstateAccessToken.objects.create`, and assert the lock comes first.

## Tasks & Acceptance

**Execution:**
- [x] `src/my_garage/api/selectors.py` -- `get_executor_link_beneficiary`, and the widened link list with `can_issue`.
- [x] `src/my_garage/api/services.py` -- the owner lock in `activate_estate_plan`; the per-link token in `_deactivate_active_links`.
- [x] `src/my_garage/estate_views.py` -- the revoke/issued lookup, the 404 template, the expiry guard and the message copy.
- [x] templates -- the `messages` block, `beneficiary/not_found.html`, the dashboard Issue guard, the F3 copy.
- [x] `tests/unit/test_epic3_retro_fixes.py` (new):
  - link-holding selector cases (emptied, never-eligible, old-token)
  - link-list rows, `can_issue` and a fixed query count
  - F2 call order
  - F5 token per row
- [x] `tests/functional/test_epic3_retro_fixes.py` (new):
  - every matrix row through the client
  - the 404 body is identical across claim, portal, detail and photo cases, and a pending flash message is absent
  - the rendered Revoke form for an emptied beneficiary reaches revoke (retro item 4 rule)
- [x] Existing tests -- update the copy assertions.

**Acceptance Criteria:**
- Given the full suite, when the gate runs, then nothing that passed at baseline fails, apart from the updated copy assertions.
- Given an executor page in any session, when it renders, then its HTML matches the baseline apart from the F3 copy.

## Implementation Notes

- Implemented by an Opus subagent from this spec. The diff was read and the gate re-run by the parent session.
- "Link-holding" means a usable link: `is_active`, issued under the current token, and either claimed or not yet expired. An emptied beneficiary whose only link is unclaimed and expired is not listed (`test_expired_unclaimed_not_holding`); it would have had no control to show.
- `tests/functional/test_estate_story3_3.py::TestLinkCookie::test_404_path_deletes_cookie` also deactivates the link now. Matrix row 2 makes the issued page show the URL to an emptied link-holder, so the test has to remove Ann from scope another way. It still tests what it set out to: the 404 path deletes the cookie.
- `_deactivate_active_links` lost its `token` parameter. `revoke_beneficiary_link(beneficiary, token, request)` keeps its signature, so its `token` is now unused.
- The F2 lock and the `Exists` filters ran only on SQLite. The lock is proven by call order, not by real contention.
- Mutation-checked by the implementer: owner lock, per-link token, expiry guard, revoke and issued lookups, Issue guard, 404 template, empty messages block.
- Gate (pass 1): 477 unit, 686 functional and 35 FastAPI tests pass; no pending migrations; lint and format are clean.
- Review patches (sent back to the implementer):
  - E1/E2: `select_for_update(no_key=True)`.
  - B3: the lock test also asserts `in_atomic_block` and `no_key`.
  - V1: claimed-then-expired emptied tests, unit and functional.
  - E3: one `now`.
  - B2: the sequential-activation test renamed.
  - Mutation-checked: dropping `no_key` or the `claimed_at` branch fails the new tests.
- Gate after patches: 478 unit, 687 functional and 35 FastAPI tests pass; no pending migrations; lint and format are clean.

## Spec Change Log

## Review Triage Log

**Code review pass 1 (2026-10-29).** Layers: blind (B), edge-case (E), verification-gap (V).

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| E1/E2 | The owner `FOR UPDATE` inverts lock order with `verify_executor_code` (token lock, then a log insert that takes `KEY SHARE` on the user row): a Postgres deadlock, and owner-referencing inserts stall during activation | medium | Confirmed: `services.py:150` locks the token and then logs, while activation locks the user and then the tokens. **Patch:** `select_for_update(no_key=True)`; `NO KEY UPDATE` still serialises activations. |
| V1 | The `claimed_at` branch of the link-holding filter is never decisive in a test; dropping it brings F1 back once a claimed link passes its 7-day `expires_at` | medium | Pre-verified. **Patch:** a claimed-then-expired emptied test. |
| B3 | The lock-order test can't tell a lock taken inside the atomic block from one taken in a separate earlier one | low | **Patch:** assert `in_atomic_block` and `no_key` at lock time. |
| E3 | Two `now()` calls: a link expiring between them lists a row with no controls | low | Real microsecond race; the fix is a direct correction. **Patch:** one `now`. |
| B2 | `test_one_active_token` passes at baseline (sequential POSTs) | low | **Patch:** rename it; the unit call-order test is the F2 proof. |
| B4 | The executor's link-issued page doesn't say the link dies with the executor code | low | Outside F3's owner-only intent. **Defer** (`deferred-work.md`). |
| B10 | A row can list on an older live link while its status comes from a newer dead one | false | Issue and revoke deactivate every active link under the beneficiary lock, so the newest link under a token is the only live one. The hand-built unit case is not reachable. |
| B1 | Revoke and executor-change paths don't take the owner lock, so they can race a first activation | low | Needs one owner acting in two tabs at the same instant; the result is ordinary last-write-wins. Rejected. |
| B5 | The "designated" rule is now declared three times | low | Real duplication; retro item 7 (extract a shared queryset before Epic 4) covers it. Rejected here. |
| B6 | Per-link tokens lose which executor session did the revoke | low | The spec chose per-link attribution (F5); the row keeps time and IP. Rejected; the user is told. |
| B7 | A crafted revoke POST for an old-token-only beneficiary says "Link revoked" for an already-dead link | low | The dashboard shows no Revoke for that row, so it is reachable only by a crafted POST, and nothing gets access. Rejected. |
| B8 | `revoke_beneficiary_link` keeps an unused `token` parameter | low | Already noted. Dropping it touches every caller and test. Rejected. |
| E5/B9 | The F4 guard checks only the link key, not whether the beneficiary session is live | low | A dead beneficiary session keeps its cookie expiry until the next beneficiary URL clears it, and grants nothing. The keys are always written together. Rejected. |
| E6 | `executor_required` resets the expiry for a session with no executor keys at all | low | Behaviour from before this spec, not touched by F4. Rejected. |
| E4 | The emptied messages block leaves a pending flash to show on the next estate page | false | That page belongs to the same browser, and the message reaches its intended reader; nothing leaks onto the 404. |
| E7 | AC "executor HTML matches baseline apart from F3" vs the F1 dashboard change | false | F1's frozen rows require the dashboard change; the AC's wording is inexact. The fix would edit this spec. |
| B11 | No dashboard-view query count test; no test of an executor page rendering a pending message | low | The selector's count is tested and the template reads only loaded attributes. The un-overridden block renders the same markup. Rejected. |
| B12 | The single-row lookup runs the aggregate; `distinct=True` guards a join that doesn't exist | low | Negligible cost on a POST. The Code Map note would be a spec edit. Rejected. |

## Verification

**Commands:**
- `pixi run pytest tests/unit/ -x -q` -- expected: all pass
- `pixi run pytest tests/functional/ -x -q` -- expected: all pass
- `pixi run manage makemigrations --check --dry-run` -- expected: "No changes detected"
- `pixi run lint` -- expected: zero errors
- `pixi run -- ruff format --check .` -- expected: zero diffs
