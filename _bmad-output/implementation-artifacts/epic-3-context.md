# Epic 3 Context: Beneficiary Scoped Access

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

After the owner activates estate access, the executor issues a unique, revocable link per beneficiary from the executor portal. The beneficiary exchanges the link once for a 30-day session and sees only the items designated to them, with full detail including the owner's personal note, with isolation enforced at the ORM query level. The epic first hardens the activation snapshot and the estate's scope (Stories 3.1-3.2), because beneficiary views and the Epic 4 PDFs depend on them. No Estate & Legacy architecture or UX docs exist.

## Stories

- Story 3.1: Activation Snapshot Integrity
- Story 3.2: Estate Scope & Executor Replacement
- Story 3.3: Beneficiary Link Generation (Executor)
- Story 3.4: Beneficiary Portal (Session)
- Story 3.5: Beneficiary Item Detail View

## Requirements & Constraints

- Executor (not owner) issues beneficiary links; no my_garage account needed for executor or beneficiary.
- Links are single-use: opening one claims it and starts a session (30-day sliding expiry). An unclaimed link expires after 7 days. Invalid, reused, revoked or expired links all return 404 with no hint whether the token ever existed.
- Beneficiary sees only items assigned to them, filtered in the ORM on every request. UI filtering alone is not enough. An item assigned to someone else, or unassigned, returns 404.
- Beneficiary item detail shows name, collection type, photo, current value, purchase price/date, service records, notes, custom fields, the assignment's conditional note, and the activation snapshot figures.
- Activation snapshots are append-only: the app issues no update or delete on them. Item deletion only nulls the `item` FK, and the row stays.
- Soft-deleted collections (`CollectionType.is_active=False`) are excluded from the estate everywhere.
- Replacing the executor (name change) must revoke the active code. A contact-only edit keeps it.
- Snapshot figures are labelled "Purchase price" and "Value minus purchase price", not "Cost basis" / "Equity". The data is unchanged.
- Performance: beneficiary view loads within 2s regardless of portfolio size. Executor and beneficiary pages must meet WCAG 2.1 AA.
- Beneficiary PII is never sent to third parties or used for analytics.
- The Story 3.1 migration needs a reverse migration (and backfill).
- Quality gate after each story: `pixi run pytest tests/unit/ tests/functional/ -x -q`, `pixi run lint`, `pixi run -- ruff format --check .`.

## Technical Decisions

- Tokens: `secrets.token_urlsafe(32)`, stored only as SHA-256 hash, compared with `secrets.compare_digest`. The raw link is shown once via the same one-shot signed-cookie pattern as the executor activation code, with a "cannot be recovered" warning.
- New model `BeneficiaryAccessLink` (Story 3.3): FK to Beneficiary (FK, not OneToOne, so deactivated links stay for audit), FK to owner, `issued_by_token` FK to EstateAccessToken (SET_NULL), `link_token_hash` (indexed), `issued_at`, `expires_at`, `claimed_at`, `is_active`. At most one active link per beneficiary, enforced in service `issue_beneficiary_link(beneficiary, token, request)`. A link is only usable while its issuing executor token is usable.
- `ValuationSnapshot` gains `token` FK (EstateAccessToken, SET_NULL, null) and `item_name` CharField(200), and `item` becomes SET_NULL/null. `activate_estate_plan` sets both in the same `bulk_create`. Portfolio and item-detail selectors filter `snapshot_trigger="ESTATE_ACTIVATION", token=<session token>`, with no timestamp matching. Deleted items appear as "Removed after activation" with their stored name and no detail link.
- Story 3.2 touches `activate_estate_plan`, `get_estate_dashboard_context`, `get_executor_portfolio_context`, `get_executor_item`, and `executor_view`. Name change is detected against the stored `EstateExecutor.name`. Revocation uses `revoke_executor_access(user, request=request)` and logs `TOKEN_REVOKED`.
- Claim: `claim_beneficiary_link(raw_token, request)` in `api/services.py`. GET on the claim URL only shows a confirm page; the CSRF-protected POST claims. Reopening a claimed link in the browser whose live session is that link redirects to the portal; every other reuse is the identical 404. Session keys `estate_beneficiary_link_id` and `estate_beneficiary_owner_id`, separate from executor and Django auth keys, which are never touched. A `beneficiary_required` decorator in `estate_views.py` re-checks the link on every request, applies `never_cache`, and slides the 30-day expiry. If the link is revoked or the executor token stops being usable, it clears the keys and returns 404.
- Isolation query (as built, `_beneficiary_assignment_qs`): `BeneficiaryAssignment.objects.filter(beneficiary=link.beneficiary, is_charitable=False, item__owner=link.owner, item__collection_type__is_active=True).select_related("item__collection_type")`. Item detail verifies a matching assignment (`item__pk=item_id`), else 404.
- Views: `require_safe` and logged after render (GET only). The link issue/revoke POST views (`/estate/portal/beneficiaries/<id>/link/`) are the portal's only state-changing views: POST only, CSRF-protected, behind `executor_required`, and they change no estate or asset data.
- Audit log events: `LINK_ISSUED`, `LINK_REVOKED`, `LINK_CLAIMED`, `BENEFICIARY_VIEW`. Add the link events to the owner activity panel's security events. The existing test keeps `ESTATE_SECURITY_EVENTS` / `ESTATE_VIEW_EVENTS` complete.
- Conventions: selectors for reads and services for writes (`api/selectors.py`, `api/services.py`). Server-rendered Django templates with Tailwind and Alpine, and no new DRF endpoints. Photos are served via a beneficiary photo route using the `static_serve` + `private, no-store` pattern from `/estate/portal/items/<id>/photo/`. Estate data is excluded from cleanup/TTL.

## UX & Interaction Patterns

- Executor dashboard `/estate/portal/dashboard/` lists each beneficiary with at least one designated item, with link status "No link", "Issued — not yet opened (expires <date>)", "Opened <date>" or "Revoked", plus Issue link and Revoke (confirmed) actions.
- Beneficiary pages sit under `/estate/beneficiary/` (no token in the URL after claim). Templates `estate/beneficiary/portal.html` and `item_detail.html` extend a beneficiary `_base.html` with no owner account chrome. The portal shows the beneficiary's name, relationship and a greeting. The empty state reads "No items have been designated for you yet."
- Story 3.2: the executor form shows a confirmation ("this revokes the current access code") before saving a name change.

## Cross-Story Dependencies

- 3.1 and 3.2 come first. 3.3-3.5 build on the token-bound snapshots and the estate scope.
- 3.3 -> 3.4 -> 3.5: the link model and issuing come first, then claim and session, then item detail (it reuses `beneficiary_required`).
- Depends on Epic 2 (executor token, portal, session patterns, access log). Epic 4 depends on this epic, and Story 4.4 (beneficiary export) uses the beneficiary session.
- Release gate: before real links or codes are handed out, add a Cloudflare Access bypass for `/estate/portal/*` and `/estate/beneficiary/*`. Otherwise recipients can only reach the portal on the LAN.
