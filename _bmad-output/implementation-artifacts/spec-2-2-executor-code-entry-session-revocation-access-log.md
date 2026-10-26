---
title: 'Story 2.2: Executor Code Entry, Session, Revocation & Access Log'
type: 'feature'
created: '2026-10-25'
status: 'done'
baseline_commit: 'ffe14f372b7c19d5315aa4046eaf3b92e67dd8e5'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 2.1 issues an executor code, but nothing accepts it. The owner can't see whether the code has been used or revoke it, codes never expire, and no access event is recorded.

**Approach:** Add a public `/estate/portal/` code-entry page that sets an executor session. An `executor_required` decorator re-checks the token on every request. Add an append-only `EstateAccessLog` (timestamp, IP, action type), an owner-side access status panel with Revoke on `/estate/activate/`, a 72-hour expiry for unused codes, and a 30-day sliding expiry for executor sessions.

## Boundaries & Constraints

**Always:**
- Hash codes with SHA-256 and compare with `secrets.compare_digest`. Every bad code gets one generic message: "Invalid access code. Please contact the estate owner." The submit button reads "Access Estate".
- Deactivate tokens, never delete them. Never update or delete `EstateAccessLog` rows.
- Write only the session keys `estate_executor_owner_id` / `estate_executor_token_id`, and never touch Django auth keys. On successful code entry, call `request.session.cycle_key()` and `django.middleware.csrf.rotate_token(request)`.
- Portal views use `executor_required`, not `@login_required`. Owner views filter by `request.user`.
- Token issue, revoke, and verify run inside `transaction.atomic()` with `select_for_update()` on the owner's tokens. `use_count` is incremented with `F()`.
- Every log entry records timestamp, IP, and action type (decided 2026-10-25, following the PRD).
  - IP source: `CF-Connecting-IP`, else the first `X-Forwarded-For` hop, else `REMOTE_ADDR`. The first value that parses with `ipaddress.ip_address()` wins; if none parse, or there's no request, store null.
  - The IP is informational only and never used for an access decision. Known limitation: LAN requests through `192.168.50.200` / `my-garage.local` skip Cloudflare and can spoof these headers.
- Portal templates load assets only from CDNs, never `/static/` or `/media/`, because Cloudflare Access bypasses only `/estate/portal/*`.

**Never:** Building the portfolio view (Story 2.3), item detail (2.4), PDF, or beneficiary links. Logging or persisting raw codes. Rate limiting (a 43-character random code makes guessing infeasible). DRF endpoints. Changes outside the estate feature.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Valid code | active, unexpired token | key cycled, CSRF rotated, both session keys set, `use_count`+1, `last_used_at` set, `expires_at` cleared, `CODE_ACCEPTED`, 302 → `/estate/portal/dashboard/` | — |
| Reused code | active token, `use_count>0`, `expires_at` null | accepted again (new device or after session expiry) | — |
| Unknown code | hash matches nothing | 200 with generic error, no session keys, nothing logged | generic message |
| Revoked / expired code | matches a token with `is_active=False`, or `expires_at` ≤ now | generic error, no session keys, `CODE_REJECTED` against that owner | generic message |
| Blank code | empty POST | form error, nothing logged | field error |
| Session, token later revoked | executor keys present, token unusable | keys popped, `set_expiry(None)`, 302 → `/estate/portal/`, generic error via `messages` | — |
| Session, token deleted | owner deleted → token cascade-deleted | same as above | no 500 |
| No session | GET `/estate/portal/dashboard/` | 302 → `/estate/portal/` | — |
| Non-safe method on a portal view | POST to `/estate/portal/dashboard/` | 405 (`require_safe` outermost, before the session check; in production CSRF may return 403 first) | — |
| Malformed IP header | `CF-Connecting-IP: x` | logged with the next valid source or null | no 500 |
| Owner revokes | POST `/estate/activate/revoke/` | active token `is_active=False`, `TOKEN_REVOKED`, toast "Executor access revoked." | no active token → info toast "No active access code."; GET → redirect to activate |
| Owner removes executor | POST `/estate/executor/remove/` | revoke runs unconditionally (`TOKEN_REVOKED` if a token was active), then the executor is deleted if present; "Executor removed." message kept | — |
| Activation / reissue | Story 2.1 POST | under lock: capture the active token IDs, deactivate by `pk__in`, log `TOKEN_REVOKED` for each, create the new token with `expires_at`=now+72h, log `TOKEN_ISSUED` | — |
| Backfill migration | active, `use_count=0`, `expires_at` null | `expires_at = F("issued_at") + 72h`; other tokens untouched | reverse = no-op |

</frozen-after-approval>

## Code Map

- `src/my_garage/models.py:524-565` -- `EstateChangeLog` (style template) and `EstateAccessToken`.
  - Add `is_usable(now)` to the token: `is_active and (expires_at is None or expires_at > now)`.
  - Add `db_index=True` on `token_hash`.
  - Add `EstateAccessLog` after the token model.
- `src/my_garage/migrations/0019_*` -- latest. Add:
  - `0020`, auto-generated: the new model plus the `token_hash` index.
  - `0021`, hand-written: module-level `backfill_expires_at(apps, schema_editor)` using `apps.get_model`, run through `RunPython(..., RunPython.noop)`.
- `src/my_garage/api/services.py:83` -- `activate_estate_plan(user, request=None)`: apply the reissue row of the matrix. Add beside it:
  - `log_estate_access(owner, event, token=None, item=None, request=None)`, which sets `item_name=item.name` when given.
  - `client_ip(request)`.
  - `verify_executor_code(raw_code, request=None) -> EstateAccessToken | None`.
  - `revoke_executor_access(user, request=None) -> bool`.

  Use `django.utils.timezone.now`. `request` is always an optional keyword, so existing callers and tests keep working.
- `src/my_garage/api/selectors.py:202` -- add `get_executor_access_status(user)` → `{token, state, recent_events}`.
  - `token`: the active token, else the latest by `(-issued_at, -pk)`, else None.
  - `state`, checked in order: `none` (no token), `revoked` (`not is_active`), `expired` (`expires_at <= now`), `unused` (`use_count == 0`), `in_use`.
  - `recent_events`: `list()` of the last 10 log rows, ordered `-timestamp, -pk`.
- `src/my_garage/forms.py:156` -- after `EstateActivateForm`, add `ExecutorCodeForm` (`PasswordInput`, `max_length=64`, label "Access code").
- `src/my_garage/estate_views.py` -- existing views call the ORM directly; keep them as they are, and route all new reads and writes through the selectors and services.
  - Add `executor_required`. It sets `request.estate_owner` / `request.estate_token` and calls `set_expiry(timedelta(days=30))`.
  - Add `portal_code_entry` (GET + POST), `portal_dashboard` (`require_safe` then `executor_required`; a stub until 2.3), and `estate_revoke_access` (login, POST).
  - Change `estate_activate` (pass the status; pass `request` to the service) and `executor_remove:106`.
- `src/my_garage/estate_urls.py` -- add `portal/` (`portal_code_entry`), `portal/dashboard/` (`portal_dashboard`), `activate/revoke/` (`revoke_access`).
- `src/my_garage/templates/my_garage/estate/activate.html` -- edits:
  - Change "one-time code" at line 14 to "an access code".
  - Add the status panel. Revoke shows whenever `token.is_active`, including an expired-but-active token.
  - The revoked state shows "Revoked" with no date.
  - Add a recent-events list (event, timestamp, IP, item name).
  - The button reads "Issue new code" when the state is expired or revoked.
- `src/my_garage/templates/my_garage/estate/activate_success.html:31-51` -- add "Expires <date> if unused" and the absolute portal URL via `request.build_absolute_uri`.
- `src/my_garage/templates/my_garage/estate/portal/` -- new templates:
  - `_base.html`: standalone; copies the CDN Tailwind config and fonts from `my_garage/base.html`, with no nav, a viewport meta, and a `messages` block.
  - `code_entry.html`.
  - `dashboard.html`: the stub.
- `tests/functional/test_estate_story2_1.py` -- fixture pattern to copy (plain `objects.create`, `force_login`). The estate suites don't use factory-boy; stay consistent. Keep the "Executor removed" assertion at `test_estate_story1_2.py:187` passing.

## Tasks & Acceptance

**Execution:**
- [x] `src/my_garage/models.py` + migrations `0020`, `0021`: add `EstateAccessLog` (fields below), `is_usable`, the `token_hash` index, and the backfill. This is the storage everything else needs. Fields:
  - `owner`: FK CASCADE
  - `token`: FK SET_NULL
  - `event`: choices TOKEN_ISSUED / TOKEN_REVOKED / CODE_ACCEPTED / CODE_REJECTED / PORTAL_VIEW / ITEM_VIEW
  - `item`: FK SET_NULL
  - `item_name`
  - `ip_address`: GenericIPAddressField, null/blank
  - `timestamp`: auto
  - Meta: ordering `["-timestamp", "-pk"]`, index `(owner, -timestamp)`
- [x] `src/my_garage/api/services.py`: the service changes above. All writes go through services.
- [x] `src/my_garage/api/selectors.py`: `get_executor_access_status`.
- [x] `src/my_garage/forms.py`: `ExecutorCodeForm`.
- [x] `src/my_garage/estate_views.py` + `estate_urls.py`: the decorator and the views.
- [x] Templates: the portal base, code entry (labelled input, `role="alert"` error, AA contrast, works on mobile), the dashboard stub (the owner's full name or username, plus "Portfolio view coming soon"), and the activate and success pages.
- [x] `tests/unit/test_estate_access_service.py`: services, `client_ip` (malformed, XFF, missing), `is_usable`, every selector state, and the backfill via `importlib.import_module("my_garage.migrations.0021_…")` with `django.apps.apps`.
- [x] `tests/functional/test_estate_story2_2.py`: every matrix row, the activate panel, the success page, revoke, executor removal, and the session-key cycling.

**Acceptance Criteria:**
- Given an anonymous visitor, when they GET `/estate/portal/`, then a labelled code form renders without a login redirect.
- Given an active token, when the owner opens `/estate/activate/`, then they see the issued date, "Not yet used — expires <date>" or "In use — last used <date>", the use count, a Revoke button, and the last 10 log events.
- Given the owner's latest token is unused and expired, when `/estate/activate/` renders, then the status reads "Expired — not used", Revoke is still offered, and the button reads "Issue new code".
- Given a fresh activation, when the success page renders, then it shows the code, the absolute portal URL, and the 72-hour expiry.
- Given the owner updates the executor's details, when saved, then the token stays active.
- Given a revoked executor session, when the executor requests any portal page, then access ends on that request.

## Implementation Notes

- `activate_estate_plan` builds the snapshot list first, then runs the token swap, logs, and `bulk_create` in one `transaction.atomic()`, so the old code is never revoked without a new code and snapshot.
- `executor_required` shows the generic error only when an executor session key was present. A first-time visitor bounced from the dashboard sees no error.
- Portal views are `never_cache`, via `@never_cache` on code entry and the inner view inside `executor_required`, so Stories 2.3/2.4 inherit it.
- New setting `PUBLIC_BASE_URL` (env; `k8s/configmap.yaml` sets `https://my-garage.zachelorpad.com`; listed in `.env.example`). The success page builds the portal link from it and falls back to the request host when it's empty.
- Reissuing while a code is active shows a warning and a confirm. Removing the executor says that the code is revoked.
- Deploy note: migration 0021 expires any never-used code issued more than 72h before deploy (intended). The owner reissues it.

## Spec Change Log

## Review Triage Log

| # | Finding | Verdict | Evidence / action |
|---|---|---|---|
| 1 | A malformed IP header raises a DataError on Postgres `inet` | high | validate with `ipaddress`; matrix row added |
| 2 | IP headers spoofable on LAN; `REMOTE_ADDR` is always Traefik | medium | `k8s/django/ingress.yaml:5-8,19-23`; XFF fallback added, limitation recorded |
| 3 | Reissue and use-count race | medium | `atomic` + `select_for_update`, `pk__in`, `F()` |
| 4 | Status selector states undefined | medium | rule defined; Revoke shown for expired; log tie-break |
| 5 | Backfill untestable (migrations disabled in tests) | medium | module-level function + `importlib` test |
| 6 | Owner never told about the 72h expiry; "one-time" copy | medium | success page + activate copy added to the map |
| 7 | `_session_expiry` lingers; CSRF not rotated | medium | `set_expiry(None)` on pop; `rotate_token` |
| 8 | Decorator order; 405 vs CSRF 403; HEAD | low | `require_safe` outermost |
| 9 | Exact copy; messages in the standalone base; static behind Access | low | copied into the frozen block |
| 10 | `item_name`; epic's `log_estate_access` signature | low | `item_name` set; epic synced |
| 11 | `executor_remove` ambiguity; no-op revoke toast | low | unconditional revoke; messages defined |
| 12 | `token_hash` unindexed | low | `db_index=True` in 0020 |

**Code review pass 1 (2026-10-25)** — layers: blind (B), edge-case (E), verification-gap (V).

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| B1/E7 | Reissue silently revokes a live code and session | medium | Activate submit while active runs `_deactivate_active_tokens`, with no warning → patch (warning + confirm) |
| B2 | Executor-remove confirm and toast don't mention revocation | low | `executor.html:70`; `executor_remove` revokes unconditionally → patch |
| B3 | Success-page portal URL is built from the request host (LAN host when owner is home) | medium | `build_absolute_uri`; ALLOWED_HOSTS includes `my-garage.local` / `192.168.50.200`; no public base-URL setting existed → human chose option 1 (2026-10-25): `PUBLIC_BASE_URL` setting + configmap `https://my-garage.zachelorpad.com`, request-host fallback → patch |
| B4 | No cache-control on portal pages | medium | no `never_cache` anywhere in portal views → patch |
| B5/E6 | Portal base renders every message as a red alert | low | `_base.html` ignores `level_tag`; shared-browser owner toasts would show → patch |
| B6 | `compare_digest` after a DB equality lookup is redundant | low | true, but no harmful outcome; the fix is editing the spec's rule → reject |
| B7/E1 | `.get()` re-read raises DoesNotExist → 500 | low | `services.py` re-read by pk after the lock; owner deletion mid-request → patch |
| B8/E5 | Backfill expires codes issued >72h before deploy | low | conforms to the frozen matrix row and the accepted epic note → reject (deploy note to the user) |
| B9 | No DB-level one-active-token constraint; lock is a no-op on SQLite | low | Postgres in prod honours `select_for_update`; concurrent same-owner activation unlikely; a constraint guards an undemonstrated state → reject |
| B10 | Untested rules: CSRF rotate, owner stays logged in, `set_expiry(None)`, HEAD, static scan | medium | covered with V1–V3 → patch (tests) |
| B11 | Event types are bare strings; typos stored silently | low | no defect today; TextChoices refactor is more than a direct correction → reject (consider in 2.3) |
| B12 | Log docstring says "never updated or deleted" despite SET_NULL/CASCADE | low | `models.py` docstring → patch (reword) |
| B13 | Form widget attrs duplicated by hand-written input | low | `code_entry.html` hand-writes the input; divergence unlikely in practice → reject |
| B14/E3 | Success page reads the current token's expiry, which could belong to a reissue from another tab | low | requires a reissue between the redirect and the GET; fix adds plumbing → reject |
| E2 | Executor `set_expiry` alters an owner session in a shared browser | false | accepted explicitly in Design Notes; `set_expiry(None)` restores the default the owner had |
| E4 | `unused` state renders a blank expiry date when `expires_at` is None | low | `activate.html` unused branch → patch (conditional render) |
| V1 | Sliding-expiry test passes without the decorator's refresh | medium | pre-verified → patch (test) |
| V2 | Guard `set_expiry(None)` not asserted | medium | pre-verified → patch (test) |
| V3 | CSRF rotation untested | medium | pre-verified → patch (test) |
| V4 | `recent_events` newest-first ordering unverified | medium | pre-verified → patch (test) |
| V5 | No failure-path test for the atomic token swap + snapshots | medium | pre-verified → patch (test) |

## Design Notes

`/estate/portal/dashboard/` has to exist for the redirect, so 2.2 ships a guarded stub that Story 2.3 replaces. The stub doesn't log `PORTAL_VIEW`; 2.3 does.

Sharing one browser between owner and executor:
- `cycle_key()` keeps the owner's auth keys, so the owner isn't logged out.
- The sliding `set_expiry` also extends the owner's session.
- Owner logout ends the executor session.

All three are accepted.

Codes stay reusable after first use, so an executor whose session lapses, or who switches devices, isn't locked out when the owner is no longer available to reissue. The PRD's "single-use where possible" is read as allowing this.

## Verification

**Commands:**
- `pixi run manage makemigrations --check --dry-run` -- expected: no changes after 0020/0021
- `pixi run pytest tests/unit/ -x -q` -- expected: all pass
- `pixi run pytest tests/functional/ -x -q` -- expected: all pass
- `pixi run lint` -- expected: zero errors
- `pixi run -- ruff format --check .` -- expected: zero diffs

**Manual checks:**
- Run the server: activate, copy the code, open `/estate/portal/` in a private window, and enter it. Revoke from the owner window, then reload the portal and confirm it bounces back to code entry.
