---
title: 'Epic 2 retrospective fixes'
type: 'bugfix'
created: '2026-10-27'
status: 'done'
route: 'dispatch'
baseline_commit: 'c66d5b64bf0712a8e67d3fbd6210331ce986b979'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-retro-2026-10-27.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Epic 2 retrospective (`epic-2-retro-2026-10-27.md`) found these defects:
- The owner's "Remove" button for the executor submits the Update form (R1).
- The raw executor code waits in plaintext in the server-side session, and the only test that it is shown can't fail (R2, R3).
- Build artifacts are committed to the repo.
- The owner's activity panel drowns security events in page views and reports stale "last used" times (R9, R10).
- Negative money and UTC times are shown misleadingly (R11, R12).
- Deploy can roll production back to an older image (R13).

**Approach:**
- Fix each defect in place.
- Commit the retro document with the fixes.
- The decision items (R4–R8, Cloudflare Access) belong to correct-course and are not part of this change.

## Boundaries & Constraints

**Always:**
- `pixi run` for every command. Factory/fixture style matches the neighbouring tests.
- Views keep calling selectors and services; no new ORM in templates.
- The raw code never touches the server-side session or the database.
- Every fix gets a test that fails without it, except the workflow change and the untracking.

**Never:**
- Migrations or model changes.
- Changing code lifetime, revocation rules, snapshot linkage, or which collections count toward the estate (R4–R8).
- Cloudflare configuration.
- Deleting the untracked files from disk.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Remove from the UI | owner page `/estate/executor/` rendered, then parsed as a browser does (html5lib) | the Remove button's form posts to `/estate/executor/remove/`; the Update button's form posts to `/estate/executor/` | — |
| Activate | POST `/estate/activate/` with confirmed | 302 to success; the session has no `estate_activation_token`; a signed, HttpOnly, short-lived cookie scoped to the success path carries the code | — |
| Success page | GET within 10 minutes | the shown code hashes to the active token's `token_hash`; response is never cached; cookie deleted | — |
| Success page again, or expired, or tampered cookie | second GET, cookie > 10 min old, or bad signature | 302 to `/estate/activate/` | bad signature treated as missing |
| Replaced code | cookie code no longer matches the active token (double submit) | 302 to `/estate/activate/` with an info message that a newer code was issued | — |
| Activity panel | 12 `PORTAL_VIEW` rows plus 1 `CODE_REJECTED` | security list shows `CODE_REJECTED`; a summary line gives the view count and last view time for the current token | no views → no summary line |
| In use | token used, then executor browses | status shows when the code was entered and the last portal visit | — |
| Negative money | `_money.html` value −50 | "−$50" (U+2212) | None → "—", 0 → "$0", unchanged |
| Times | estate templates that render time of day | show a zone label (e.g. "UTC") | date-only formats unchanged |
| Out-of-order deploy | run for a commit that is an ancestor of the deployed image's commit | job ends green without applying | unresolvable deployed tag → deploy proceeds |

</frozen-after-approval>

## Code Map

- `src/my_garage/templates/my_garage/estate/executor.html:49-78` -- the Remove `<form>` (`:69-76`) is nested inside the Update form. Fix: move it out as a standalone `<form id=…>` after the outer form, and give the Remove button `form="<id>"` so the flex layout stays. The `onsubmit` confirm stays on the moved form.
- `tests/functional/test_estate_story1_2.py:175` -- `TestExecutorRemove`. Add the html5lib form-ownership test here.
- `src/my_garage/estate_views.py:321-326` (`estate_activate`) -- replace `session["estate_activation_token"]` with `redirect(...).set_signed_cookie(name, raw, salt=…, max_age=600, httponly=True, secure=settings.SESSION_COOKIE_SECURE, samesite="Strict", path=reverse("estate:activate_success"))`.
- `src/my_garage/estate_views.py:353-373` (`estate_activate_success`):
  - Add `@never_cache`.
  - Read with `get_signed_cookie(..., default=None, max_age=600)`.
  - Match `_hash_code(raw)` against the active token via the existing `get_executor_access_status(...)["token"]`. Compare in constant time (`secrets.compare_digest`).
  - Delete the cookie on every response.
  - Expose a hash helper from services instead of importing a private name if needed.
- `src/my_garage/api/services.py:190-197` -- docstring: the code is returned once and stored only as its hash.
- `tests/functional/test_estate_story2_1.py:159-180`:
  - Replace the test that can't fail with a check that the code on the page (inside the `select-all` div) hashes to the active `token_hash`.
  - Rewrite `test_success_page_purges_token_from_session` for the cookie: second GET redirects, and the session never holds the code.
  - Add cases for an expired cookie, a tampered cookie, and a replaced code.
- `src/my_garage/api/selectors.py:248-272` (`get_executor_access_status`):
  - Keep `token` and `state`.
  - Replace `recent_events` with `security_events`: the last 10 rows where `event` is in the TOKEN_*/CODE_* set.
  - Add `view_count` and `last_view_at`: `PORTAL_VIEW`/`ITEM_VIEW` rows for the returned token, in one aggregate query.
  - Update the docstring.
- `tests/unit/test_estate_access_service.py:167-186` -- these assert on `recent_events`. Update them to the new keys, add a test that views don't crowd out security events, and add view-summary tests.
- `src/my_garage/templates/my_garage/estate/activate.html:36-61`:
  - Status line: "In use — code entered <last_used_at>", then "· last portal visit <last_view_at>" when present.
  - Render `security_events` under "Recent activity".
  - Add a summary line "Portal views: N · last <time>".
  - Grep the tests for "last used" and "Recent activity" before renaming any copy (`test_estate_story2_2.py:161` checks "In use" and "Code accepted").
- `src/my_garage/templates/my_garage/estate/portal/_money.html` -- add a `value < 0` branch that renders "−" + `currency_display`. `currency_display` already rounds `abs()`, see `templatetags/my_garage_extras.py:40-47`.
- Time-of-day formats: `activate.html:40,41,58`, `activate_success.html:36`, `portal/item_detail.html:119`. Append ` T` to the format, which renders "UTC" (`TIME_ZONE="UTC"`, `USE_TZ=True`).
- `.github/workflows/deploy.yml`:
  - Add a top-level `concurrency: {group: deploy-k3s, cancel-in-progress: false}`.
  - Set checkout `fetch-depth: 0`.
  - Add a guard step after "Ensure kubectl". It reads the django image tag with `kubectl get deploy django -n my-garage -o jsonpath=…`, which the runner's RBAC allows (get on deployments, `k8s/ci/rbac.yaml:38-39`).
  - If the deployed tag resolves to a commit, differs from the built SHA, and `git merge-base --is-ancestor <built> <deployed>` is true, set `skip=true` and add a notice.
  - Every later step except "Show pod state on failure" gets `if: steps.<guard>.outputs.skip != 'true'`.
- `.gitignore:132` -- change to `celerybeat-schedule*`, and add `coverage.json`. Run `git rm --cached` on `celerybeat-schedule.{bak,dat,dir}`, `src/celerybeat-schedule.{bak,dat,dir}` and `coverage.json`.
- `_bmad-output/implementation-artifacts/epic-2-retro-2026-10-27.md` -- untracked. Commit it as is.

## Tasks & Acceptance

**Execution:**
- [x] `src/my_garage/templates/my_garage/estate/executor.html` + `tests/functional/test_estate_story1_2.py` -- un-nest the Remove form; add the html5lib ownership test.
- [x] `src/my_garage/estate_views.py`, `src/my_garage/api/services.py` + `tests/functional/test_estate_story2_1.py` -- carry the code in a signed cookie, with `never_cache` and the active-token match; fix the docstring; rewrite the success-page tests per the matrix.
- [x] `src/my_garage/api/selectors.py`, `activate.html` + `tests/unit/test_estate_access_service.py` (and the functional panel test) -- security events, view summary, status wording.
- [x] `portal/_money.html` + a portal test -- signed negatives.
- [x] estate templates listed above + a test -- zone label on times.
- [x] `.github/workflows/deploy.yml` -- concurrency group and the superseded-commit guard.
- [x] `.gitignore` + `git rm --cached` -- untrack the artifacts.

**Acceptance Criteria:**
- Given an owner with a designated executor, when they click Remove in a browser and confirm, then the executor is deleted and any active code is revoked.
- Given any new estate test, when the fix it covers is reverted, then that test fails.
- Given this change merged, when Deploy runs for the newest main commit, then it applies and waits for rollouts as before.

## Implementation Notes

- The raw code goes to the success page in the signed cookie `estate_activation_code`:
  - salt `my_garage.estate.activate_success`;
  - no `max_age` when set, so it's a browser-session cookie;
  - 600 s enforced on read;
  - HttpOnly, SameSite Strict, `secure=SESSION_COOKIE_SECURE`;
  - path `/estate/activate/success/`.
- The success page is `never_cache` and deletes the cookie on every response. It shows the code only when its hash matches the active token (`hash_executor_code`, formerly `_hash_code`). It redirects with a message when:
  - the cookie is missing or expired;
  - the code was replaced;
  - the code is no longer active.
- `get_executor_access_status` returns `security_events` (TOKEN_*/CODE_*, last 10), `view_count` and `last_view_at` for the returned token, in 3 queries. A test keeps `ESTATE_SECURITY_EVENTS` and `ESTATE_VIEW_EVENTS` in step with `EVENT_CHOICES`.
- The deploy guard reads the django image tag and skips when the built SHA is a strict ancestor of the deployed one. The comments document two limits:
  - a pending run can be replaced, so a third overlapping Build can drop the newest deploy;
  - rolling back means reverting on main.
- Gate: unit 373, functional 566, lint and format clean, artifacts untracked, workflow YAML parses.

## Spec Change Log

## Review Triage Log

**Code review pass 1 (2026-10-27).** Layers: blind (B), edge-case (E), verification-gap (V). The review diff left out the deletion of the generated `coverage.json` (~300 KB) and this spec, which was the edge-case layer's claims file.

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| B1/E1/E8 | A concurrency group keeps only one pending run, so a third overlapping Build can cancel the newest commit's deploy | low | Real GitHub behaviour. It needs three Builds to overlap and finish out of order, and the next merge redeploys the tip. A proper fix needs new logic. Rejected as a behaviour change. **Patch:** the comment now states the limitation. |
| B2/E2/V-o1 | The guard blocks rolling back by re-running an old Deploy run | low | Real. In this pipeline the rollback path is a revert on main, which is what the next deploy pins. **Patch:** comment only. |
| B3 | `max_age` on `set_signed_cookie` writes the plaintext code to the browser's on-disk cookie store | low | Real: `max_age` makes the cookie persistent. **Patch:** drop it on set. `get_signed_cookie(max_age=600)` still enforces the limit. Also reword the "must not persist" docstring. |
| B4/E5/V-o3 | `_money.html` renders "−$0" for values in (−0.5, 0) | low | Real: `currency_display` rounds to $0. **Patch:** use `value < -0.5`, plus a test case. |
| B5 | `ESTATE_SECURITY_EVENTS` / `ESTATE_VIEW_EVENTS` duplicate `EVENT_CHOICES` | low | Epic 3's new beneficiary-link events would silently land in neither list. **Patch:** a test that the two lists are disjoint and together cover every choice. |
| B6 | "Portal views: N" is for one token, under a list that spans all tokens | low | Real ambiguity after a reactivation. **Patch:** relabel to "Portal views with this code". |
| B7 | The success page runs the 3-query status selector just to get the token | low | Two extra queries on a rarely visited page. The fix would add a selector. Rejected. |
| B8 | Retro follow-through isn't recorded: sprint status, deferred items, "Nothing below has been applied" | low | Real, but it's documentation. Handled when the retrospective is finalized (status note in the retro doc, then `sprint_status.py update`). R4–R8 go to correct-course, not `deferred-work.md`. **Patch** (doc). |
| B9/V2 | The cookie's `secure` flag is never asserted | medium | Pre-verified (V). Dropping `secure=` would pass every test. **Patch:** test. |
| B10/E3 | A missing or expired cookie redirects with no explanation | low | Real. A refresh lands the owner back on activate with nothing said. **Patch:** one `messages.info` line, plus a test. |
| B11 | The spec isn't in the diff | false | By design: the spec is the claims file, and it's committed with the change after review. |
| V1 | No test that a revoked code stays off the success page | medium | Pre-verified (V). Removing `not token.is_active` would show a revoked code and pass. **Patch:** test. |
| V3 | The Remove-form test doesn't check for a CSRF token | low | Pre-verified (V). A lost `{% csrf_token %}` would reopen R1. **Patch:** one assertion. |
| V4 | The deploy guard logic has no automated check | low | Pre-verified (V). The repo has no harness for workflow shell. **Defer** (`deferred-work.md`). |
| V-o2/E6 | Session rows written before this change still hold codes | low | Only the old success view ever cleared the key. Production has had no activations (user, 2026-10-26). The fix would be a data migration. Rejected. |
| V-o4 | html5lib isn't a declared dependency | low | It's transitive via beautifulsoup4, and the tests fail loudly with `FeatureNotFound` if it disappears. Declaring it would churn `pixi.lock`. Rejected. |
| E4 | After a double submit, the "newer code" message implies the owner has a usable code they never saw | low | Real wording problem. **Patch:** the message now says to issue a new code. |
| E7 | The per-view detail list was removed, and the security list keeps a dead `item_name` branch | low | Removing the list is the spec's intent (a summary line instead). Only `ITEM_VIEW` rows carry an item, so the branch is dead. **Patch:** delete it. |
| E9 | `test_no_views_no_summary_line` and `test_cookie_just_inside_lifetime_is_shown` pass on the old code | low | Real against the "fails on revert" acceptance criterion. **Patch:** the lifetime test now asserts the cookie and the token hash. The no-views test is the negative half of `test_views_do_not_hide_security_events`, which does fail on revert, so it stays as it is. |

## Design Notes

**Why a cookie rather than the session:** the success page has to survive the POST→redirect→GET without the server ever storing the plaintext code. A signed, HttpOnly cookie on a path that only the success page uses keeps the code in the owner's own browser for at most 10 minutes. Matching it against the active token's hash also covers the case where the owner submits twice: the success page will never show a code that has already been revoked.

## Verification

**Commands:**
- `pixi run pytest tests/unit/ -x -q` -- expected: all pass
- `pixi run pytest tests/functional/ -x -q` -- expected: all pass
- `pixi run lint` -- expected: zero errors
- `pixi run -- ruff format --check .` -- expected: zero diffs
- `git ls-files | command grep -E "celerybeat-schedule|^coverage.json$"` -- expected: no output

**Manual checks:**
- The deploy workflow YAML parses: `python -c "import yaml;yaml.safe_load(open('.github/workflows/deploy.yml'))"`. Every step after the guard carries the skip condition, except the failure step.
