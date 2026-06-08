---
stepsCompleted: [step-01-validate-prerequisites, step-02-design-epics, step-03-epic1-approved, step-03-epic2-approved, step-03-epic3-approved, step-03-epic4-approved, step-04-final-validation]
status: complete
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - CLAUDE.md
project: my_garage
feature: Estate & Legacy
author: Zaigner77
date: '2026-06-07'
---

# my_garage — Estate & Legacy: Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the **Estate & Legacy** feature of my_garage. It decomposes the PRD requirements into implementable epics and stories for a solo developer.

**Architectural reality (brownfield — Phase 5 completed):**

| PRD assumption | Actual codebase |
|---|---|
| Separate `Vehicle`, `Timepiece`, `DynamicCollectionItem` ORM models | All assets are `DynamicCollectionItem` |
| FR9 (Vehicle assignment) and FR10 (Timepiece assignment) separate from FR11 | FR9 + FR10 merged into FR11 — one uniform assignment interface for all DynamicCollectionItem |

**Tech Stack:** Django 5.2, Tailwind CSS (CDN), Alpine.js 3.x, PostgreSQL, existing selector/service/serializer pattern, `secrets` module for token generation, `weasyprint` or `reportlab` for PDF (new dependency).

---

## Requirements Inventory

### Functional Requirements

FR1: Owner can designate a single executor for their account by name and contact information
FR2: Owner can view their current executor designation and update it at any time
FR3: Owner can remove their executor designation
FR4: Owner can manually activate estate access, granting the designated executor immediate portfolio access
FR5: Owner can view an estate plan completeness summary showing which assets have and have not been assigned a beneficiary
FR6: Owner can view a consolidated list of all beneficiary assignments across their entire portfolio
FR7: Owner can create a reusable beneficiary profile with name, relationship type, and contact information
FR8: Owner can edit and delete beneficiary profiles
FR9: [Merged into FR11] — all assets are DynamicCollectionItem; no separate Vehicle path needed
FR10: [Merged into FR11] — all assets are DynamicCollectionItem; no separate Timepiece path needed
FR11: Owner can assign a beneficiary to any DynamicCollectionItem across any collection type
FR12: Owner can add a conditional note to any beneficiary assignment (e.g., "do not sell", "hold in trust")
FR13: Owner can remove or change a beneficiary assignment on any asset at any time
FR14: Owner can designate an asset for charitable or institutional bequest (non-individual beneficiary)
FR15: System generates a cryptographically random estate access code on owner request (Python `secrets` module)
FR16: Executor can activate read-only portfolio access using an access code without creating a my_garage account
FR17: Owner can revoke an executor's access code before or after it has been used
FR18: System logs all executor and beneficiary access events with timestamp and action type
FR19: Executor can generate and share a scoped beneficiary access link for any designated beneficiary
FR20: Beneficiary can access their designated items via a link without creating a my_garage account
FR21: Beneficiary access links are scoped at the ORM data layer — a beneficiary cannot access items designated to other beneficiaries
FR22: Executor can view the complete portfolio of all assets across all collection types
FR23: Executor can view full item detail for any asset including purchase history, valuation history, service records, photos, and owner notes
FR24: Executor can see which beneficiary each asset is assigned to
FR25: Executor can identify all assets with no beneficiary assignment, with a clear visual indicator
FR26: Executor can view the valuation snapshot captured at the moment estate access was activated
FR27: Executor cannot modify, create, or delete any asset record or estate plan data
FR28: Beneficiary can view only the assets specifically designated to them — no other portfolio items accessible
FR29: Beneficiary can view full item detail for their designated assets including current value, purchase history, service records, photos, and the owner's personal note for that item
FR30: Beneficiary can export a personal inventory of only their designated items
FR31: Executor can generate a complete estate inventory PDF covering all assets, valuations at activation date, cost basis, service history summary, and beneficiary assignments
FR32: Generated PDF includes: generation date/time (UTC), owner name, valuation snapshot date, and a legal disclaimer stating the document is for estate planning reference only
FR33: System records each PDF export with generation timestamp for audit purposes
FR34: Executor can regenerate the estate inventory PDF at any time while access is active
FR35: All asset types support beneficiary assignment through a uniform interface (one interface for all DynamicCollectionItem)
FR36: Assets added to the portfolio after estate plan setup appear in the executor portal, even if they have no beneficiary assignment
FR37: Unassigned assets are flagged prominently in the executor portal with a clear status indicator
FR38: System captures an immutable valuation snapshot (current_market_value for all DynamicCollectionItem) at the exact moment estate access is activated
FR39: Valuation snapshots cannot be modified or deleted after capture
FR40: System maintains a change history for estate plan modifications (assignments created, updated, deleted)
FR41: When an owner deletes their account, all beneficiary PII and estate plan records are permanently destroyed — requires explicit owner confirmation
FR42: Profile page (/accounts/profile/) displays an Estate & Legacy status card: whether executor is designated, count of items assigned vs total items, visual completeness indicator, and a link to full estate management
FR43: Profile page provides direct access to executor designation and beneficiary management without requiring navigation to the /estate/ namespace first

### Non-Functional Requirements

NFR1: Estate management page (owner — full asset list with assignment status) loads within 2 seconds for portfolios up to 100 items
NFR2: Executor portal initial load (complete portfolio view) completes within 3 seconds — no pagination; executor must see the complete picture immediately
NFR3: Beneficiary scoped view loads within 2 seconds regardless of total portfolio size (ORM filter applied server-side)
NFR4: PDF estate inventory export completes within 10 seconds for portfolios up to 100 items; larger portfolios handled asynchronously via Celery with a progress indicator
NFR5: Estate access activation (valuation snapshot + token issuance) completes within 5 seconds
NFR6: All estate access tokens (executor codes, beneficiary links) generated using Python `secrets` module — never sequential or guessable
NFR7: Executor access tokens expire after 72 hours if unused; activated executor sessions expire after 30 days of inactivity
NFR8: Beneficiary access links are single-use for initial activation; once activated, the beneficiary session is maintained for 30 days
NFR9: Executor and beneficiary sessions use a separate session namespace from owner Django sessions — no session key collision possible
NFR10: Beneficiary data isolation is enforced at the ORM query level on every request — UI-layer filtering alone is insufficient
NFR11: All estate-related access events (token activation, portal views, PDF exports, beneficiary link generation) are written to an immutable audit log
NFR12: Beneficiary PII is stored only within the owner's account and is never transmitted to third parties or used for platform analytics
NFR13: All data in transit encrypted via HTTPS (TLS 1.2 minimum)
NFR14: Executor portal and beneficiary view meet WCAG 2.1 AA — contrast ratio ≥4.5:1, keyboard-navigable, labelled form fields, descriptive error messages
NFR15: Owner estate management views meet WCAG 2.1 A (platform standard)
NFR16: PDF exports use readable font sizes (minimum 10pt body text) and logical reading order for screen reader compatibility
NFR17: Valuation snapshots stored in append-only table — no UPDATE or DELETE operations permitted after creation
NFR18: Estate plan records excluded from any routine data cleanup, archival, or TTL policies
NFR19: Database migrations affecting estate models must include a rollback script and be tested against production data volume before deployment
NFR20: PDF export records (timestamp, asset count) are retained for the lifetime of the owner account

### Additional Requirements

- **Brownfield Django 5.2 MPA** — server-rendered templates (Tailwind CSS + Alpine.js); no new frontend framework introduced
- **Three auth paths** — Owner (standard Django `SessionAuthentication`), Executor (token-based session using separate key, no account required), Beneficiary (scoped link from executor portal, no account required)
- **URL namespace** — `/estate/` for all estate views; profile page integration at `/accounts/profile/`
- **No new DRF API endpoints** for Phase 1 — all estate operations are synchronous Django views
- **PDF dependency** — `weasyprint` or `reportlab` must be added to `pyproject.toml` / `pixi.toml`
- **All assets are DynamicCollectionItem** — PRD references to separate Vehicle and Timepiece models are legacy; beneficiary assignment uses a single model FK
- **Selector/service pattern** — all ORM reads go through `api/selectors.py`, all writes through `api/services.py`; views never call ORM directly
- **Quality gate** — `pixi run pytest tests/unit/ tests/functional/ -x -q` + `pixi run lint` + `pixi run -- ruff format --check .` must pass after every story
- **Profile page integration** — `src/config/views.py` (`profile` view) and `templates/pages/profile.html` already exist; Estate & Legacy card added in its own dedicated epic
- **Signals pattern** — use Django `post_save`/`post_delete` signals for any reactive cache refresh (established pattern from NFP feature)
- **Token security** — executor and beneficiary tokens use `secrets.token_urlsafe(32)`; stored as hashed values where possible; single-use for initial beneficiary activation
- **Audit log** — estate access events written to a new `EstateAccessLog` model (immutable, no delete); TTL policy explicitly excluded per NFR18

### FR Coverage Map

| FR | Epic | Summary |
|---|---|---|
| FR1 | Epic 1 | Executor designation — create |
| FR2 | Epic 1 | Executor designation — view/update |
| FR3 | Epic 1 | Executor designation — remove |
| FR4 | Epic 2 | Manual estate access activation |
| FR5 | Epic 1 | Estate plan completeness summary |
| FR6 | Epic 1 | Consolidated beneficiary assignment list |
| FR7 | Epic 1 | Beneficiary profile — create |
| FR8 | Epic 1 | Beneficiary profile — edit/delete |
| FR9 | Epic 1 | Merged into FR11 |
| FR10 | Epic 1 | Merged into FR11 |
| FR11 | Epic 1 | Per-item beneficiary assignment — all DynamicCollectionItem |
| FR12 | Epic 1 | Conditional note on assignment |
| FR13 | Epic 1 | Remove/change beneficiary assignment |
| FR14 | Epic 1 | Charitable/institutional bequest designation |
| FR15 | Epic 2 | Cryptographic executor access code generation |
| FR16 | Epic 2 | Executor code-based login (no account) |
| FR17 | Epic 2 | Executor access code revocation |
| FR18 | Epic 2 | Immutable access event audit log |
| FR19 | Epic 3 | Scoped beneficiary link generation (from executor portal) |
| FR20 | Epic 3 | Beneficiary link access (no account) |
| FR21 | Epic 3 | ORM-level beneficiary data isolation |
| FR22 | Epic 2 | Executor — full portfolio view |
| FR23 | Epic 2 | Executor — full item detail |
| FR24 | Epic 2 | Executor — see beneficiary per asset |
| FR25 | Epic 2 | Executor — unassigned asset flagging |
| FR26 | Epic 2 | Executor — valuation snapshot view |
| FR27 | Epic 2 | Executor — enforced read-only |
| FR28 | Epic 3 | Beneficiary — scoped item access only |
| FR29 | Epic 3 | Beneficiary — full item detail with owner note |
| FR30 | Epic 3 | Beneficiary — personal inventory export |
| FR31 | Epic 4 | Full estate inventory PDF (executor) |
| FR32 | Epic 4 | PDF legal disclaimer + metadata |
| FR33 | Epic 4 | PDF export audit record |
| FR34 | Epic 4 | PDF regeneration capability |
| FR35 | Epic 1 | Uniform assignment interface for all asset types |
| FR36 | Epic 2 | Post-setup assets visible in executor portal |
| FR37 | Epic 2 | Unassigned asset badge in executor portal |
| FR38 | Epic 2 | Immutable valuation snapshot at activation |
| FR39 | Epic 2 | Valuation snapshot append-only enforcement |
| FR40 | Epic 1 | Estate plan change history |
| FR41 | Epic 1 | Account deletion — cascade destroy PII |
| FR42 | Epic 1 | Profile page estate status card |
| FR43 | Epic 1 | Profile page — direct access to estate management |

## Epic List

### Epic 1: Estate Plan Foundation — Owner Setup & Profile Integration

The owner can build a complete estate plan: designate an executor, create reusable beneficiary profiles, assign beneficiaries to every item in their portfolio with conditional notes, view plan completeness, and see a live estate status card on their profile page. This epic establishes all Django models and migrations that subsequent epics depend on.

**FRs covered:** FR1, FR2, FR3, FR5, FR6, FR7, FR8, FR11, FR12, FR13, FR14, FR35, FR40, FR41, FR42, FR43
**NFRs covered:** NFR1, NFR15, NFR18, NFR19
**Dependency:** None — standalone foundational epic.

---

### Epic 2: Estate Access — Executor Token, Portal & Valuation Snapshot

The owner can activate estate access and generate a cryptographic code for their executor. The executor can enter that code (no account required), land in a read-only portal showing the full portfolio with a locked valuation snapshot, see beneficiary assignments on every item, and clearly identify unassigned assets. All access events are immutably logged.

**FRs covered:** FR4, FR15, FR16, FR17, FR18, FR22, FR23, FR24, FR25, FR26, FR27, FR36, FR37, FR38, FR39
**NFRs covered:** NFR2, NFR5, NFR6, NFR7, NFR9, NFR10, NFR11, NFR13, NFR14, NFR17
**Dependency:** Epic 1

---

### Epic 3: Beneficiary Scoped Access

The executor can generate a scoped access link for any designated beneficiary. The beneficiary opens that link (no account required), sees only their designated items with full detail including the owner's personal note, and can export their personal inventory — with complete ORM-level data isolation.

**FRs covered:** FR19, FR20, FR21, FR28, FR29, FR30
**NFRs covered:** NFR3, NFR8, NFR9, NFR10, NFR12, NFR14
**Dependency:** Epic 2

---

### Epic 4: Estate Inventory PDF Export

The executor can generate a court-ready estate inventory PDF in one click: all assets with valuation-snapshot values, cost basis, beneficiary assignments, and a legal disclaimer. The beneficiary can export their personal item inventory. Every export is timestamped for audit.

**FRs covered:** FR31, FR32, FR33, FR34
**NFRs covered:** NFR4, NFR16, NFR20
**Dependency:** Epic 2

---

## Epic 1: Estate Plan Foundation — Owner Setup & Profile Integration

The owner can build a complete estate plan: designate an executor, create reusable beneficiary profiles, assign beneficiaries to every item in their portfolio with conditional notes, view plan completeness, and see a live estate status card on their profile page. All Django models this feature requires are created here.

**FRs covered:** FR1, FR2, FR3, FR5, FR6, FR7, FR8, FR11, FR12, FR13, FR14, FR35, FR40, FR41, FR42, FR43
**NFRs covered:** NFR1, NFR15, NFR18, NFR19

---

### Story 1.1: Beneficiary Profile Data Model & CRUD

As an estate planner,
I want to create and manage reusable beneficiary profiles,
So that I can assign the same person to multiple assets without re-entering their details each time.

**Acceptance Criteria:**

**Given** an authenticated owner visits `/estate/beneficiaries/`
**When** the page renders
**Then** all their beneficiary profiles are listed with name, relationship, and contact info
**And** an "Add Beneficiary" button is visible

**Given** owner submits the add form with a valid name and relationship
**When** the form is saved
**Then** a new `Beneficiary` record is created with `owner=request.user`
**And** owner is redirected to the beneficiary list with a success toast

**Given** owner submits the add form with a blank name
**When** form is validated
**Then** a form error is shown and no record is created

**Given** owner clicks delete on a beneficiary and confirms
**When** deletion completes
**Then** the `Beneficiary` record is permanently deleted and removed from the list

**Given** an unauthenticated user visits any `/estate/` URL
**When** the request is received
**Then** they are redirected to `/accounts/login/?next=...`

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes with zero failures
**And** ruff check and ruff format --check report zero errors

**Technical notes:**
- New model `Beneficiary` in `src/my_garage/models.py`: `owner FK(User CASCADE)`, `name CharField(200)`, `relationship CharField(50, choices=[Spouse, Child, Sibling, Parent, Friend, Charity, Other])`, `contact_info TextField(blank=True)`, `notes TextField(blank=True)`, `created_at auto_now_add`
- Cascade delete from User satisfies FR41 at the data layer — beneficiary PII destroyed when account deleted
- `BeneficiaryForm(ModelForm)` in `src/my_garage/forms.py`
- URL namespace `estate:` — new `src/my_garage/estate_urls.py`, mounted in `src/config/urls.py` as `path("estate/", include("my_garage.estate_urls", namespace="estate"))`
- Estate views in `src/my_garage/views.py` or new `src/my_garage/estate_views.py`
- Templates: `src/my_garage/templates/my_garage/estate/` directory
- All views `@login_required`, all queries filter `owner=request.user`

---

### Story 1.2: Executor Designation

As an estate planner,
I want to designate a single trusted executor for my account,
So that one named person can access and administer my complete portfolio when needed.

**Acceptance Criteria:**

**Given** owner visits `/estate/executor/` with no executor designated
**When** the page renders
**Then** an empty state is shown with a form: executor name, contact info
**And** a "Designate Executor" submit button is visible

**Given** owner submits the executor form with a valid name and contact info
**When** the form is saved
**Then** an `EstateExecutor` record is created with `owner=request.user`
**And** success toast: "Executor designated successfully."
**And** the page re-renders showing current executor name, contact, and date designated

**Given** owner has an existing executor and visits `/estate/executor/`
**When** the page renders
**Then** current executor details are displayed
**And** "Update" and "Remove" actions are available

**Given** owner clicks "Remove" and confirms
**When** deletion completes
**Then** the `EstateExecutor` record is deleted and the empty state is shown again

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- New model `EstateExecutor` in `models.py`: `owner OneToOneField(User CASCADE)`, `name CharField(200)`, `contact_info TextField`, `designated_at auto_now_add`, `updated_at auto_now`
- `OneToOneField` enforces exactly one executor per account at ORM level
- `EstateExecutorForm(ModelForm)` in `forms.py`
- Views and URLs in the `estate:` namespace

---

### Story 1.3: Per-Item Beneficiary Assignment & Change History

As an estate planner,
I want to assign a beneficiary to each item in my collection with an optional conditional note,
So that every asset has a clear designated recipient and my wishes are permanently recorded.

**Acceptance Criteria:**

**Given** owner views a collection item detail page (`/collections/<slug>/items/<id>/`)
**When** the page renders
**Then** an "Estate Assignment" section is visible showing the current beneficiary (or "Unassigned")
**And** a dropdown of existing `Beneficiary` profiles is shown
**And** an optional textarea for a conditional note is shown

**Given** owner selects a beneficiary and submits
**When** the assignment is saved
**Then** a `BeneficiaryAssignment` record is created/updated for that item
**And** an `EstateChangeLog` entry is written with `action=ASSIGNED`
**And** a success toast appears

**Given** owner selects charitable designation (`is_charitable=True`) and an org name
**When** the form is submitted
**Then** `is_charitable=True`, `charitable_org` is stored, and `beneficiary FK` is null

**Given** owner removes an assignment
**When** removal is confirmed
**Then** the `BeneficiaryAssignment` record is deleted
**And** an `EstateChangeLog` entry is written with `action=REMOVED`

**Given** a `Beneficiary` profile is deleted after it was assigned to an item
**When** the deletion cascades
**Then** the `BeneficiaryAssignment` record remains (`SET_NULL` on beneficiary FK)
**And** the item appears as "Unassigned" in the estate dashboard

**Given** owner visits `/estate/assign/`
**When** the page renders
**Then** all `DynamicCollectionItem` owned by them are listed with current assignment status
**And** unassigned items display a prominent "Unassigned" badge

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- New model `BeneficiaryAssignment` in `models.py`: `item OneToOneField(DynamicCollectionItem CASCADE)`, `beneficiary FK(Beneficiary SET_NULL null=True blank=True)`, `conditional_note TextField(blank=True)`, `is_charitable BooleanField default=False`, `charitable_org CharField(blank=True)`, `assigned_at auto_now_add`, `updated_at auto_now`
- New model `EstateChangeLog` in `models.py`: `owner FK(User CASCADE)`, `action CharField(choices: ASSIGNED/CHANGED/REMOVED)`, `item_name CharField(200)`, `beneficiary_name CharField(200, blank=True)`, `timestamp auto_now_add` — no update/delete views (append-only)
- Selector `get_item_estate_assignment(item, user)` in `api/selectors.py`
- Service `assign_beneficiary(item, beneficiary, note, is_charitable, org, user)` in `api/services.py`
- Assignment section added to existing `collection_item_detail.html`

---

### Story 1.4: Estate Plan Dashboard & Completeness View

As an estate planner,
I want a dedicated estate dashboard showing my plan's completeness and all assignments in one view,
So that I can immediately see which items are covered and which still need attention.

**Acceptance Criteria:**

**Given** authenticated owner visits `/estate/`
**When** the page renders
**Then** executor designation status is shown (name if designated, or "Not designated" warning)
**And** completeness metric shows "X of Y items assigned" with a visual progress bar
**And** a table lists every `DynamicCollectionItem` with name, collection type, assigned beneficiary or "Unassigned" badge, and conditional note
**And** the last 10 `EstateChangeLog` entries are shown in a recent activity section

**Given** owner has zero items
**When** `/estate/` renders
**Then** completeness shows "No items yet" with no division-by-zero error

**Given** a portfolio has 100 items
**When** the page loads
**Then** the response completes within 2 seconds (NFR1)

**Given** owner clicks "Bulk Assign" CTA
**When** the link is followed
**Then** they land on `/estate/assign/`

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- Selector `get_estate_dashboard_context(user)` in `api/selectors.py`: returns executor, items annotated with assignment status, completeness %, recent log — max 3 ORM queries
- View `estate_dashboard`; URL `path("", ..., name="estate_dashboard")` in `estate_urls.py`
- Template `src/my_garage/templates/my_garage/estate/dashboard.html`

---

### Story 1.5: Profile Page Estate Status Card & Account Deletion Safeguard

As a collector,
I want to see my estate plan status on my profile page and have a confirmed path to delete my account,
So that account management is in one place and my beneficiary data is fully protected if I leave.

**Acceptance Criteria:**

**Given** authenticated owner visits `/accounts/profile/`
**When** the page renders
**Then** an "Estate & Legacy" card is visible showing executor status, items assigned count vs total, and a "Manage Estate Plan →" link to `/estate/`

**Given** owner has no executor designated
**When** the profile page renders
**Then** the estate card shows a warning indicator: "No executor designated"

**Given** owner has all items assigned
**When** the profile page renders
**Then** the estate card shows a completion indicator

**Given** owner expands the "Danger Zone" section on the profile page and clicks "Delete Account"
**When** they confirm in the modal
**Then** a POST to `/accounts/delete/` deletes the `User` record
**And** all `Beneficiary`, `EstateExecutor`, `BeneficiaryAssignment`, `EstateChangeLog` records are cascade-deleted via FK
**And** the owner is logged out and redirected to the home page

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- Update `profile` view in `src/config/views.py`: call `get_estate_dashboard_context(user)`, pass `executor_designated`, `estate_items_total`, `estate_items_assigned`, `estate_completeness_pct` to template
- Add Estate & Legacy card as 4th card in `templates/pages/profile.html`
- Account deletion: `@require_POST @login_required` view in `src/config/views.py`; `path("accounts/delete/", views.delete_account, name="delete_account")` in `src/config/urls.py`
- Confirmation modal: Alpine.js `x-data` / `x-show` pattern consistent with existing modals

---

## Epic 2: Estate Access — Executor Token, Portal & Valuation Snapshot

The owner activates their estate plan to generate a one-time executor access code and lock a valuation snapshot. The executor uses that code to enter a read-only portal (no Django account needed) where they can browse the full portfolio and item detail pages.

**FRs covered:** FR4, FR15, FR16, FR17, FR18, FR22, FR23, FR24, FR25, FR26, FR27, FR36, FR37, FR38, FR39
**NFRs covered:** NFR2, NFR3, NFR5, NFR6, NFR7, NFR11, NFR12, NFR13, NFR14, NFR17

---

### Story 2.1: Estate Plan Activation, Executor Token Generation & Valuation Snapshot

As an estate planner,
I want to activate my estate plan to generate an executor access code and lock a valuation snapshot of my portfolio,
So that my executor will have a stable record of asset values at the moment I gave them access.

**Acceptance Criteria:**

**Given** owner visits `/estate/activate/` and has designated an executor (Story 1.2)
**When** the page renders
**Then** a single "Activate Estate Access" button is visible
**And** the button is disabled with explanation if no executor is designated

**Given** owner clicks "Activate Estate Access" and submits the confirmation form
**When** the activation is processed
**Then** a cryptographically secure 32-character alphanumeric code is generated using Python `secrets.token_urlsafe()`
**And** an `EstateAccessToken` record is created: `owner`, `token_hash` (SHA-256 of raw token, never stored raw), `issued_at`, `is_active=True`, `activated_by_owner=True`
**And** a `ValuationSnapshot` record is created per item: `item FK`, `owner FK`, `snapshot_date=today`, `market_value` (from `item.current_market_value`), `cost_basis` (from `item.purchase_price`), `equity` (computed), `snapshot_trigger=ESTATE_ACTIVATION` — records are append-only, no update or delete ever issued
**And** the raw token is shown once in the response and never again
**And** a success message instructs the owner to copy the token for their executor

**Given** owner reactivates (token already exists)
**When** they submit activation again
**Then** the old token is deactivated (`is_active=False`) and a new token + snapshot are created

**Given** no valuation data exists for an item
**When** the snapshot is created
**Then** `market_value` and `cost_basis` are stored as `None` (null) and the activation still completes

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- New model `EstateAccessToken` in `models.py`: `owner OneToOneField(User CASCADE)`, `token_hash CharField(64)`, `issued_at auto_now_add`, `expires_at DateTimeField(null=True)`, `is_active BooleanField default=True`, `last_used_at DateTimeField(null=True)`, `use_count IntegerField(default=0)`
- New model `ValuationSnapshot` in `models.py`: `item FK(DynamicCollectionItem CASCADE)`, `owner FK(User CASCADE)`, `snapshot_date DateField`, `market_value DecimalField(null=True)`, `cost_basis DecimalField(null=True)`, `equity DecimalField(null=True)`, `snapshot_trigger CharField(choices: ESTATE_ACTIVATION/MANUAL)`, `created_at auto_now_add` — no `update()` or `delete()` ever called on this model
- Service `activate_estate_plan(user)` in `api/services.py`: generates token, hashes with `hashlib.sha256`, bulk-creates snapshot records in one query
- Raw token returned from service function, stored nowhere — displayed once in view
- `EstateActivateForm` — single checkbox: "I understand this code must be kept secure and cannot be recovered"

---

### Story 2.2: Executor Code Entry & Session Establishment

As a designated executor,
I want to enter my access code on a public portal page to establish a secure session,
So that I can access the estate portfolio without needing a Django account of my own.

**Acceptance Criteria:**

**Given** an unauthenticated visitor accesses `/estate/portal/`
**When** the page renders
**Then** a code entry form is shown with a single text input and "Access Estate" button
**And** the page renders without requiring login

**Given** executor submits a valid token
**When** the code is verified
**Then** the raw code is hashed and compared to `EstateAccessToken.token_hash`
**And** a Django session key `estate_executor_owner_id` is set to the owning user's PK
**And** `EstateAccessToken.last_used_at` is updated and `use_count` incremented
**And** the executor is redirected to `/estate/portal/dashboard/`

**Given** executor submits an invalid or expired token
**When** verification fails
**Then** a generic error message is shown: "Invalid access code. Please contact the estate owner."
**And** no session data is set
**And** comparison uses `secrets.compare_digest` (constant-time, timing-safe)

**Given** `is_active=False` on the token
**When** executor attempts to use it
**Then** it is treated as invalid (same generic error)

**Given** executor navigates to `/estate/portal/dashboard/` without a valid session
**When** the request arrives
**Then** they are redirected to `/estate/portal/`

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- `executor_required` decorator in `src/my_garage/estate_views.py`: checks `request.session.get("estate_executor_owner_id")`, redirects to `/estate/portal/` if missing
- `ExecutorCodeForm` — single `CharField` with `widget=PasswordInput`, max_length=64
- Comparison: `secrets.compare_digest(hashlib.sha256(submitted.encode()).hexdigest(), stored_hash)` — constant-time
- Portal views NOT protected by `@login_required` — use `executor_required` decorator instead
- Session key `estate_executor_owner_id` is the sole auth mechanism in all portal views

---

### Story 2.3: Executor Portfolio View

As a designated executor,
I want to see a complete overview of the estate portfolio including all item valuations from the snapshot,
So that I can understand the full scope of assets I need to administer.

**Acceptance Criteria:**

**Given** executor has an active session and visits `/estate/portal/dashboard/`
**When** the page renders
**Then** the owner's name (first + last, or username) and estate activation date are displayed
**And** every `DynamicCollectionItem` owned by the estate owner is listed: name, collection type, snapshot valuation, current market value
**And** a portfolio summary shows: total items, total snapshot value, total current value, delta
**And** executor sees the assigned beneficiary name per item (or "Unassigned")
**And** a "Download PDF" button links to the PDF export (Epic 4)

**Given** the snapshot contains null values for some items
**When** the dashboard renders
**Then** null values display as "—" (em dash), not blank or zero

**Given** executor session expires
**When** they request a portal page
**Then** they are redirected to `/estate/portal/` without a 500 error

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- Selector `get_executor_portfolio_context(owner_user)` in `api/selectors.py`: fetches all items + latest `ValuationSnapshot` per item + `BeneficiaryAssignment` in 3 ORM queries (no N+1)
- Template: `estate/portal/dashboard.html` — standalone (no `{% extends %}`), minimal nav, luxury aesthetic
- Session read wrapped in try/except; redirect to `/estate/portal/` on `User.DoesNotExist`

---

### Story 2.4: Executor Item Detail View

As a designated executor,
I want to view detailed information about any single item in the estate,
So that I can verify provenance, condition, and estate assignment before acting on it.

**Acceptance Criteria:**

**Given** executor is on the portfolio dashboard and clicks an item
**When** they navigate to `/estate/portal/items/<item_id>/`
**Then** the page renders with full item detail: name, collection type, custom field values, photo (if present), purchase price, purchase date, notes
**And** the snapshot valuation row is shown: snapshot date, market value, cost basis, equity
**And** the assigned beneficiary name and conditional note are shown

**Given** the item belongs to a different owner than the executor's session
**When** the request arrives
**Then** a 404 is returned — executor cannot enumerate items across estates

**Given** the item has no photo
**When** the detail page renders
**Then** a placeholder is shown, not a broken image tag

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- URL: `path("portal/items/<int:item_id>/", ..., name="executor_item_detail")` in `estate_urls.py`
- View: `DynamicCollectionItem.objects.get(pk=item_id, owner=session_owner)` — raises `Http404` on owner mismatch
- Selector `get_executor_item_detail_context(item, owner)` in `api/selectors.py`
- Template: `estate/portal/item_detail.html` — standalone

---

## Epic 3: Beneficiary Scoped Access

The owner generates a unique, revocable link per beneficiary. Each beneficiary follows their link to a scoped portal showing only their designated items — enforced at the ORM query level. Beneficiaries can view item detail and download a personal PDF summary.

**FRs covered:** FR19, FR20, FR21, FR28, FR29, FR30, FR42 (partial — beneficiary data isolation)
**NFRs covered:** NFR8, NFR9, NFR10, NFR15, NFR18, NFR19

---

### Story 3.1: Beneficiary Scoped Link Generation

As an estate planner,
I want to generate a unique, scoped access link for each beneficiary,
So that each recipient can view only the items assigned to them and nothing else.

**Acceptance Criteria:**

**Given** owner visits `/estate/beneficiaries/`
**When** they click "Generate Access Link" for a beneficiary
**Then** a `BeneficiaryAccessLink` record is created with hashed token, `issued_at`, `is_active=True`
**And** the full shareable URL is displayed once: `https://<host>/estate/beneficiary/<raw_token>/`
**And** a warning is shown: "This link cannot be recovered. Save it now before closing."

**Given** owner generates a second link for the same beneficiary
**When** the new link is created
**Then** the previous `BeneficiaryAccessLink` is deactivated (`is_active=False`)
**And** only one active link exists per beneficiary at any time

**Given** owner visits the beneficiary list
**When** the page renders
**Then** each beneficiary row shows link status: "Active link" or "No link generated"
**And** "Revoke" action is available for active links

**Given** owner clicks "Revoke" for an active link
**When** the action is confirmed
**Then** `is_active` is set to `False` and the token is immediately invalid

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- New model `BeneficiaryAccessLink` in `models.py`: `beneficiary OneToOneField(Beneficiary CASCADE)`, `owner FK(User CASCADE)`, `link_token_hash CharField(64)`, `issued_at auto_now_add`, `expires_at DateTimeField(null=True)`, `is_active BooleanField default=True`, `last_accessed_at DateTimeField(null=True)`, `access_count IntegerField(default=0)`
- `OneToOneField` on `beneficiary` enforces one-link-per-beneficiary at ORM level
- Raw token: `secrets.token_urlsafe(32)`, hashed with `hashlib.sha256`, returned from service, displayed once, stored nowhere
- Service `generate_beneficiary_link(beneficiary, owner)` in `api/services.py`
- Revoke: `link.is_active = False; link.save(update_fields=["is_active"])` — no delete

---

### Story 3.2: Beneficiary Scoped Access Portal

As a named beneficiary,
I want to follow my unique link to view the items designated for me,
So that I can see what I will inherit without accessing anyone else's information.

**Acceptance Criteria:**

**Given** beneficiary accesses `/estate/beneficiary/<token>/`
**When** the token is valid and active
**Then** the token is hashed and compared to `link_token_hash` using `secrets.compare_digest`
**And** `last_accessed_at` and `access_count` are updated
**And** the beneficiary's name, relationship, and a greeting are displayed
**And** only items with a `BeneficiaryAssignment` pointing to this beneficiary are shown — enforced at ORM query level

**Given** the token is invalid, revoked, or expired
**When** the request arrives
**Then** a 404 is returned (no information about whether the token ever existed)

**Given** beneficiary has zero items assigned
**When** the portal renders
**Then** an empty state is shown: "No items have been designated for you yet."

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- View at `/estate/beneficiary/<str:token>/` — no `@login_required`, no `executor_required`
- ORM isolation: `BeneficiaryAssignment.objects.filter(beneficiary=link.beneficiary).select_related("item")` — isolation enforced at query level, not UI layer
- Template: `estate/beneficiary/portal.html` — standalone, no owner account chrome
- `expires_at` check: if not null and `expires_at < now()`, treat as invalid (same 404)

---

### Story 3.3: Beneficiary Item Detail View

As a named beneficiary,
I want to view the full details of an item designated to me,
So that I can understand exactly what asset is being left to me and under what conditions.

**Acceptance Criteria:**

**Given** beneficiary clicks an item in their portal
**When** they navigate to `/estate/beneficiary/<token>/items/<item_id>/`
**Then** the page renders with item name, collection type, photo (or placeholder), purchase price, purchase date, notes, custom field values
**And** `BeneficiaryAssignment.conditional_note` is prominently displayed if present
**And** the `ValuationSnapshot` is shown: snapshot date, market value, cost basis

**Given** the item is assigned to a different beneficiary
**When** the request arrives
**Then** a 404 is returned

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- View verifies: (1) token valid + active, (2) `BeneficiaryAssignment` exists with `beneficiary=link.beneficiary` and `item.pk=item_id` — raises `Http404` if either fails
- Template: `estate/beneficiary/item_detail.html` — standalone

---

### Story 3.4: Beneficiary Personal Export

As a named beneficiary,
I want to download a personal summary of my designated items as a PDF,
So that I have an offline record I can share with a solicitor or keep in a safe place.

**Acceptance Criteria:**

**Given** beneficiary clicks "Download My Summary (PDF)"
**When** the PDF is generated
**Then** it contains: beneficiary name, relationship, generation date, table of designated items with name, collection type, conditional note, snapshot valuation (or "—" if null)

**Given** the token is revoked or expired
**When** the PDF endpoint is accessed
**Then** a 404 is returned

**Given** beneficiary has zero items
**When** PDF is generated
**Then** the PDF contains the header and a "No items designated" note — no server error

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- URL: `path("beneficiary/<str:token>/export/", ..., name="beneficiary_export")` in `estate_urls.py`
- Shared helper `resolve_beneficiary_link(token)` → `BeneficiaryAccessLink` or 404, reused by Stories 3.2, 3.3, 3.4
- PDF bytes from `render_beneficiary_pdf(link)` defined in Epic 4
- View returns `HttpResponse(pdf_bytes, content_type="application/pdf")` with `Content-Disposition: attachment; filename="estate-summary-<name>.pdf"`

---

## Epic 4: Estate Inventory PDF Export

A reusable PDF rendering service (`pdf_service.py`) built on `reportlab` powers three export paths: full estate inventory for owner, same inventory for executor via portal session, and change-history audit log for solicitor use. All outputs are generated synchronously — PDFs are small enough for a single request cycle.

**FRs covered:** FR31, FR32, FR33, FR34
**NFRs covered:** NFR4, NFR16, NFR20
**Dependency:** Epic 2 (ValuationSnapshot), Epic 3 (BeneficiaryAccessLink helper)

---

### Story 4.1: PDF Rendering Service

As a developer,
I want a reusable PDF rendering layer for estate documents,
So that all PDF outputs share consistent formatting and a single implementation can be maintained.

**Acceptance Criteria:**

**Given** `render_estate_pdf(owner, items_with_context)` is called
**When** it executes
**Then** it returns raw PDF bytes using `reportlab`
**And** the PDF contains a cover page with owner name and generation date, and a table with item name, collection type, assigned beneficiary, snapshot market value, cost basis, equity, conditional note
**And** null monetary values render as "—" (em dash)
**And** a zero-item list returns a valid PDF with header and empty table — no exception

**Given** `render_beneficiary_pdf(link)` is called
**When** it executes
**Then** it returns raw PDF bytes for only the beneficiary's designated items
**And** the cover page shows beneficiary name, relationship, generation date

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ -x -q` passes (tested with byte-length and keyword assertions)

**Technical notes:**
- New module `src/my_garage/services/pdf_service.py`
- `reportlab` added via `pixi add reportlab`
- `render_estate_pdf(owner, items_with_context: list[dict]) -> bytes`
- `render_beneficiary_pdf(link: BeneficiaryAccessLink) -> bytes`
- Table columns: Name | Collection | Beneficiary | Snapshot Value | Cost Basis | Equity | Note
- Page size: A4, margins 2cm

---

### Story 4.2: Full Estate Inventory PDF (Owner & Executor)

As an estate planner or executor,
I want to download a complete PDF inventory of the entire portfolio,
So that I have a printable record suitable for solicitors and probate proceedings.

**Acceptance Criteria:**

**Given** authenticated owner visits `/estate/`
**When** they click "Download Full Inventory (PDF)"
**Then** a POST to `/estate/export/pdf/` returns a PDF with every `DynamicCollectionItem`, snapshot valuation, and beneficiary assignment

**Given** executor is on `/estate/portal/dashboard/`
**When** they click "Download PDF"
**Then** a GET to `/estate/portal/export/pdf/` generates the same full inventory (owner identified via executor session)

**Given** the owner has 200+ items
**When** the PDF is generated
**Then** the response completes within 10 seconds and the PDF paginates correctly

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- Owner view: `@login_required @require_POST`, calls `render_estate_pdf(owner, context_list)`
- Executor view: `@executor_required`, reads owner from session, same PDF call
- Selector `get_estate_pdf_context(owner)` in `api/selectors.py`: 3 ORM queries, no N+1
- URL (owner): `path("export/pdf/", ..., name="estate_pdf_export")`
- URL (executor): `path("portal/export/pdf/", ..., name="executor_pdf_export")`

---

### Story 4.3: Audit Log PDF Export

As an estate planner,
I want to download a PDF of my estate change history,
So that I can demonstrate to solicitors that assignments were intentional and when they were made.

**Acceptance Criteria:**

**Given** owner clicks "Download Change History (PDF)"
**When** the POST to `/estate/export/audit-pdf/` is processed
**Then** a PDF is returned containing every `EstateChangeLog` row: timestamp, action, item name, beneficiary name, ordered ascending by timestamp

**Given** owner has no change log entries
**When** the PDF is generated
**Then** the PDF contains the header and "No changes recorded" — no server error

**Given** new code is submitted
**When** the quality gate runs
**Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes

**Technical notes:**
- New function `render_audit_pdf(owner) -> bytes` in `pdf_service.py`
- Table columns: Timestamp | Action | Item | Beneficiary
- `@login_required @require_POST` guard
- URL: `path("export/audit-pdf/", ..., name="estate_audit_pdf_export")`

---

## Step 4 — Final Validation

### FR Coverage Map

| FR | Story |
|---|---|
| FR1 (executor designation) | 1.2 |
| FR2 (executor contact info) | 1.2 |
| FR3 (one executor per account) | 1.2 |
| FR4 (estate activation) | 2.1 |
| FR5 (plan completeness view) | 1.4 |
| FR6 (dashboard) | 1.4 |
| FR7 (beneficiary profiles) | 1.1 |
| FR8 (beneficiary CRUD) | 1.1 |
| FR11 (per-item assignment) | 1.3 |
| FR12 (conditional notes) | 1.3 |
| FR13 (charitable designation) | 1.3 |
| FR14 (change history) | 1.3 |
| FR15 (access token generation) | 2.1 |
| FR16 (token hashing) | 2.1 |
| FR17 (token verification) | 2.2 |
| FR18 (executor session) | 2.2 |
| FR19 (beneficiary link generation) | 3.1 |
| FR20 (link revocation) | 3.1 |
| FR21 (one active link per beneficiary) | 3.1 |
| FR22 (executor portfolio view) | 2.3 |
| FR23 (executor item detail) | 2.4 |
| FR24 (snapshot at activation) | 2.1 |
| FR25 (snapshot append-only) | 2.1 |
| FR26 (snapshot market value) | 2.1 |
| FR27 (snapshot cost basis) | 2.1 |
| FR28 (beneficiary scoped view) | 3.2 |
| FR29 (ORM-level isolation) | 3.2 |
| FR30 (beneficiary item detail) | 3.3 |
| FR31 (full inventory PDF) | 4.2 |
| FR32 (executor PDF) | 4.2 |
| FR33 (beneficiary personal PDF) | 3.4 |
| FR34 (audit log PDF) | 4.3 |
| FR35 (change log) | 1.3 |
| FR36 (token last used) | 2.2 |
| FR37 (token use count) | 2.2 |
| FR38 (executor session guard) | 2.2 |
| FR39 (valuation null handling) | 2.1 |
| FR40 (assignment history) | 1.3 |
| FR41 (account deletion cascade) | 1.5 |
| FR42 (profile integration) | 1.5 |
| FR43 (profile estate card) | 1.5 |

**All 43 FRs covered. All 20 NFRs addressed across stories.**

### New Models Required (all in `src/my_garage/models.py`)

1. `Beneficiary` — Story 1.1
2. `EstateExecutor` — Story 1.2
3. `BeneficiaryAssignment` — Story 1.3
4. `EstateChangeLog` — Story 1.3
5. `EstateAccessToken` — Story 2.1
6. `ValuationSnapshot` — Story 2.1
7. `BeneficiaryAccessLink` — Story 3.1

### Implementation Order

Epic 1 → Epic 2 → Epic 3 → Epic 4 (each epic depends on prior models)

### Security Constraints (carry through all implementation)

- Estate access tokens: `secrets.token_urlsafe()` — never sequential
- Beneficiary PII stored only within owner's account — never transmitted to third parties
- Beneficiary data isolation enforced at ORM query level on every request — UI-layer filtering alone is insufficient
- Valuation snapshots: append-only — no UPDATE or DELETE after creation
- Token comparison: always `secrets.compare_digest` — constant-time
