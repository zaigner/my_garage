---
title: 'Epic 3 retro decisions Q2-Q4: beneficiary visibility hint, LINK_REJECTED, noindex'
type: 'feature'
created: '2026-10-29'
status: 'done'
baseline_commit: '2db7d9c5fcb58f7783c3dfc17622ddd56ec8ed80'
route: 'dispatch'
review_loop_iteration: 1
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** These are the Epic 3 retro decisions of 2026-10-29 (`epic-3-retro-2026-10-29.md`, Decisions).
- **Q2:** owners aren't told that a beneficiary sees the item's notes and custom fields.
- **Q3:** a failed claim on a real beneficiary link logs nothing, while a wrong executor code logs `CODE_REJECTED`.
- **Q4:** the claim page should not be indexed.

**Approach:**
- **Q2:** a hint on the item notes field, on both the add and the edit form.
- **Q3:** a new `LINK_REJECTED` access-log event, written when a claim-URL request fails for a hash that matches a real link.
- **Q4:** the claim page already inherits `<meta name="robots" content="noindex">` from `estate/portal/_base.html`, so a test pins it and nothing else changes.

## Boundaries & Constraints

**Always:**
- **Responses unchanged:** every claim-URL response (status, body, headers) stays exactly as today; `LINK_REJECTED` only adds a log row.
- **When to log:** log on a failed GET or POST whose SHA-256 hash matches a `BeneficiaryAccessLink` row (unclaimable for any reason: claimed, revoked, expired, dead executor token, or a lost claim race).
  - **Row contents:** owner = link.owner, token = `link.issued_by_token`, and the beneficiary's name.
  - **No log for:** an unknown hash, HEAD requests, or the reopen-own-link redirect. HEAD changes nothing; the redirect is not a failure. (Many previews and mail scanners use GET, so they can log too; the dedupe below bounds that.)
  - **Hash comparison:** use `secrets.compare_digest`, as elsewhere.
  - **Dedupe (human, 2026-10-29, after review pass 1):** at most one `LINK_REJECTED` row per link per 24 hours. A link is identified by its issuing token plus the beneficiary's name: one active link per beneficiary, and the log has no link FK. A failure within 24 hours of the last matching row logs nothing. Two simultaneous first failures may both log; that is accepted.
- **Panel grouping:** `LINK_REJECTED` joins `ESTATE_SECURITY_EVENTS`, so it shows in the owner's security panel as "Link rejected · <name>". The event-group completeness test must stay green.
- **Hint wording, from one source (amended by the human, 2026-10-29, after review pass 1):** "If you designate this item to a beneficiary, they will see its full details once estate access is activated, including these notes, custom fields, photo and service records." It is the form's `help_texts["notes"]` and appears on both the add form and the edit form of the item detail page.

**Never:**
- No change to which links are claimable, to the 404 page, or to the reopen redirect.
- On the edit page, don't start rendering help text for other fields; model help texts exist and would appear.
- No new HTTP headers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected | Logging |
|---|---|---|---|
| Unknown URL | GET or POST, hash matches no link | 404 page | nothing |
| Reused link | GET or POST from another browser after a claim | 404 page | one `LINK_REJECTED`, beneficiary name, issuing token |
| Revoked / expired / dead token | GET or POST | 404 page | one `LINK_REJECTED` |
| Repeat within 24 h | another failed GET or POST of the same link, under 24 h after its last `LINK_REJECTED` | 404 page | nothing |
| Repeat after 24 h | the same, 24 h or more after the last row | 404 page | one more `LINK_REJECTED` |
| HEAD on a dead link | HEAD | 404 | nothing |
| Reopen own link | live session for that link | 302 → portal | nothing |
| Claimable link | GET → confirm page; POST → claim | unchanged | GET nothing; POST `LINK_CLAIMED` only |
| Claim page / 404 page | GET | contains `<meta name="robots" content="noindex">` | — |

</frozen-after-approval>

## Code Map

- `src/my_garage/estate_views.py:286-320` `beneficiary_claim` -- the GET failure (`get_claimable_beneficiary_link` → None) and the POST failure (`claim_beneficiary_link` → None) both return `_beneficiary_not_found`. The reopen redirect runs first; keep it first.
- `src/my_garage/api/services.py` `claim_beneficiary_link` (docstring says "Failed claims log nothing"; update it). The pattern to mirror is `verify_executor_code`, which logs `CODE_REJECTED` in the service via `log_estate_access(owner, event, token=, request=, beneficiary=)`.
- `src/my_garage/api/estate_selectors.py` -- `get_claimable_beneficiary_link` shows the hash lookup with `compare_digest`. Add a read-only lookup of the link by hash, whatever its state.
  - `ESTATE_SECURITY_EVENTS`: add `LINK_REJECTED`.
  - Fix the `get_executor_access_status` docstring ("TOKEN_*/CODE_*" → include LINK_*).
- `src/my_garage/models.py:612` `EstateAccessLog.EVENT_CHOICES` -- add `("LINK_REJECTED", "Link rejected")` after `LINK_CLAIMED`. `event` is max_length 20, which fits. Then `pixi run manage makemigrations` (choices-only AlterField; the latest is 0024).
- `src/my_garage/forms.py:222` `DynamicCollectionItemForm.Meta` -- add `help_texts`.
- `src/my_garage/templates/my_garage/collection_item_form.html:180` -- already renders `field.help_text`; no change expected.
- `src/my_garage/templates/my_garage/collection_item_detail.html:230-238` -- the edit-mode standard-field loop renders no help text. Add the `<p class="text-gray-500 text-xs mt-1">` line for `field.name == "notes"` only.
- `src/my_garage/templates/my_garage/estate/portal/_base.html:6` -- existing noindex meta; the beneficiary `_base.html`, `claim.html` and `not_found.html` inherit it.
- Tests to follow:
  - `tests/functional/test_estate_story3_4.py` (claim matrix and fixtures).
  - `tests/unit/test_beneficiary_claim_service.py`.
  - `tests/unit/test_estate_access_service.py:193` (event-group completeness).
  - Grep for assertions that a failed claim logs nothing (e.g. "no log") and update only the ones the matrix changes.

## Tasks & Acceptance

**Execution:**
- [x] `src/my_garage/models.py` + new migration -- add the event choice.
- [x] `src/my_garage/api/estate_selectors.py` -- by-hash lookup, the `ESTATE_SECURITY_EVENTS` entry, and the docstring. `get_claimable_beneficiary_link` reuses the by-hash lookup, then applies its state checks, so the hash lookup is written once.
- [x] `src/my_garage/api/services.py` -- a service that logs `LINK_REJECTED` for a matching hash, applying the 24-hour dedupe (an `exists()` check on owner, event, token and beneficiary_name, newer than now − 24 h); `claim_beneficiary_link` docstring.
- [x] `src/my_garage/estate_views.py` -- call it on both failure paths, skipping HEAD. Any comment says HEAD changes nothing; it must not claim that previews use HEAD.
- [x] `src/my_garage/forms.py`, `collection_item_detail.html` -- the notes hint.
- [x] Tests:
  - one per matrix row (functional, in `tests/functional/test_estate_retro_decisions.py`), with the 24-hour rows driven by moving the last row's timestamp;
  - each view failure path (GET and POST) asserts the row's `ip_address` (set `REMOTE_ADDR`);
  - a unit test for the service;
  - add-form and edit-form hint assertions, scoped to the notes field.

**Acceptance Criteria:**
- Given a reused link opened twice in another browser, when the owner opens the activate page, then the security panel lists one "Link rejected" row naming the beneficiary.
- Given the full suite, when it runs, then it passes, and `makemigrations --check` reports no changes.

## Verification

**Commands:**
- `pixi run pytest tests/unit/ -x -q`, `pixi run pytest tests/functional/ -x -q` -- all pass
- `pixi run manage makemigrations --check --dry-run` -- no changes
- `pixi run lint`, `pixi run -- ruff format --check .` -- clean

## Implementation Notes

## Spec Change Log

- **Loop 1 (2026-10-29), intent_gap.**
  - **Trigger:** review pass 1. B1/E1: previews and mail scanners GET links, so GET logging gives false alarms. B2/E3/E4: unthrottled rows crowd the 10-row panel. B3: the hint understates what a beneficiary sees.
  - **Human decisions:** dedupe to one row per link per 24 hours, and the "full details" hint wording. Both are written into the frozen block.
  - **Also amended:** the matrix (two 24-hour rows), the AC (one row, not two), tasks (the single hash lookup, IP assertions, the HEAD comment).
  - **Known-bad state avoided:**
    - a security panel flooded by reloads or scanner re-checks;
    - a code comment claiming previews use HEAD;
    - a hint that hides service records and photos.
  - **KEEP** (worked in pass 1 and must survive):
    - `get_beneficiary_link_by_hash` with `compare_digest`;
    - `log_beneficiary_link_rejected(raw_token, request=None)` returning the row or None;
    - the view calls on both failure paths, with HEAD skipped and the reopen redirect still first;
    - migration 0025 (choices-only);
    - `help_texts["notes"]`, plus the notes-only `<p>` on the edit page;
    - the test file layout (`TestLinkRejectedMatrix`, `TestNoindex`, `TestNotesHint`) and the unit `TestLinkRejected` class;
    - the lost-race test via patching the view's claim call.

## Review Triage Log

Pass 1 (2026-10-29; blind B, edge-case E, verification-gap V on Opus).

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| B1/E1/E2 | GET logging assumes previews use HEAD. Scanners and unfurlers GET, so a claimed link re-fetched by Safe Links or a double-submit logs false rejections | medium | Real: `test_estate_story3_4.py::test_preview_fetch_does_not_burn_link` models a preview as GET. Rooted in the frozen "When to log" rule → **intent_gap** → human chose a 24-hour dedupe |
| B2/E3/E4 | Unthrottled `LINK_REJECTED` from anyone holding a dead URL crowds the 10-row security panel and grows the table | medium | Real: `get_executor_access_status` slices `[:10]` over `ESTATE_SECURITY_EVENTS`. Same root cause as B1 (no limit in the frozen rule) → **intent_gap** → resolved by the dedupe |
| B3 | Hint names only notes and custom fields; the beneficiary page also shows photo, purchase details, service records and the snapshot | medium | Real (`_item_header`, `_item_provenance`, `_item_activation`). Frozen wording → **intent_gap** → human chose "full details" |
| V1/B7 | No test asserts `ip_address` on a `LINK_REJECTED` row | low | Pre-verified gap (V). Folded into the re-derivation tasks |
| B6 | `get_beneficiary_link_by_hash` repeats the hash lookup in `get_claimable_beneficiary_link` | low | Real duplicate. Direct fix, folded into the re-derivation tasks |
| B4/E5 | A failing log INSERT turns the 404 into a 500 | low | True, and the same for every `log_estate_access` call (portal views, `CODE_REJECTED`). Needs a DB error on a dead-link request. Fix adds a guard → rejected |
| B5 | A failure hashes the token twice and fetches the link twice | low | Only on failure paths, one extra indexed lookup. Fix changes the service signature → rejected |
| B8 | Tests POST without CSRF; a cross-browser POST really gets 403 | low | CSRF middleware runs before the view and doesn't change the view's logic; the stale-confirm-page POST runs the same branch the tests cover. Rejected |
| B9 | Kill scenarios repeated across `test_estate_story3_4.py` and the new file | low | Test duplication only; fix restructures fixtures. Rejected |
| E2 (pre-existing part) | A double-submitted claim's second POST carries the cycled-away session and shows the real beneficiary a 404 | maybe-false | Depends on which response the browser keeps after a double click. Pre-existing since Story 3.4 → **defer** (medium if true, unverified) |

Pass 2 (2026-10-29, after loop 1; blind B, edge-case E, verification-gap V on Opus). V: no gaps.

| # | Finding | Verdict | Evidence / route |
|---|---|---|---|
| E1/B1/E4/E6 | Dedupe key (token + name) is shared by a revoked link and its reissue under the same token, and by links whose token was deleted (`token=None`), so an old link's row hides the new link's first rejection for 24 h | low | Real: `issue_beneficiary_link` deactivates and recreates under the same token. Smallest fix, a `timestamp__gte=link.issued_at` bound, keeps the human's "per link" intent and adds no surface → **patch**, plus a reissue test |
| B9 | `assert raw not in entry.beneficiary_name` is vacuous after `== "Ann"` | low | Real; deletion → **patch** |
| E2/B2 | Two same-named beneficiaries under one token share a window | low | Real but needs two beneficiaries with identical names, and the `issued_at` bound narrows it. Full fix needs a link FK (migration) → rejected |
| E3 | A rename between failures logs a second row inside 24 h | low | One extra row; the bound is a noise limit, not a guarantee. Rejected |
| B3 | Later attempts from a different IP inside the window are dropped | low | Real, but it reopens the human's "one row per link per day" decision of loop 1. Rejected as decided |
| B4 | The row doesn't record why the claim failed | low | A new feature, outside the intent. Rejected |
| B5 | A double-submit by the real beneficiary logs `LINK_REJECTED` | carried | Pass 1 B1/E2 (intent_gap, resolved by the dedupe); the 404 part is already deferred. Carried |
| B6/E5 | A failing log write turns the 404 into a 500 | carried | Pass 1 B4/E5, rejected. Carried |
| B7 | The link is looked up more than once per failed request | carried | Pass 1 B5, rejected. Carried |
| B8 | No index covers the dedupe query | low | It runs only on failed known-link requests; a personal app's per-owner log is small, and the `(owner, -timestamp)` index narrows it. Rejected |
| B10 | The hint shows to owners without beneficiaries; "designate … to" wording; placement under Notes | low | Wording and placement are the human's frozen decision (loop 1); showing it always was in the approved spec. Rejected |
| B11 | `deferred-work.md` and the spec are missing from the diff | false | The review diff covers `src` and `tests` by design; the leftovers are in the triage logs and `deferred-work.md`. Rejected |
