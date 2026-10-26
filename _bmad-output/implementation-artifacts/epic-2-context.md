# Epic 2 Context: Estate Access — Executor Token, Portal & Valuation Snapshot

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

The owner activates estate access, which issues a one-time-display executor code and locks a valuation snapshot of every item. The executor, who has no my_garage account and may be grieving, under stress, and on a phone, enters that code and gets a read-only portal covering the whole portfolio: every item, its snapshot and current value, its beneficiary, and a clear flag on unassigned items. The owner stays in control: they can see when the code is used and revoke it at any time, and every access event is logged. The MVP bar is that a first-time executor can find and understand every asset within 15 minutes of receiving the code.

## Stories

- Story 2.1: Estate Plan Activation, Executor Token Generation & Valuation Snapshot (shipped)
- Story 2.2: Executor Code Entry, Session, Revocation & Access Log
- Story 2.3: Executor Portfolio View
- Story 2.4: Executor Item Detail View

## Requirements & Constraints

- Executor access needs no Django account. The code is the only credential.
- The portal is strictly read-only: no create, update, or delete of any asset or estate record.
- The owner can revoke the executor code before or after it has been used, and revocation must take effect promptly.
- Every executor access event (code use, portal views, revocation) is logged with timestamp and action type in an immutable, append-only log, kept for the life of the owner account and never cleaned up.
- Unused executor codes expire after 72 hours. An executor session expires after 30 days of inactivity.
- Executor session state must not collide with the owner's Django auth session.
- Codes come from the `secrets` module, are stored only as SHA-256 hashes, are compared in constant time, and are never logged or persisted raw.
- Failed code entry shows one generic message that never reveals whether a code exists, is revoked, or expired.
- Assets added after activation still appear in the portal (with no snapshot value). Unassigned assets carry a prominent badge.
- Null valuations display as "—", never blank or zero.
- Performance: the full portfolio loads in under 3 s with no pagination; activation completes in under 5 s.
- Executor-facing pages meet WCAG 2.1 AA (≥4.5:1 contrast, keyboard navigable, labelled fields, descriptive errors) and work on mobile. Owner estate pages meet WCAG 2.1 A.
- Beneficiary PII is never sent to third parties.

## Technical Decisions

- All assets are `DynamicCollectionItem`. There are no separate Vehicle/Timepiece paths in estate features.
- `EstateAccessToken` uses an owner FK (not OneToOne) so deactivated tokens stay as audit trail; the service keeps at most one `is_active=True` per owner. Tokens are deactivated, never deleted.
- `ValuationSnapshot` is append-only. Cost basis comes from `purchase_price` (null-preserving), not `total_cost_basis`.
- The raw activation code is handed to the success page through a session pop, so it displays exactly once.
- Executor auth is the Django session keys `estate_executor_owner_id` and `estate_executor_token_id`, checked by an `executor_required` decorator that re-validates the token on every request. Portal views do not use `@login_required`.
- New append-only `EstateAccessLog` model (owner, token, event, item + item_name, client IP, timestamp). The IP comes from `CF-Connecting-IP`, else `REMOTE_ADDR`. No user agent is stored.
- Portal templates live under `estate/portal/` and are standalone (no `{% extends %}` of the owner chrome), with minimal nav and a luxury aesthetic.
- Owner estate views live in `src/my_garage/estate_views.py` / `estate_urls.py` (namespace `estate`). Reads go through `api/selectors.py` and writes through `api/services.py`.
- No new DRF endpoints. All estate operations are synchronous Django views.
- Deployment: the live site sits behind Cloudflare Access. The owner chose not to add a bypass for `/estate/portal/*` (2026-10-26), so the portal is reached through Access like the rest of the site.
- Shipped in 2.2 and reused here:
  - `executor_required` sets `request.estate_owner` / `request.estate_token`, re-checks the token, and applies `never_cache`.
  - Portal views use `@require_safe` outermost.
  - `log_estate_access(owner, event, token=, item=, request=)` records the IP.
  - Portal templates extend the standalone `estate/portal/_base.html` (CDN assets only, no `/static/` or `/media/`).
  - `PUBLIC_BASE_URL` builds links for people outside the LAN.

## Cross-Story Dependencies

- 2.2 provides `executor_required`, the session keys, and `EstateAccessLog`, which 2.3 and 2.4 depend on. 2.3 and 2.4 write `PORTAL_VIEW` / `ITEM_VIEW` events.
- 2.2 changes 2.1's activation service (sets `expires_at`, logs issue/revoke) and the executor-removal view (revokes the active code).
- The executor "Download PDF" button and export belong to Story 4.2 (Epic 4), not this epic.
- Epic 3 (beneficiary links) reuses this epic's token/session patterns and adds its own `EstateAccessLog` event types.
