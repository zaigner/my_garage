# Sprint Change Proposal: Estate & Legacy, before Epic 3

**Date:** 2026-10-27
**Scope:** Moderate. The backlog is reorganized and two stories are added; no epics are added or removed.
**Mode:** Batch. All decisions below were made by Zaigner77 on 2026-10-27.
**Status:** Approved by Zaigner77 on 2026-10-27, and applied on branch `docs/estate-correct-course-epic3`. Sprint status was regenerated with `sprint_plan.py`, and retro action items 1 and 2 were closed.

## 1. Issue summary

Two sets of problems have to be resolved before Epic 3 (beneficiary access) starts.

1. **Plan conflicts in Epics 3–4,** found by the readiness gate on 2026-10-25:
   - PRD FR19 and Journey 3 say the **executor** issues beneficiary links. Story 3.1 says the **owner** does.
   - NFR8 makes beneficiary links single-use, but Stories 3.2–3.4 put the token in every URL.
   - Story 3.4 needs Epic 4's PDF service (4.1), while Epic 4 lists Epic 3 as a dependency. That's a loop.
   - The final FR coverage map (`epics-estate-legacy.md` "Step 4 — Final Validation") uses its own FR names, which don't match the PRD's numbering. For example, it lists "FR16 token hashing" where the PRD's FR16 is code-based executor access.
2. **Decisions from the Epic 2 retrospective** (`implementation-artifacts/epic-2-retro-2026-10-27.md`, findings R4–R8), plus technical notes that no longer match the code:
   - **R4:** `ValuationSnapshot` has no link to its token and is CASCADE-deleted with its item, which conflicts with FR39 and NFR17.
   - **R5:** the epic calls the executor code "one-time", but a used code stays valid until it's revoked.
   - **R6:** replacing the executor through Update leaves the old code live.
   - **R7:** soft-deleted collections count toward the estate.
   - **R8:** the snapshot's "cost basis" is really the purchase price.
   - The Cloudflare Access bypass has been skipped.

**Evidence:** the retro document (sourced findings plus a live behaviour run), the epics file line references below, and the PRD (`prd.md:82, :221, :405, :440`).

## 2. Impact analysis

### Epics

| Epic | Impact |
|---|---|
| Epic 2 (done) | Technical notes and wording updated to match what was built (no code change). R4, R6, R7 and R8 become new work in Epic 3. |
| Epic 3 | Two new stories at the start: 3.1 snapshot integrity (R4), and 3.2 estate scope and executor replacement (R6, R7, R8). Beneficiary links move to the executor. Links are exchanged once for a session (NFR8). The beneficiary export moves out to Epic 4. Stories are renumbered 3.3–3.5. |
| Epic 4 | Gains Story 4.4 (beneficiary export, formerly 3.4). It depends on Epic 3 for the beneficiary session, and nothing points back, so the loop is gone. PDFs label the snapshot figures as purchase price (R8). |

### Stories (old key → new)

| Old | New | Change |
|---|---|---|
| — | **3.1 Activation snapshot integrity** | new (R4) |
| — | **3.2 Estate scope & executor replacement** | new (R6, R7, R8) |
| 3.1 Beneficiary scoped link generation | **3.3** | the executor issues links from the portal; a link is good for one exchange and expires after 7 days if unused |
| 3.2 Beneficiary scoped access portal | **3.4** | the link is exchanged once for a 30-day beneficiary session; pages under `/estate/beneficiary/` carry no token |
| 3.3 Beneficiary item detail view | **3.5** | session-based URL; executor-portal patterns |
| 3.4 Beneficiary personal export | **4.4** | moved after 4.1 |

### Artifacts

- **PRD** (`prd.md`):
  - `:82` and `:221`: separate the beneficiary link (single-use exchange) from the executor code (expires after 72 hours if unused, then valid until revoked).
  - FR39 is unchanged: R4 brings the code into line with it.
- **Epics** (`epics-estate-legacy.md`): every edit listed in section 4.
- **Architecture / UX:** there are no Estate & Legacy architecture or UX documents, so nothing to update.
- **Operations:** a Cloudflare Access bypass for `/estate/portal/*` and `/estate/beneficiary/*` is recorded as a release gate (decided 2026-10-27). It stays as the open action item `epic-2-retro-item-3-…` in `sprint-status.yaml`.
- **Code impact:**
  - Story 3.1 adds a migration with backfill.
  - Story 3.2 changes `activate_estate_plan`, the portal selectors, the owner estate dashboard selector, `executor_view`, and the portal templates.
  - Executor-portal patterns are reused for beneficiaries: separate session keys, `require_safe`, logging after render.

## 3. Recommended approach

**Direct adjustment (option 1).** Nothing completed needs a rollback, and the MVP isn't affected. Every PRD capability keeps its owning story. The R4–R8 code changes become two small Epic 3 stories, so they land before beneficiaries or PDFs rely on snapshots and estate scope.

- **Risk: low to medium.** The main risk is the Story 3.1 migration (backfilling `token` and `item_name` on existing snapshots). Production has no activations (owner confirmed on 2026-10-26), so the backfill only matters in dev and test.
- **Alternatives considered:**
  - Reopening Epic 2 for R4–R8. Rejected: Epic 2 is closed with a verdict, and Epic 3 is the first story that depends on this work.
  - Folding R4–R8 into the beneficiary stories. Rejected: it mixes a migration with new feature surface.

## 4. Detailed change proposals (epics-estate-legacy.md unless noted)

### 4.1 Epic 2: wording and technical notes (as-built)

**E2-a. Epic 2 intro, `:431`**
- OLD: "...to generate a one-time executor access code and lock a valuation snapshot."
- NEW: "...to generate an executor access code (it expires after 72 hours if never used; once used it stays valid until the owner revokes it) and lock a valuation snapshot."
- Rationale: R5, keep as built.

**E2-b. Epic 2 NFR lists, `:181` vs `:434`**
- Make both read: **NFR2, NFR5, NFR6, NFR7, NFR9, NFR10, NFR11, NFR13, NFR14, NFR17**.
- Rationale: the two lists disagree. Epic 2 doesn't touch beneficiaries, so NFR3 and NFR12 belong to Epic 3.

**E2-c. Story 2.1 AC, `:455`**
- OLD: "a cryptographically secure 32-character alphanumeric code is generated using Python `secrets.token_urlsafe()`"
- NEW: "a cryptographically secure code is generated with `secrets.token_urlsafe(32)` (43 URL-safe characters)"

**E2-d. Story 2.1 technical note, `:474`**
- OLD: "`owner OneToOneField(User CASCADE)`"
- NEW: "`owner ForeignKey(User CASCADE)`. Deactivated tokens are kept for the audit trail, so an owner has several tokens and at most one is active."

**E2-e. Story 2.1 technical note: raw token**
- OLD: "Raw token returned from service function, stored nowhere — displayed once in view"
- NEW: "The raw token is returned once from the service and stored only as its SHA-256 hash. It reaches the success page in a signed, HttpOnly, browser-session cookie scoped to that page, which reads it for at most 10 minutes. The page is `never_cache` and shows the code only while it matches the active token. (Changed by the Epic 2 retro fixes, PR #30.)"

**E2-f. Story 2.3 technical notes, `:610-611`**
- OLD: "`get_executor_portfolio_context(owner_user)` ... latest `ValuationSnapshot` per item ... in 3 ORM queries" and "standalone (no `{% extends %}`)"
- NEW: "`get_executor_portfolio_context(owner, token)`, 2 ORM queries. It reads the activation snapshots for the session's token (from Story 3.1, by `token`; previously `created_at >= token.issued_at`). Templates extend `estate/portal/_base.html`."

**E2-g. Story 2.4 technical notes, `:646-648`**
- OLD: "`DynamicCollectionItem.objects.get(pk=item_id, owner=session_owner)`", "`get_executor_item_detail_context(item, owner)`", "standalone"
- NEW:
  - `get_executor_item(owner, item_id)` returns the item or `None`, and the view raises 404.
  - `get_executor_item_detail_context(owner, token, item_id)` runs 4 queries and also returns service records and valuation history (FR23).
  - Photos are served by `/estate/portal/items/<id>/photo/` (`private, no-store`).
  - The template extends `_base.html`.

**E2-h. Epic 2 operational note** (new paragraph after the readiness fixes, `:436`)
- NEW: "**Release gate (decided 2026-10-27):** before the first real executor code or beneficiary link is handed out, the owner adds a Cloudflare Access bypass for `/estate/portal/*` and `/estate/beneficiary/*`. Without it, recipients who have no Access login can only reach the portal on the LAN."

### 4.2 Epic 3: header and new stories

**E3-a. Epic List entry and Epic 3 header, `:186-191` and `:652-657`**
- NEW intro: "After activation, the executor issues a unique link for each beneficiary from the portal. The beneficiary uses the link once to start a 30-day session, and sees only their designated items, enforced at the ORM query level. Epic 3 first hardens the activation snapshot and estate scope that beneficiaries and the Epic 4 PDFs depend on."
- **FRs:** FR19, FR20, FR21, FR28, FR29. FR30 moves to Epic 4.
- **NFRs:** NFR3, NFR8, NFR9, NFR10, NFR12, NFR14, NFR17. NFR15, NFR18 and NFR19 move to Epic 1, where they were met. NFR19 also applies to Story 3.1's migration.
- **Dependency:** Epic 2.
- This also removes the stray "FR42 (partial — beneficiary data isolation)": FR42 is the profile card.

**E3-b. NEW Story 3.1: Activation Snapshot Integrity** (R4)

> As an estate planner, I want each activation's valuation snapshot tied to the code it was taken for and kept even if I later delete an item, so that my executor and the estate PDF always show the values that were locked at activation (FR38, FR39, NFR17).
>
> **AC:**
> - Given an activation, when snapshots are created, then each row has `token` set to the new `EstateAccessToken`, and `item_name` copied from the item.
> - Given an item is deleted after activation, when the executor opens the dashboard, then the item's activation value is still counted in "value at activation". The item appears as "Removed after activation" with its stored name, and it has no detail link.
> - Given the portfolio and item-detail selectors, when they read "value at activation", then both filter `snapshot_trigger="ESTATE_ACTIVATION", token=<session token>`. There's no timestamp matching, and the two pages always agree.
> - Given existing snapshots, when the migration runs, then `token` is backfilled to the token issued at the same activation (`created_at >= issued_at`, before the next token's `issued_at`), and `item_name` comes from the item. A reverse migration is provided (NFR19).
> - Quality gate passes.
>
> **Technical notes:**
> - Fields: `ValuationSnapshot.token FK(EstateAccessToken, SET_NULL, null=True)`, `item FK → SET_NULL null=True`, `item_name CharField(200)`.
> - There are still no `update()` or `delete()` calls on snapshots. `SET_NULL` is the only change Django makes to a row.

**E3-c. NEW Story 3.2: Estate Scope & Executor Replacement** (R6, R7, R8)

> As an estate planner, I want the estate to contain only the collections I still keep, and replacing my executor to cut off the previous one, so that what my executor sees matches my intentions.
>
> **AC:**
> - Given a soft-deleted collection (`CollectionType.is_active=False`), when the owner activates, opens the estate dashboard, or the executor opens the portal or an item, then its items are excluded: no snapshot, not listed, item detail returns 404. This applies to `activate_estate_plan`, `get_estate_dashboard_context`, `get_executor_portfolio_context` and `get_executor_item`. Beneficiary views and PDFs inherit it.
> - Given an active executor code, when the owner saves the executor form with a different **name**, then the page first asks for confirmation ("this revokes the current access code"). On save, the code is revoked and `TOKEN_REVOKED` is logged. A contact-only edit keeps the code.
> - Given the executor portal, when snapshot figures render, then they are labelled "Purchase price" and "Value minus purchase price" (not "Cost basis" and "Equity"). The data is unchanged.
> - Quality gate passes.

### 4.3 Epic 3: beneficiary stories (renumbered and rewritten)

**E3-d. Story 3.1 → 3.3: Beneficiary Link Generation (executor)**
- **User:** OLD "As an estate planner" → NEW "As an executor, I want to issue a unique access link for each designated beneficiary from the portal".
- **AC:** OLD "owner visits `/estate/beneficiaries/`" → NEW:
  - The executor dashboard lists every beneficiary that has at least one designated item, with link status: "No link", "Issued — not yet opened (expires <date>)", "Opened <date>" or "Revoked".
  - "Issue link" sends a POST to `/estate/portal/beneficiaries/<id>/link/`. This is the portal's first state-changing view, an explicit exception to its safe-methods rule (FR27 still holds: no estate or asset data changes). It needs CSRF.
  - The URL `https://<PUBLIC_BASE_URL>/estate/beneficiary/claim/<raw_token>/` is shown once, using the same one-shot cookie pattern as the activation code.
  - Issuing again deactivates the previous link.
  - The executor can revoke a link.
  - The owner's activity panel lists `LINK_ISSUED`, `LINK_REVOKED` and `LINK_CLAIMED` as security events. The two event lists are kept complete by the existing test.
- **Technical notes:**
  - `BeneficiaryAccessLink`: `beneficiary FK(CASCADE)` (FK, not OneToOne, so deactivated links stay for audit, the same lesson as `EstateAccessToken`), `owner FK`, `issued_by_token FK(EstateAccessToken SET_NULL)`, `link_token_hash`, `issued_at`, `expires_at = issued_at + 7 days`, `claimed_at null`, `is_active`.
  - At most one active link per beneficiary, enforced in the service.
  - A link is only usable while the issuing executor token is usable.

**E3-e. Story 3.2 → 3.4: Beneficiary Portal (session)**
- **AC:** OLD "Given beneficiary accesses `/estate/beneficiary/<token>/`" → NEW:
  - `GET /estate/beneficiary/claim/<token>/` checks the hash with `compare_digest` and checks that the link is active, unclaimed, unexpired, and its issuing token usable.
  - On success it sets `claimed_at`, starts a session with the keys `estate_beneficiary_link_id` / `estate_beneficiary_owner_id` (separate from the executor and owner keys, NFR9), logs `LINK_CLAIMED`, and redirects to `/estate/beneficiary/`.
  - A second claim of the same link returns the generic 404 (NFR8 single-use). The beneficiary asks the executor to reissue.
  - A `beneficiary_required` decorator re-checks the link on every request (revoke takes effect on the next request) and uses a 30-day sliding expiry and `never_cache`.
  - `/estate/beneficiary/` lists only items whose `BeneficiaryAssignment.beneficiary` is the session's beneficiary. Each view logs `BENEFICIARY_VIEW`.
- **Technical notes:** the old "token in every URL" notes are replaced by the claim-then-session flow. `resolve_beneficiary_link(token)` is replaced by `claim_beneficiary_link(raw, request)` and the decorator.

**E3-f. Story 3.3 → 3.5: Beneficiary Item Detail**
- URL: OLD `/estate/beneficiary/<token>/items/<item_id>/` → NEW `/estate/beneficiary/items/<item_id>/`, behind `beneficiary_required`.
- The page shows what FR29 lists: current value, purchase history, service records, photos (through a beneficiary photo route) and the conditional note. The snapshot rows are labelled as in Story 3.2.
- An item not assigned to the session's beneficiary returns 404.

### 4.4 Epic 4

**E4-a. Epic 4 header, `:797-802`**
- FRs: FR30, FR31, FR32, FR33, FR34.
- Dependency: Epic 2 (snapshots) and Epic 3 (Story 3.1 snapshot integrity, Story 3.4 beneficiary session). Nothing depends back on Epic 4.

**E4-b. Story 4.1: PDF Rendering Service**
- Table columns: OLD "Name | Collection | Beneficiary | Snapshot Value | Cost Basis | Equity | Note" → NEW "Name | Collection | Beneficiary | Value at activation | Purchase price | Value minus purchase price | Note" (R8).
- `render_beneficiary_pdf(link)` takes the beneficiary's session link.

**E4-c. NEW Story 4.4: Beneficiary Personal Export (formerly 3.4)**
- The content of the old 3.4 ACs is kept.
- The URL becomes `/estate/beneficiary/export/`, behind `beneficiary_required`.
- Each export is logged (FR33).
- The PDF comes from `render_beneficiary_pdf` (4.1).

**E4-d. Story 4.2 technical note**
- Add: "Executor PDF uses the session token's snapshot set (Story 3.1). Soft-deleted collections are excluded (Story 3.2). Items removed after activation are listed by their stored name."

### 4.5 Final validation section

**E5-a. FR coverage map:** replace the table with one keyed to the PRD's FR numbers and titles:
- FR1–3 → 1.2
- FR4 → 2.1
- FR5–6 → 1.4
- FR7–8 → 1.1
- FR9–10 merged → FR11
- FR11–14 → 1.3
- FR15 → 2.1
- FR16–18 → 2.2
- FR19 → 3.3
- FR20 → 3.4
- FR21 → 3.4
- FR22 → 2.3
- FR23 → 2.4
- FR24–25 → 2.3
- FR26 → 2.3/2.4
- FR27 → 2.2–2.4
- FR28 → 3.4
- FR29 → 3.5
- FR30 → 4.4
- FR31–32 → 4.1/4.2
- FR33 → 4.2/4.4
- FR34 → 4.2
- FR35 → 1.3
- FR36–37 → 2.3
- FR38 → 2.1 + 3.1
- FR39 → 2.1 + 3.1
- FR40 → 1.3
- FR41 → 1.5
- FR42–43 → 1.5

**E5-b. Models list:** `BeneficiaryAccessLink` moves to Story 3.3. Add "`ValuationSnapshot` gains `token` and `item_name` in Story 3.1".

**E5-c. Security constraints:**
- OLD "Valuation snapshots: append-only — no UPDATE or DELETE after creation"
- NEW "... no UPDATE or DELETE issued by the app. Item deletion nulls `item` and keeps the row (Story 3.1)."

### 4.6 PRD (prd.md)

**P-a. `:82`**
- OLD "Access credentials are single-use, time-limited, and cryptographically non-guessable"
- NEW "Access credentials are cryptographically non-guessable and revocable. Beneficiary links are single-use (exchanged for a session). Executor codes expire after 72 hours if unused."

**P-b. `:221`**
- OLD "...single-use where possible, and revocable by owner at any time"
- NEW "...beneficiary links single-use; executor codes expire if unused; all revocable by the owner, and beneficiary links by the executor too."

### 4.7 Sprint status (applied after approval)

Development keys:
- New: `3-1-activation-snapshot-integrity`, `3-2-estate-scope-executor-replacement`.
- Renamed: `3-3-beneficiary-link-generation-executor`, `3-4-beneficiary-portal-session`, `3-5-beneficiary-item-detail-view`, `4-4-beneficiary-personal-export`.
- Removed: the old `3-1…3-4` keys.
- All of these are `backlog`.

Retro action items:
- Mark `epic-2-retro-item-1-…` (decisions) and `epic-2-retro-item-2-…` (reconcile notes) `done` once these edits land.
- `epic-2-retro-item-3-…` (Cloudflare release gate) stays open.

## 5. Implementation handoff

- **Scope: Moderate.**
- **Who does what:**
  - **This session (PO/Dev):** apply sections 4.1–4.7 on branch `docs/estate-correct-course-epic3` and open a docs PR.
  - **Developer (`bmad-build`):** Stories 3.1 → 3.2 → 3.3 → 3.4 → 3.5, then Epic 4.
  - **Owner (Zaigner77):** the Cloudflare Access bypass before the first real code or link is handed out.
- **Success criteria:**
  - The epics file and PRD have no conflicts left between FR19/NFR8 and the stories.
  - The FR map matches the PRD's numbering.
  - Epic 3 doesn't depend on Epic 4.
  - Running `bmad-sprint-planning` against the edited epics produces the keys in 4.7 without orphans.
  - Retro action items 1 and 2 are closed.
- **Choice made in this proposal (change it before approving if you like):** an unused beneficiary link expires after **7 days** (the executor code uses 72 hours). Links are often sent by email to people who may not open them right away.
