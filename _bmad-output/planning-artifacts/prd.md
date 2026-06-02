---
stepsCompleted: [step-01-init, step-02-discovery, step-02b-vision, step-02c-executive-summary, step-03-success, step-04-journeys, step-05-domain, step-06-innovation, step-07-project-type, step-08-scoping, step-09-functional, step-10-nonfunctional, step-11-polish, step-12-complete]
status: complete
completedAt: '2026-05-29'
inputDocuments:
  - _bmad/_memory/project-context.md
  - docs/IMPLEMENTATION_PLAN.md
  - docs/SERVICE_RECORDS_GUIDE.md
  - docs/UPGRADES_KANBAN_GUIDE.md
  - docs/UX-enhancement.md
  - docs/schemas/FIELD_TYPES.md
classification:
  projectType: web_app
  domain: legaltech_personal_estate
  complexity: high
  projectContext: brownfield
workflowType: prd
project: my_garage
author: Zaigner77
date: '2026-05-29'
---

# Product Requirements Document — my_garage

**Feature:** Estate & Legacy
**Author:** Zaigner77
**Date:** 2026-05-29

---

## Executive Summary

my_garage is a Django 5.2 personal asset management platform for collectors tracking vehicles, timepieces, and user-defined collections as financial investments. This PRD defines the **Estate & Legacy** feature — a trust and estate planning layer that makes every item in a collector's portfolio discoverable, valued, documented, and transferable at the owner's time of death.

The feature solves a structural gap in estate execution for physical collections: heirs and executors have no reliable way to discover what exists, establish what it's worth, or cleanly assign items per the owner's wishes. my_garage already holds the complete picture — purchase history, valuation timelines, service records, photos, and provenance — for every asset. The Estate & Legacy feature attaches legal intent to that existing data: each item can be designated to a named beneficiary, and the entire portfolio can be administered by a designated executor with controlled, auditable access.

**Tagline:** *Keep your collection current and forever.*

**Classification:** Web application (brownfield) · Personal estate planning / legaltech-adjacent · High complexity (multi-role access control, sensitive PII, contingent access triggers) · Django 5.2 + FastAPI platform · Phase 1 MVP → Phase 2 full suite → Phase 3 legal integration.

### What Makes This Special

No estate planning tool has the asset-level richness that my_garage already maintains. Competitors (Everplans, Trust & Will, attorney-managed inventories) require owners to manually describe and value each item — a snapshot that goes stale. my_garage's estate layer is *live*: valuations update automatically, service records accumulate, and the inventory stays current without additional effort. When a beneficiary or executor gains access, they receive a complete, date-of-access snapshot of every asset — current market value, full cost basis, condition history — not a spreadsheet filled out years ago.

**Core insight: the hardest problem in estate execution for physical collections is discovery, not distribution.** Once heirs know exactly what exists and what it's worth, the legal execution becomes tractable. This feature solves discovery completely.

---

## Success Criteria

### User Success

**Owner (estate planner):**
- Designates a beneficiary for every asset in their portfolio in a single session
- Assigns a trusted executor to their full account with a single action
- Returns to update beneficiary assignments after adding new assets (living estate plan behavior)

**Executor:**
- Activates access and navigates the full portfolio without external help or documentation
- Receives a complete, dated snapshot of every asset — current market value, purchase history, cost basis, service records, photos
- Exports a court-ready PDF inventory in one action

**Beneficiary:**
- Sees only their designated items — no access to assets assigned to others
- Understands the value, history, and provenance of each designated item without contacting anyone else

### Business Success

- **Setup adoption:** ≥50% of active users designate at least one beneficiary within 90 days of feature launch
- **Completion rate:** ≥30% of users who begin beneficiary setup assign beneficiaries to all items
- **Living plan behavior:** ≥40% of new asset additions trigger a beneficiary update within 30 days
- **Executor designation:** ≥25% of active users designate an executor
- **Zero failure-mode executions:** No executor or beneficiary unable to access what they needed due to a feature deficiency

**Failure signals:** Estate plan goes stale relative to collection · Executor cannot navigate or export the inventory · Beneficiary contacts owner asking "what do I do with this?"

### Technical Success

- Access control is strictly scoped — no cross-contamination between beneficiaries, no accidental full-portfolio exposure
- Valuation snapshot captures exact `current_market_value` for all assets at activation time with immutable audit trail
- PDF export includes all assets, valuations, photos, cost basis, and beneficiary assignments
- Access credentials are single-use, time-limited, and cryptographically non-guessable
- Activating estate access never modifies, deletes, or alters the owner's original records

### Measurable Outcomes

| Outcome | Target | Timeframe |
|---|---|---|
| Users with ≥1 beneficiary assigned | 50% of active users | 90 days post-launch |
| Users with all items assigned | 30% of users who begin setup | 90 days post-launch |
| Executor designations | 25% of active users | 90 days post-launch |
| Estate plan update after new asset | 40% of new asset additions | Ongoing |
| Successful executor access activations | 100% (zero failures) | All time |
| PDF export generation without error | 99.9% success rate | All time |

---

## Product Scope

### MVP — Phase 1

Solves the core discovery problem end-to-end for a single owner–executor–beneficiary flow:

- `Beneficiary` model: name, relationship, contact info, optional conditional note per assignment
- Per-item beneficiary assignment for all asset types (Vehicle, Timepiece, DynamicCollectionItem)
- Single executor designation per user account with view-only portfolio access
- Manual estate access activation by owner
- Immutable valuation snapshot at access activation
- Estate inventory PDF export (all assets, valuations, beneficiary assignments, cost basis)
- Executor read-only portal: full portfolio view, item detail, export capability
- Beneficiary scoped view: designated items only

### Growth Features — Phase 2

- Inactivity dead man's switch (configurable 90/180/365 days → owner ping → executor notify)
- Multi-beneficiary splits with percentage allocation per item
- Backup executor designation
- Emergency access code generation (printable, for storage with physical will)
- Charitable/institutional bequest designation
- Storage and physical location fields on all asset types
- Unassigned asset reminder notifications (Celery Beat)
- "Estate completeness" dashboard indicator

### Vision — Phase 3

- Death certificate upload + verification workflow for executor access activation
- Legal document attachment linking (will, trust, POA) per item or full estate
- Attorney read-only share link (time-limited, no account required)
- Time-locked beneficiary assignments (release date condition)
- External estate attorney / trust administrator integration hooks

---

## User Journeys

### Journey 1: The Collector Prepares — Marcus Sets Up His Estate Plan

*Primary User / Happy Path*

Marcus is 58, a lifelong car enthusiast and watch collector. He has three vehicles, eleven timepieces, and a growing bourbon collection in my_garage — all meticulously catalogued with service records, valuations, and photos. His estate attorney recently asked him to prepare an asset inventory for his will, and Marcus realized that while he knows exactly what everything is worth, his wife and two adult children have no idea.

He opens my_garage and notices a new **"Estate & Legacy"** section in the sidebar. The system walks him through two setup steps: first, designating his oldest son Daniel as **executor**. Then, item by item, he works through his collection. The 1972 Porsche 911 goes to Daniel. The AP Royal Oak goes to his daughter Priya. The bourbon collection splits equally. For his daily driver, he adds a note: *"Sell at market value, split proceeds between the kids."*

Forty minutes later, Marcus is done. He feels relief — for the first time, the collection he's spent decades building has a plan. He prints the estate access code and tucks it with his will at his attorney's office.

Six weeks later, when he picks up a vintage Omega Seamaster, it takes three minutes to assign it to Priya. The estate plan stays current.

**Capabilities revealed:** Estate setup UI, executor designation, per-item assignment, conditional notes, access code generation, PDF export, return/update flow on new asset addition.

---

### Journey 2: The Executor Activates — Daniel Faces the Unthinkable

*Secondary User / Executor Access Path*

Daniel is 34 when his father Marcus passes unexpectedly. Amid grief and logistics, Daniel's attorney hands him a printed card from Marcus's estate files: *"my_garage Estate Access — Executor Code: [code]"* and a URL.

Daniel has never used my_garage. He visits the link, enters the code, and is in within two minutes. The system presents Marcus's complete portfolio — 15 assets across three categories, each with current market value, full purchase and service history, photos, and a designated beneficiary. Two items have no beneficiary — rims Marcus added after setup. Daniel flags those for probate.

He clicks **"Export Estate Inventory"** and receives a dated PDF. He sends it to the estate attorney. The attorney's response: *"This is the cleanest inventory I've seen in 30 years of practice."*

**Capabilities revealed:** Code-based access (no account required), read-only portfolio portal, beneficiary assignment visibility, unassigned item flagging, PDF export, storage/location fields.

---

### Journey 3: The Beneficiary Discovers Her Legacy — Priya Gets the Call

*Secondary User / Beneficiary Scoped Access*

Priya is 31 and lives across the country. She knew her father collected watches but never paid close attention. Daniel sends her an access link from the executor portal tied specifically to her designated items.

Priya sees **three items**: the AP Royal Oak, a vintage Rolex Datejust, and a note: *"The Datejust was the first watch I ever bought with my own money. I always meant to tell you the story."*

Each watch has its full history — when Marcus bought it, what he paid, service records, current estimated value, photos. Priya exports her personal inventory, contacts an insurer, and schedules a meeting with an estate jeweler — all from the information in my_garage.

**Capabilities revealed:** Beneficiary-scoped access (designated items only), item detail with full history, personal export, owner notes per assignment.

---

### Journey 4: The Gap in the Plan — Marcus Forgot One

*Primary User / Edge Case: Unassigned Asset at Activation*

Marcus added a 2021 BMW M3 eight months after completing his estate plan and forgot to assign it. When Daniel activates executor access, the BMW M3 appears with a **yellow "Unassigned"** badge. The system surfaces it clearly: *"These assets have no beneficiary designation. They will need to be handled through the probate process."*

The system had sent Marcus two quiet reminders — he dismissed both. The gap was his choice, not a system failure.

**Capabilities revealed:** Unassigned asset detection and surfacing, owner reminder notifications (Phase 2), probate fallback communication, "add asset → assign beneficiary" prompt flow.

---

### Journey Requirements Summary

| Journey | Core Capabilities Required |
|---|---|
| Marcus — Setup | Estate setup UI, executor designation, per-item assignment, conditional notes, access code gen, PDF export |
| Daniel — Executor | Code-based access, read-only portal, unassigned item flagging, PDF export, storage fields |
| Priya — Beneficiary | Scoped access (assigned items only), item detail + history, owner notes, personal export |
| Marcus — Edge Case | Unassigned asset detection, owner reminders (Phase 2), executor unassigned-item surfacing |

---

## Domain-Specific Requirements

### Privacy & PII Handling

- Beneficiary PII (name, contact, relationship) is stored only within the owner's account — never shared across users or used for platform analytics
- Beneficiary contact information is used solely for access delivery — not for platform communication
- Owner can delete all beneficiary records at any time with full cascade (invitations revoked, access terminated)
- Estate access logs are retained for the lifetime of the owner account and excluded from routine cleanup cycles

### Data Durability & Integrity

- Estate plan records are append-preferred — edits create audit trail entries rather than silent overwrites
- Valuation snapshots at estate access activation are immutable — no modification or deletion permitted after lock
- PDF export records (date, asset valuations, assignments) are stored as read-only audit entries
- Owner account deletion requires explicit confirmation that estate plan and beneficiary data will be permanently destroyed — no silent cascade

### Access Control & Security

- Executor and beneficiary access credentials are cryptographically random, single-use where possible, and revocable by owner at any time
- Executor sessions are read-only — no write operations permitted on any asset record
- Beneficiary access is scoped at the ORM level — not UI-level hiding
- All executor and beneficiary access events are logged with timestamp, IP, and action type

### Legal Admissibility Considerations

- PDF estate inventory export includes: generation date/time (UTC), owner identity, valuation date and source, per-item purchase price / current market value / cost basis / beneficiary name and relationship, and footer: *"Generated by my_garage personal asset management platform — for estate planning reference purposes"*
- The platform makes no legal representations — exports are reference documents, not legal instruments. Disclaimer required on all estate-adjacent UI and exports.

### Risk Mitigations

| Risk | Mitigation |
|---|---|
| Owner dies before estate plan setup | Inactivity dead man's switch (Phase 2) + prominent onboarding prompt |
| Executor code lost or stolen | Single-use codes; owner can regenerate and revoke |
| Beneficiary data exposed to wrong person | ORM-level row filtering on every request |
| Estate plan goes stale | Unassigned asset badge; Phase 2 reminder notifications |
| PDF export used as legal instrument | Prominent disclaimer on all exports |
| Beneficiary data retained after owner's death | Executor account expires 12 months after activation (owner-configurable) |

---

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. The Living Estate Plan**
Every estate planning tool produces a static snapshot. my_garage's estate layer is structurally different: embedded in an active asset management platform, the estate plan updates automatically as the collection evolves. Valuations refresh on schedule. Service records accumulate. When an owner adds a new asset, the system prompts for beneficiary assignment immediately. The estate plan is never more than one action out of date. No competitor achieves this because no competitor is also the owner's asset management system.

**2. Asset-Rich Handover**
Existing estate inventory tools capture name, estimated value, and location. my_garage's handover includes full purchase history, cost basis, service and maintenance records, condition assessments, photos, AI-generated valuations, and owner personal notes. A beneficiary receiving a watch receives everything the owner ever recorded about that object.

**3. Discovery-First Estate Planning**
The conventional framing is distribution: *who gets what*. The actual hard problem for physical collections is discovery: *what exists, what is it worth, where is it*. my_garage solves discovery completely as a byproduct of normal platform use. Distribution (beneficiary assignment) becomes a lightweight layer on top of an already-solved discovery problem.

### Competitive Landscape

| Competitor | Inventory Richness | Auto-Updating | Asset-Native |
|---|---|---|---|
| Everplans | Low (text fields) | No | No |
| Trust & Will | None (legal docs only) | No | No |
| Attorney inventory | None (client-provided) | No | No |
| Spreadsheet | Manual | No | No |
| **my_garage Estate** | **High (full history)** | **Yes** | **Yes** |

The gap is structural. Competitors can't close it without becoming asset management platforms themselves.

### Validation Approach

- **Executor usability test:** Can a person who has never used my_garage navigate the portfolio, identify all assets, and export the inventory within 15 minutes of receiving an access code? Target: 90% success rate.
- **Living plan behavior:** Do owners return to update assignments after adding new assets, unprompted? Target: ≥40% within 30 days.
- **Estate plan completeness:** % of users who begin beneficiary setup and assign all items before session end.

### Innovation Risks

| Risk | Mitigation |
|---|---|
| Owners treat estate setup as one-time task | Proactive unassigned-asset reminders; "Estate completeness" indicator on dashboard |
| Executor unfamiliar with platform abandons onboarding | Code-only access, no account required; executor portal is fully self-contained |
| Asset-rich data overwhelming non-collector beneficiaries | Beneficiary view is simplified — value, photo, owner note, one-click export |

---

## Project Scoping

### MVP Strategy

**Approach:** Experience MVP — minimum needed for an owner to feel their legacy is genuinely secured. Proves the core value proposition end-to-end: owner sets up estate plan → executor gains access → executor exports inventory.

**Resource profile:** Solo developer. Scope decisions favor sequential simplicity.

**MVP gate:** *Can an executor who has never used my_garage access the full portfolio, understand every asset's value, and export a complete inventory within 15 minutes of receiving an access code?*

### MVP Capability Set (Phase 1)

**Journeys fully supported:** Marcus setup · Daniel executor activation · Priya beneficiary view · Unassigned asset detection (no reminder notifications — Phase 2)

| Capability | Rationale |
|---|---|
| `Beneficiary` model (name, relationship, contact, note) | Foundation of all estate assignment logic |
| Per-item beneficiary assignment — Vehicle, Timepiece, DynamicCollectionItem | Core distribution mechanic |
| Single executor designation per account | Enables estate administration |
| Manual estate access activation by owner | Simplest, most legally defensible trigger |
| Valuation snapshot at activation (immutable) | Date-of-death value record |
| `EstateAccessToken` — code-based executor access, no account required | Executor onboarding must be frictionless |
| Executor read-only portal — full portfolio, item detail, beneficiary assignments | Core executor experience |
| Beneficiary scoped view — designated items only, ORM-filtered | Core beneficiary experience |
| Unassigned asset detection + badge in executor view | Executor knows what needs probate |
| Estate inventory PDF export | Court-ready handover document |

**Deferred from MVP:** Inactivity dead man's switch · Multi-beneficiary splits · Printable emergency access card · Unassigned asset reminder notifications · Storage/location fields

### Risk Mitigation

**Technical:**

| Risk | Likelihood | Mitigation |
|---|---|---|
| Token-based executor session conflicting with Django auth | Medium | Separate session key + middleware; executor views decorator-gated |
| PDF generation quality / legal format | Medium | Prototype `weasyprint` early against sample data before full build |
| ORM-level beneficiary scoping leaking data | Low | Explicit QuerySet filter on every beneficiary view |

**Market:**

| Risk | Mitigation |
|---|---|
| Owners never return to update estate plan | Phase 2 reminders; Phase 1 unassigned-asset badge creates natural return trigger |
| Executor abandons onboarding | Code-only access, no account creation; portal is self-contained |

**Resource (Solo Developer):**

| Risk | Contingency |
|---|---|
| PDF generation overruns | Ship Phase 1 without PDF; add as Phase 1b patch. Web portal still delivers executor value. |
| Phase 2 scope creep | Hard cutoff: any feature requiring new Celery async infrastructure is Phase 2. |

---

## Web Application Requirements

### Architecture

The Estate & Legacy feature is a brownfield addition to an existing Django 5.2 MPA. All new views use the existing server-rendered template pattern (Tailwind CSS + Alpine.js). No new frontend framework is introduced.

**Three authentication paths:**
1. **Owner** — standard Django session auth (`IsAuthenticated`); estate views filtered by `owner=request.user`
2. **Executor** — token-based; access code maps to `EstateAccessToken` (UUID + expiry); read-only middleware enforces zero write operations; no my_garage account required
3. **Beneficiary** — scoped invitation link from executor portal; maps to `BeneficiaryAccessGrant`; items filtered at ORM level to designated-only; no account required

**Browser support:** Chrome, Firefox, Safari, Edge — last 2 major versions. No IE11.

**SEO:** Not applicable. All estate views are behind auth or token-gated.

**Real-time:** None required for Phase 1. Unassigned asset reminders use existing Celery Beat pattern.

### Responsive Design

- Owner estate management views: desktop-primary, mobile-responsive
- Executor portal: mobile-capable — executor may access in stressful circumstances away from home
- Beneficiary view: mobile-first — beneficiaries likely open access link on phone

### Accessibility

- Executor portal and beneficiary view: **WCAG 2.1 AA** — contrast ratio ≥4.5:1, keyboard-navigable, labelled form fields, descriptive error messages
- Owner estate management views: WCAG 2.1 A (platform standard)

### Implementation Notes

- URL namespace: `/estate/`
- Executor and beneficiary sessions use separate session keys — no collision with owner Django sessions
- PDF generation: `reportlab` or `weasyprint` — new dependency in `pyproject.toml`
- No new DRF API endpoints for Phase 1 — all estate operations are synchronous Django views

---

## Functional Requirements

### Estate Plan Management

- **FR1:** Owner can designate a single executor for their account by name and contact information
- **FR2:** Owner can view their current executor designation and update it at any time
- **FR3:** Owner can remove their executor designation
- **FR4:** Owner can manually activate estate access, granting the designated executor immediate portfolio access
- **FR5:** Owner can view an estate plan completeness summary showing which assets have and have not been assigned a beneficiary
- **FR6:** Owner can view a consolidated list of all beneficiary assignments across their entire portfolio

### Beneficiary Management

- **FR7:** Owner can create a reusable beneficiary profile with name, relationship type, and contact information
- **FR8:** Owner can edit and delete beneficiary profiles
- **FR9:** Owner can assign a beneficiary to any Vehicle in their portfolio
- **FR10:** Owner can assign a beneficiary to any Timepiece in their portfolio
- **FR11:** Owner can assign a beneficiary to any DynamicCollectionItem in any collection
- **FR12:** Owner can add a conditional note to any beneficiary assignment (e.g., "do not sell," "hold in trust")
- **FR13:** Owner can remove or change a beneficiary assignment on any asset at any time
- **FR14:** Owner can designate an asset for charitable or institutional bequest (non-individual beneficiary)

### Estate Access & Security

- **FR15:** System generates a cryptographically random estate access code on owner request
- **FR16:** Executor can activate read-only portfolio access using an access code without creating a my_garage account
- **FR17:** Owner can revoke an executor's access code before or after it has been used
- **FR18:** System logs all executor and beneficiary access events with timestamp and action type
- **FR19:** Executor can generate and share a scoped beneficiary access link for any designated beneficiary
- **FR20:** Beneficiary can access their designated items via a link without creating a my_garage account
- **FR21:** Beneficiary access links are scoped at the data layer — a beneficiary cannot access items designated to other beneficiaries

### Executor Portal

- **FR22:** Executor can view the complete portfolio of all assets across all asset types (Vehicle, Timepiece, all collections)
- **FR23:** Executor can view full item detail for any asset including purchase history, valuation history, service records, photos, and owner notes
- **FR24:** Executor can see which beneficiary each asset is assigned to
- **FR25:** Executor can identify all assets with no beneficiary assignment, with a clear visual indicator
- **FR26:** Executor can view the valuation snapshot captured at the moment estate access was activated
- **FR27:** Executor cannot modify, create, or delete any asset record or estate plan data

### Beneficiary Experience

- **FR28:** Beneficiary can view only the assets specifically designated to them — no other portfolio items are accessible
- **FR29:** Beneficiary can view full item detail for their designated assets including current value, purchase history, service records, photos, and the owner's personal note for that item
- **FR30:** Beneficiary can export a personal inventory of only their designated items

### Estate Inventory Export

- **FR31:** Executor can generate a complete estate inventory PDF covering all assets, their valuations at activation date, cost basis, service history summary, storage location (if provided), and beneficiary assignments
- **FR32:** Generated PDF includes: generation date/time (UTC), owner name, valuation snapshot date, and a legal disclaimer stating the document is for estate planning reference only
- **FR33:** System records each PDF export with generation timestamp for audit purposes
- **FR34:** Executor can regenerate the estate inventory PDF at any time while access is active

### Asset Coverage & Inventory Integrity

- **FR35:** All three asset types (Vehicle, Timepiece, DynamicCollectionItem) support beneficiary assignment through a uniform interface
- **FR36:** Assets added to the portfolio after estate plan setup appear in the executor portal, even if they have no beneficiary assignment
- **FR37:** Unassigned assets are flagged prominently in the executor portal with a clear status indicator

### Valuation Snapshot & Audit Integrity

- **FR38:** System captures an immutable valuation snapshot (current_market_value for all assets) at the exact moment estate access is activated
- **FR39:** Valuation snapshots cannot be modified or deleted after capture
- **FR40:** System maintains a change history for estate plan modifications (assignments created, updated, deleted)
- **FR41:** When an owner deletes their account, all beneficiary PII and estate plan records are permanently destroyed — requires explicit owner confirmation

---

## Non-Functional Requirements

### Performance

- **NFR1:** Estate management page (owner — full asset list with assignment status) loads within 2 seconds for portfolios up to 100 items
- **NFR2:** Executor portal initial load (complete portfolio view) completes within 3 seconds — no pagination; executor must see the complete picture immediately
- **NFR3:** Beneficiary scoped view loads within 2 seconds regardless of total portfolio size (ORM filter applied server-side)
- **NFR4:** PDF estate inventory export completes within 10 seconds for portfolios up to 100 items; larger portfolios handled asynchronously via Celery with a progress indicator
- **NFR5:** Estate access activation (valuation snapshot + token issuance) completes within 5 seconds

### Security

- **NFR6:** All estate access tokens (executor codes, beneficiary links) are generated using cryptographically secure random functions (Python `secrets` module); tokens are never sequential or guessable
- **NFR7:** Executor access tokens expire after 72 hours if unused; activated executor sessions expire after 30 days of inactivity
- **NFR8:** Beneficiary access links are single-use for initial activation; once activated, the beneficiary session is maintained for 30 days
- **NFR9:** Executor and beneficiary sessions use a separate session namespace from owner Django sessions — no session key collision possible
- **NFR10:** Beneficiary data isolation is enforced at the ORM query level on every request — UI-layer filtering alone is insufficient
- **NFR11:** All estate-related access events (token activation, portal views, PDF exports, beneficiary link generation) are written to an immutable audit log
- **NFR12:** Beneficiary PII is stored only within the owner's account and is never transmitted to third parties or used for platform analytics
- **NFR13:** All data in transit encrypted via HTTPS (TLS 1.2 minimum); database-at-rest encryption follows the platform's existing PostgreSQL configuration

### Accessibility

- **NFR14:** Executor portal and beneficiary view meet **WCAG 2.1 AA** — minimum contrast ratio 4.5:1, all interactive elements keyboard-navigable, form fields have associated labels, error messages are descriptive
- **NFR15:** Owner estate management views meet WCAG 2.1 A (platform standard)
- **NFR16:** PDF exports use readable font sizes (minimum 10pt body text) and logical reading order for screen reader compatibility

### Data Reliability & Durability

- **NFR17:** Valuation snapshots are stored in an append-only table — no `UPDATE` or `DELETE` operations permitted after creation
- **NFR18:** Estate plan records (beneficiary assignments, executor designation, access tokens) are excluded from any routine data cleanup, archival, or TTL policies
- **NFR19:** Database migrations affecting estate models must include a rollback script and be tested against production data volume before deployment
- **NFR20:** PDF export records (timestamp, asset count, export hash) are retained for the lifetime of the owner account
