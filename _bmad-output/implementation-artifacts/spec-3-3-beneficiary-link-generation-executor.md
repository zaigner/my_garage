---
title: 'Story 3.3: Beneficiary Link Generation (Executor)'
type: 'feature'
created: '2026-10-28'
status: 'done'
route: 'dispatch'
baseline_commit: '3ed1d4c456ea14efc5f4ee8190b3c6e0f67f63cb'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-3-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-3-2-estate-scope-executor-replacement.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The executor can see the estate but has no way to give a beneficiary access to their own items (FR19). Story 3.4 claims links and 3.5 shows item detail. Both need a link to exist first.

**Approach:**
- New `BeneficiaryAccessLink` model.
- The executor dashboard gets a "Beneficiary links" section listing each designated beneficiary with a link status and Issue / Revoke actions.
- Issuing shows the claim URL once, through the signed-cookie pattern used for the activation code.
- Link events appear in the owner's activity panel.

**Decisions (2026-10-28):**
- An unopened link past its 7 days shows "Expired — not opened".
- Links from an earlier activation are ignored, so the beneficiary shows "No link".
- Link events store the beneficiary's name in `EstateAccessLog.beneficiary_name`.
- The spec is kept whole even though it is over the token guideline.

## Boundaries & Constraints

**Always:**
- Raw token from `secrets.token_urlsafe(32)`. Only its SHA-256 hash is stored. It never goes in the session, the database, logs or messages.
- A beneficiary has at most one active link. Issuing deactivates the previous one in the same transaction and logs `LINK_REVOKED` for it.
- Issue and revoke are POST only, CSRF-protected and behind `executor_required`. They change no estate or asset data.
- Only the owner's beneficiaries with at least one designated item are eligible. A designated item is a non-charitable assignment to that beneficiary, in an active collection. Any other id returns 404.
- Status comes from the beneficiary's newest link issued under the executor's current token. Links issued under an earlier activation are ignored, because they died with that token.
- Selectors for reads, services for writes. No new DRF endpoints.

**Never:**
- Claim, beneficiary session or beneficiary pages (Stories 3.4–3.5). The claim route is added only as a stub that always returns 404, so `reverse()` works.
- Owner-side link management.
- Changing the executor-token or snapshot logic.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| List | beneficiaries A (2 items), B (charitable only), C (only items in a soft-deleted collection) | only A listed, with item count | — |
| Status "No link" | no link under the current token | "No link" + Issue link | — |
| Status issued | active, unclaimed, `expires_at` in future | "Issued — not yet opened (expires <date>)" + Issue new link + Revoke | — |
| Status opened | active, `claimed_at` set | "Opened <date>" + Issue new link + Revoke | — |
| Status revoked | newest link inactive | "Revoked" + Issue link | — |
| Status expired | active, unclaimed, `expires_at` past | "Expired — not opened" + Issue link | — |
| Issue | POST `…/beneficiaries/<id>/link/` | link created (`expires_at` = +7 days, `issued_by_token` = session token); `LINK_ISSUED` logged; 302 to the one-shot page | ineligible / other owner's id → 404 |
| Reissue | active link exists | old link `is_active=False` + `LINK_REVOKED`; new link active | — |
| One-shot page | first GET after issue | shows `<PUBLIC_BASE_URL or request host>/estate/beneficiary/claim/<raw>/` and "This link cannot be recovered. Save it now before closing." | — |
| One-shot replay | second GET, a missing or tampered cookie, or a hash that is no longer the beneficiary's active link | redirect to the dashboard with "A link can only be shown once. Issue a new link to get one." | cookie deleted on every response |
| Revoke | POST `…/link/revoke/`, active link | `is_active=False`; `LINK_REVOKED` logged; message "Link revoked for <name>." | no active link → "No active link." |
| GET on issue/revoke | GET | 405 | — |
| Owner activity panel | link events | listed with the beneficiary's name | — |

</frozen-after-approval>

## Code Map

- `src/my_garage/models.py:548-616`:
  - `EstateAccessToken` is the pattern for the new `BeneficiaryAccessLink` (fields as in the epic context). Add the related name `access_links` and `Meta.ordering = ["-issued_at", "-pk"]`.
  - `EstateAccessLog.EVENT_CHOICES` gains `LINK_ISSUED`, `LINK_REVOKED` and `LINK_CLAIMED` (written in 3.4), plus `beneficiary_name = CharField(200, blank=True)`, set like `item_name`, so the panel survives beneficiary deletion.
- `src/my_garage/migrations/0023_*`: generated with `makemigrations`. Schema only.
- `src/my_garage/api/services.py`:
  - `log_estate_access` (`:112`) gains `beneficiary=None` and fills `beneficiary_name`.
  - New `issue_beneficiary_link(beneficiary, token, request=None) -> str` and `revoke_beneficiary_link(beneficiary, token, request=None) -> bool`. Both run in `transaction.atomic()` with `select_for_update` on the beneficiary's active links, mirroring `_deactivate_active_tokens` (`:169`).
  - Hash with `hash_executor_code` (`:126`). It is plain SHA-256 hex.
- `src/my_garage/api/selectors.py`:
  - `ESTATE_SECURITY_EVENTS` (`:267`) gains the three link events. `tests/unit/test_estate_access_service.py:193` enforces full coverage.
  - New `get_executor_beneficiary(owner, beneficiary_id)`: the eligible beneficiary or None.
  - New `get_executor_beneficiary_links(owner, token) -> list[dict]`: beneficiary, item_count, link, status. Two queries: annotated beneficiaries, then the token's links for them, newest first.
- `src/my_garage/estate_views.py`:
  - `portal_dashboard` (`:113`) adds `beneficiary_links` to the context.
  - New `portal_link_issue` and `portal_link_revoke` (`require_POST` + `executor_required`) and `portal_link_issued` (`require_safe` + `executor_required`). The one-shot logic copies `estate_activate` / `_activate_success_response` (`:337-420`): own cookie name and salt, 600 s max age, `path` = the issued page URL, `samesite="Strict"`.
  - New stub `beneficiary_claim` (`never_cache`, always `Http404`).
- `src/my_garage/estate_urls.py`: `portal/beneficiaries/<int:pk>/link/`, `…/link/revoke/`, `…/link/issued/`, `beneficiary/claim/<str:token>/`.
- `src/my_garage/templates/my_garage/estate/portal/dashboard.html`: a "Beneficiary links" section after the summary, as a `<ul>` that works at every width. Revoke and reissue use `onsubmit="return confirm(…)"` like `activate.html:71`.
- `…/estate/portal/link_issued.html` (new): based on `activate_success.html`, extending `portal/_base.html`.
- `…/estate/activate.html:63`: append ` · {{ e.beneficiary_name }}` when set.

## Tasks & Acceptance

**Execution:**
- [x] `src/my_garage/models.py` + migration -- model, event choices, `beneficiary_name`.
- [x] `src/my_garage/api/services.py` -- `log_estate_access(beneficiary=)`, issue and revoke services.
- [x] `src/my_garage/api/selectors.py` -- event group, the two selectors.
- [x] `src/my_garage/estate_views.py`, `estate_urls.py` -- the four views and routes.
- [ ] templates -- the dashboard section, `link_issued.html`, the activity-panel name.
- [x] `tests/unit/test_beneficiary_link_service.py` (new) -- issue/reissue/revoke invariants, hash-only storage, eligibility, every status row, and the selector at 2 queries.
- [x] `tests/functional/test_estate_story3_3.py` (new) -- every matrix row through the client, including CSRF (`enforce_csrf_checks=True`), 405 on GET, cross-owner 404, and a stub claim URL that returns 404.

**Acceptance Criteria:**
- Given an executor session, when they issue a link for a beneficiary, then the DB holds only the hash, the raw URL appears exactly once, and the owner's activity panel shows "Link issued · <name>".
- Given a link issued under token T1, when the owner reactivates (T2) and the executor logs in again, then that beneficiary shows "No link".

## Implementation Notes

- Gate after review patches: 423 unit and 616 functional tests pass; no pending migrations; lint and format are clean. Nothing was deferred.

## Spec Change Log

## Review Triage Log

**Code review pass 1 (2026-10-28).** Layers: blind (B), edge-case (E), verification-gap (V).

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| E1/B1 | Two concurrent issue POSTs can leave two active links | medium | On a first issue, `select_for_update` on zero active rows locks nothing, so on PostgreSQL a double click creates two links. **Patch:** lock the `Beneficiary` row first in both services. |
| E6/B5/V-o2 | The one-shot cookie is not deleted when the page returns 404 | low | `_eligible_beneficiary_or_404` raises before `delete_cookie`. That breaks the matrix's "cookie deleted on every response". **Patch:** catch `Http404` in `portal_link_issued` and delete the cookie on that response too. |
| V-o1 | The link cookie is persistent (`max_age=600`) | low | The activation pattern omits `max_age` on purpose (comment at `estate_activate`), so the raw token is written to disk. `get_signed_cookie` already enforces the 600 s. **Patch:** drop `max_age` on set. |
| E5/B4 | A HEAD request to the one-shot page uses up the cookie | low | `require_safe` lets HEAD run the full view and delete the cookie. **Patch:** `require_GET`. |
| E7 | The activity panel says "Beneficiary link issued", but the AC says "Link issued · <name>" | low | Direct deviation from the AC; the fix is trivial. **Patch:** the labels become "Link issued" / "Link revoked" / "Link claimed" (in the uncommitted 0023). |
| V1 | Cookie attributes and deletion are not asserted; the test client ignores the path | low | Pre-verified (V). **Patch:** tests that mirror `test_estate_story2_1.py:198-233`. |
| V2/B10a | Opened-state actions untested; revoked/expired don't assert that the Revoke form is absent | low | Pre-verified (V). **Patch:** assert the revoke form action for each status. |
| B10b | Revoke and the issued page are not tested without a session | low | **Patch:** extend `test_requires_executor_session`. |
| B10c | The issued page doesn't say the link stops working on reissue or revoke | low | The executor needs this to understand reissue. **Patch:** one sentence. |
| E2/B2/V-o3 | T1 links stay `is_active` after reactivation; 3.4 might honour them | false | Only one owner token can be active, so any link not under the current token has an unusable token. Story 3.4's AC requires "its issuing executor token is usable" for a claim. Nothing in 3.3 reads these links. |
| E3/B3 | Revoke returns 404 once a beneficiary loses all designations, leaving a live link | low | Real, but it needs a reassignment after issue. 3.4's ORM isolation then shows that beneficiary an empty portal with no items. The fix needs new listing and branching. Rejected. |
| E4 | Link events can crowd TOKEN/CODE rows out of the 10-row panel | low | The epic puts link events in the security group by design. A separate cap means a new query and group. Rejected. |
| B6 | Reissue after expiry or reactivation logs LINK_REVOKED for an already-dead link | low | The row was still `is_active`, so a deactivation did happen. Distinguishing the cases needs a new branch or event. Rejected. |
| B7 | The raw token in the claim URL path reaches access logs | false | The epic AC fixes the URL format `/estate/beneficiary/claim/<raw_token>/`, and 3.4 redirects to a token-free URL after the single-use claim. The CF Access bypass is already a recorded release gate. |
| B8 | `link_token_hash` should be unique | false | A 256-bit random token; no collision is reachable. |
| B9 | Services don't check that the token's owner matches the beneficiary's owner | false | The only callers (the views) pass `request.estate_token` with a beneficiary looked up under `request.estate_owner`; no mismatched caller exists. |
| B10d | Tests use `objects.create`, not factory-boy | false | They match every existing estate test file; not a defect in this diff. |

## Design Notes

- **Status order:** `is_active=False` → revoked; `claimed_at` → opened; `expires_at <= now` → expired; else → issued.
- **The one-shot check** compares `hash_executor_code(raw)` with the beneficiary's active link issued under the session token, using `secrets.compare_digest`.
- **No-JS fallback:** confirms are JS-only, the same accepted risk as Story 3.2 (V1 in `deferred-work.md`).

## Verification

**Commands:**
- `pixi run pytest tests/unit/ -x -q` -- expected: all pass
- `pixi run pytest tests/functional/ -x -q` -- expected: all pass
- `pixi run manage makemigrations --check --dry-run` -- expected: "No changes detected"
- `pixi run lint` -- expected: zero errors
- `pixi run -- ruff format --check .` -- expected: zero diffs
