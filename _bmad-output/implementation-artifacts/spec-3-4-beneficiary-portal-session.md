---
title: 'Story 3.4: Beneficiary Portal (Session)'
type: 'feature'
created: '2026-10-28'
status: 'done'
baseline_commit: '3ce49fb948bdd9fd03917cc0afef566ea33f8a56'
route: 'dispatch'
review_loop_iteration: 1
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-3-3-beneficiary-link-generation-executor.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 3.3 lets the executor issue a beneficiary link, but the claim URL is a stub that always returns 404. Beneficiaries still cannot see the items designated to them (FR20).

**Approach:**
- `claim_beneficiary_link` exchanges a valid link once for a 30-day sliding beneficiary session.
- A `beneficiary_required` decorator re-checks the link on every request.
- `/estate/beneficiary/` lists only the session beneficiary's designated items, filtered in the ORM.

**Decisions (2026-10-28):**
- Opening the link does not claim it. GET `/estate/beneficiary/claim/<token>/` shows a "View my designated items" page, and its POST button claims the link. Link previews and mail scanners therefore cannot use the link up. The epic AC's "opens" now reads "opens and confirms".
- The spec is kept whole even though it is over the token guideline.
- (Review, 2026-10-28) Reopening a claimed link in the browser whose live beneficiary session belongs to that exact link redirects to `/estate/beneficiary/`. Every other reuse is still the identical 404.

## Boundaries & Constraints

**Always:**
- A link is claimable only when it is active, unclaimed and unexpired, and its `issued_by_token` is usable. The hash is compared with `secrets.compare_digest`. Every other case returns the same bare 404: unknown, reused, revoked, expired, or a dead token. Failed claims log nothing.
- GET and HEAD on the claim URL change nothing: they render the confirm page for a claimable link and 404 otherwise. Only a CSRF-protected POST claims.
- The claim runs in `transaction.atomic()`. It locks the beneficiary row (as issue/revoke do), then re-reads the link, so two concurrent claims cannot both succeed.
- On claim: `cycle_key()` and `rotate_token()`, then write only `estate_beneficiary_link_id` / `estate_beneficiary_owner_id` and set a 30-day expiry. Executor keys and Django auth keys keep their values.
- `beneficiary_required` (`never_cache`) loads the session link, scoped by owner id. It requires `is_active`, `claimed_at` set, and a usable `issued_by_token`. The 7-day `expires_at` stops applying once a link is claimed. On failure it pops the two beneficiary keys and returns 404. It resets the expiry to browser-session only when no executor session keys remain. On success it slides the expiry by 30 days.
- Isolation: assignments with `beneficiary=link.beneficiary`, `is_charitable=False`, `item__owner=link.owner` and `item__collection_type__is_active=True`, using `select_related("item__collection_type")`. The query count is fixed whatever the item count.
- The portal is `require_safe`. `BENEFICIARY_VIEW` is logged after render on GET only, with `token=link.issued_by_token` and `beneficiary=`.
- Selectors for reads, services for writes. No new DRF endpoints.

**Never:**
- Item detail pages, item links or photos (Story 3.5).
- Changes to executor-session, link-issue or snapshot behaviour.
- A raw token in the session, the DB, logs or messages.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Open link | GET, claimable link | confirm page with a "View my designated items" POST button; `claimed_at` stays null, session unchanged, nothing logged | — |
| Preview fetch | GET or HEAD, then the beneficiary POSTs | claim still succeeds | — |
| Claim | POST, claimable link | `claimed_at` set, session keys written, `LINK_CLAIMED` logged (beneficiary name), 302 → `/estate/beneficiary/` | no CSRF token → 403 |
| Reuse | GET or POST after a claim, from another browser or with a dead / different-link session | 404 | no log |
| Reopen own link | GET or POST after a claim, in the browser whose live session is that link | 302 → `/estate/beneficiary/` | no log, no re-claim |
| Invalid / revoked / expired / token revoked or expired / older activation | — | 404, identical body | no log |
| Portal | session, 2 assigned items + 1 other beneficiary's + 1 unassigned + 1 charitable + 1 in a soft-deleted collection | greeting with name and relationship; owner's name; exactly the 2 items (name, collection, current value); `BENEFICIARY_VIEW` logged once | — |
| Empty | session, zero items | "No items have been designated for you yet." | — |
| Mid-session revoke | link revoked / reissued, owner revokes or reactivates, or executor name changed | beneficiary keys cleared, 404 | executor keys untouched |
| No session | GET `/estate/beneficiary/` | 404 | — |
| HEAD on portal | — | 200, nothing logged | — |
| Owner panel | — | "Link claimed · <name>" shown; "Portal views with this code" excludes beneficiary views | — |

</frozen-after-approval>

## Code Map

- `src/my_garage/models.py:612` -- add `("BENEFICIARY_VIEW", "Beneficiary viewed")` to `EstateAccessLog.EVENT_CHOICES`. Then `makemigrations` → `0024_*` (choices only, no schema change).
- `src/my_garage/api/selectors.py:269-278`:
  - `ESTATE_VIEW_EVENTS` gains `BENEFICIARY_VIEW`, so `test_event_groups_cover_every_event_type` stays green.
  - Add `EXECUTOR_VIEW_EVENTS = ("PORTAL_VIEW", "ITEM_VIEW")` and use it in the `get_executor_access_status` view count (`:313`). Beneficiary views must not inflate "Portal views with this code".
  - New `get_beneficiary_assignments(link) -> list[BeneficiaryAssignment]`: the isolation filter above, ordered by collection then item name.
  - New `get_claimable_beneficiary_link(raw_token, now) -> BeneficiaryAccessLink | None`: a read-only claimability check, used by the GET page and re-run inside the service lock.
- `src/my_garage/api/services.py`:
  - New `claim_beneficiary_link(raw_token, request=None) -> BeneficiaryAccessLink | None`, after `revoke_beneficiary_link` (`:249`).
  - Hash with `hash_executor_code`. Use `Beneficiary.objects.select_for_update()` as in `issue_beneficiary_link`.
  - Log `LINK_CLAIMED` with `token=link.issued_by_token, beneficiary=link.beneficiary`.
- `src/my_garage/estate_views.py`:
  - `BENEFICIARY_LINK_KEY` / `BENEFICIARY_OWNER_KEY` / `BENEFICIARY_SESSION_DAYS = 30` next to the executor constants (`:56`).
  - `beneficiary_required` follows `executor_required` (`:69-95`) and sets `request.beneficiary_link`. The failure path returns `HttpResponseNotFound`, not a redirect.
  - Replace the `beneficiary_claim` stub (`:213`): `never_cache` + `require_http_methods(["GET", "HEAD", "POST"])`. GET renders the confirm page; POST claims, then redirects or returns 404.
  - Add `beneficiary_portal`.
- `src/my_garage/estate_urls.py` -- add `beneficiary/` → `beneficiary_portal` (name `beneficiary_portal`).
- `src/my_garage/templates/my_garage/estate/beneficiary/_base.html` (new) -- extends `estate/portal/_base.html` (no account chrome), default title "Your Designated Items".
- `…/estate/beneficiary/claim.html` (new): a short welcome naming the owner, and a POST form with `{% csrf_token %}` and the "View my designated items" button. No beneficiary data appears before the claim.
- `…/estate/beneficiary/portal.html` (new):
  - Header "Hello, <name>" plus relationship, then "Items <owner full name or username> has designated for you".
  - A `<ul>` of items using `portal/_money.html`, and the empty state.

## Tasks & Acceptance

**Execution:**
- [x] `src/my_garage/models.py` + migration -- the `BENEFICIARY_VIEW` choice.
- [x] `src/my_garage/api/selectors.py` -- event groups, executor-only view count, `get_beneficiary_assignments`.
- [x] `src/my_garage/api/services.py` -- `claim_beneficiary_link`.
- [x] `src/my_garage/estate_views.py`, `estate_urls.py` -- decorator, claim, portal.
- [x] templates -- `beneficiary/_base.html`, `beneficiary/claim.html`, `beneficiary/portal.html`.
- [x] `tests/unit/test_beneficiary_claim_service.py` (new):
  - every claimable and unclaimable state, including the token states
  - single-use; hash compare
  - selector isolation across every excluded case
  - selector query count fixed at 1 or 2 items
  - executor view count excludes `BENEFICIARY_VIEW`
- [x] `tests/functional/test_estate_story3_4.py` (new):
  - every matrix row through the client
  - after claim, `_auth_user_id` and executor keys are unchanged in a shared session
  - the session expiry slides
  - mid-session revoke clears only the beneficiary keys
- [x] `_bmad-output/implementation-artifacts/sprint-status.yaml` -- `3-3` → done (PR #34 merged), `3-4` → in-progress.

**Acceptance Criteria:**
- Given a claimed session, when the executor revokes the link, then the beneficiary's next request returns 404 and the session no longer holds `estate_beneficiary_*` keys.
- Given a browser with an executor session, when a beneficiary link is claimed in it, then both sessions work and neither key set is altered by the other.

## Implementation Notes

- `get_claimable_beneficiary_link` takes the SHA-256 hash, not the raw token: `selectors.py` does not import `services.py`, where `hash_executor_code` lives. The view and the service hash first.
- Added `get_beneficiary_session_link(link_id, owner_id)` to `selectors.py` so the decorator does no ORM work itself.
- Dead links and sessions render Django's `page_not_found` with never-cache headers (`_beneficiary_not_found`). A raised `Http404` would skip the `never_cache` headers.
- The claim re-checks under the beneficiary-row lock and then runs a conditional `UPDATE … WHERE claimed_at IS NULL`, so even a missed lock cannot double-claim.
- `tests/functional/test_estate_story3_3.py`: the stub test (claim URL → 404) became `TestClaimUrl`, which checks that the URL shown once opens the claim page (200). This is epic-2 retro item 4.
- Gate (pass 1): 448 unit and 643 functional tests pass; no pending migrations; lint and format are clean.
- Review patches:
  - E3 reopen redirect, B9c/E1 single lookup with a None-safe lock, B6 copy.
  - Tests for V1, V2, B2, E3 and E1.
  - Mutation-checked: dropping `claimed_at__isnull` fails `test_stale_read_cannot_double_claim`; dropping the expiry reset fails `test_keys_cleared_and_404`.
- Gate after patches: 450 unit and 646 functional tests pass; no pending migrations; lint and format are clean.

## Spec Change Log

- **Pass 1 (2026-10-28), E3 intent_gap:**
  - **Trigger:** a beneficiary reopening their own claimed link got 404.
  - **Amended (human-approved):** a frozen decision and the matrix rows "Reuse" / "Reopen own link".
  - **Known-bad state avoided:** a live beneficiary believing their access was revoked.
  - **Approach:** by the human's choice, the code was patched on top rather than reverted.
  - **KEEP:** the claim/session/isolation code and the tests from pass 1.

## Review Triage Log

**Code review pass 1 (2026-10-28).** Layers: blind (B), edge-case (E), verification-gap (V).

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| E3 | A browser with a live session that reopens its own claim URL gets 404 | medium | Reopening the link from email or messages is everyday behaviour, and the beneficiary then believes access is gone. The frozen matrix row "Reuse → 404" does not separate this case. **intent_gap** → human. |
| V1 | No test checks that `_session_expiry` is removed after a beneficiary-only session dies | low | Pre-verified. **Patch:** assert it as `test_estate_story2_2.py:134` does. |
| V2/B9a | The conditional `UPDATE … claimed_at IS NULL` branch is never exercised | low | Pre-verified. **Patch:** a stale-read unit test. |
| B2 | The owner-panel test asserts that "Portal views with this code" is absent, which passes trivially | low | The line is inside `{% if access.view_count %}`. **Patch:** log one `PORTAL_VIEW` and assert ": 1". |
| B6 | After a claim, nothing tells the beneficiary what to do if they lose access | low | **Patch:** one line on the claim page. |
| B9c | The claim runs the claimability lookup three times | low | **Patch:** lock using the pre-check's `beneficiary_id`; drop the candidate query. |
| E1 | A beneficiary deleted mid-claim → `DoesNotExist` → 500 | low | **Patch:** use `filter().first()` and return None (folded into B9c). |
| V-o1/B3a | `set_expiry(None)` falls back to the 14-day default, not "browser-session only" | low | Confirmed: no `SESSION_EXPIRE_AT_BROWSER_CLOSE`. The behaviour matches `executor_required:102`. The dead session holds no beneficiary keys, so nothing leaks. Rejected; the user is told the spec wording is inexact. |
| B3b/E5 | A claim in a browser logged in as the owner makes that login a 30-day sliding session | low | Real. Executor sessions already do the same. The fix needs an auth-aware branch. Rejected; the user is told. |
| B4 | A second claim in the same browser silently replaces the first beneficiary's session | low | Real, and recoverable by reissue. A warning needs new UI branching. Rejected; the user is told. |
| B5 | No "end this session" action on a shared device | low | A feature addition (route + view + template). Rejected; the user is told. |
| V-o2/E4 | `executor_required` resets the expiry even when beneficiary keys are live | low | The expiry drops to 14 days until the next beneficiary visit slides it back. Fixing it changes executor code (spec Never). Rejected. |
| B9b/E2 | The claim does not lock the token, so it can log `LINK_CLAIMED` under a token revoked a moment earlier | low | Microsecond race; `beneficiary_required` 404s on the first request. Rejected. |
| E6 | Pending executor flash messages could render on beneficiary pages in a shared browser | low | Messages are consumed by the executor's own redirect; it needs a shared browser and an unfollowed redirect. Rejected. |
| E7 | An emptied beneficiary's link cannot be revoked from the executor UI | low | carried: 3.3 triage E3, unchanged. Rejected. |
| B1 | The portal shows live value; the executor shows the snapshot | false | The executor dashboard also shows "Current value" (`dashboard.html:40,125`). |
| B7/E8 | `BENEFICIARY_VIEW` is write-only | false | The epic requires only the entry. Story 4.3 (audit-log PDF) consumes the log. |
| B8 | `compare_digest` after a DB equality match is redundant; the hash is not unique | false | It mirrors `verify_executor_code` and the AC requires it. Uniqueness: 3.3 triage B8. |
| B10 | A POST to the portal without a session returns 405, not 404 | false | Same order as the executor views. The matrix's no-session row is GET; a 405 reveals nothing about a token. |
| B11 | Spec / sprint-status / Code Map disagree | false | Sprint status moves at presentation. The other fixes edit this spec, which triage rules out. |

## Design Notes

- **Why the claim lives behind the issuing token:** any link not under the owner's current token has an unusable token (only one active token per owner). So "token usable" also covers links from an earlier activation; no extra check is needed (3.3 triage E2).
- **A beneficiary with no designations left** after the claim sees the empty state, not a 404 (3.3 triage E3).
- **Portal content:** name, collection type and current value only. Detail, photos, the snapshot and the conditional note come in 3.5.

## Verification

**Commands:**
- `pixi run pytest tests/unit/ -x -q` -- expected: all pass
- `pixi run pytest tests/functional/ -x -q` -- expected: all pass
- `pixi run manage makemigrations --check --dry-run` -- expected: "No changes detected"
- `pixi run lint` -- expected: zero errors
- `pixi run -- ruff format --check .` -- expected: zero diffs
