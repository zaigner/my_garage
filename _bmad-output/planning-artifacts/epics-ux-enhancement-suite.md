---
stepsCompleted: [step-01, step-02, step-03, step-04]
inputDocuments:
  - docs/UX-enhancement.md
  - CLAUDE.md
status: implemented
date: 2026-05-21
author: Zaigner77
---

# my_garage — UX Enhancement Suite: Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the **UX Enhancement Suite** (13 specs), decomposing the requirements from `docs/UX-enhancement.md` into implemented stories. All stories are shipped and quality-gated (304 tests passing, ruff clean).

**Tech Stack:** Django 5.2, Tailwind CSS (CDN), Alpine.js 3.x, Font Awesome 6.4, Google Gemini API.

---

## Requirements Inventory

### Functional Requirements

- FR-01: Portfolio value must animate on page load to create emotional engagement
- FR-02: Navigation must be accessible on touch devices (no hover-only interactions)
- FR-03: Search must be discoverable without opening the hamburger menu
- FR-04: System messages must not cause page layout shift
- FR-05: File upload inputs must support drag-and-drop with visual feedback
- FR-06: Valuation history must be represented as a visual trend chart
- FR-07: Empty collection states must communicate collection-specific value propositions
- FR-08: Onboarding checklist completion must reflect real user progress from the database
- FR-09: Valuation history must be surfaced within the existing tab system on item detail pages
- FR-10: Collection item cards must communicate interactivity affordance on hover
- FR-11: Users must be able to generate an AI-written curator's note for any collection item
- FR-12: Users must be able to view portfolio allocation analytics broken down by category
- FR-13: Service records must be viewable in a timeline layout as an alternative to the table

### Non-Functional Requirements

- NFR-01: All interactive components must use Alpine.js — no custom JS beyond existing `toggleSearch()`
- NFR-02: All UI must conform to the luxury token palette (`luxury-gold` #D4AF37, `luxury-black` #0B1026, `luxury-card` #151b33, `luxury-white` #F5F5F5)
- NFR-03: No new backend models or database migrations required for any spec in this suite
- NFR-04: All views must pass `pixi run pytest tests/unit/ tests/functional/ -x -q` after implementation
- NFR-05: All code must pass `pixi run -- ruff check .` and `pixi run -- ruff format --check .`
- NFR-06: Provider context values that are QuerySets must be converted to Python lists before template rendering

### Additional Requirements

- ADD-01: `PromptRenderer` uses Jinja2 `StrictUndefined` — every key referenced in a `.j2` template must be present in the context dict passed to it; missing keys raise `UndefinedError` immediately
- ADD-02: Existing functional tests must be audited for string-matching assertions before shipping any spec that renames UI copy
- ADD-03: For any provider context field processed by a template, a no-mock regression test must verify `status_code == 200` with real DB rows

---

## FR Coverage Map

| FR | Epic | Story |
|---|---|---|
| FR-01 | Epic 1 | Story 1.1 |
| FR-02 | Epic 2 | Story 2.1 |
| FR-03 | Epic 2 | Story 2.2 |
| FR-04 | Epic 3 | Story 3.1 |
| FR-05 | Epic 4 | Story 4.1 |
| FR-06 | Epic 1 | Story 1.2 |
| FR-07 | Epic 5 | Story 5.1 |
| FR-08 | Epic 5 | Story 5.2 |
| FR-09 | Epic 1 | Story 1.3 |
| FR-10 | Epic 1 | Story 1.4 |
| FR-11 | Epic 6 | Story 6.1 |
| FR-12 | Epic 2 | Story 2.3 |
| FR-13 | Epic 2 | Story 2.4 |
| NFR-01..06 | All | All |
| ADD-01..03 | All | All |

---

## Epic List

1. **Epic 1: Portfolio Presentation & Visualisation** — Make the portfolio feel alive through animation, sparklines, tabs, and card affordances
2. **Epic 2: Navigation, Discovery & Analytics** — Make the app navigable on any device and surface portfolio analytics in a dedicated page and timeline view
3. **Epic 3: Toast Notification System** — Replace inline Django messages with a floating, non-disruptive notification layer
4. **Epic 4: Drag-and-Drop File Upload** — Replace hidden file inputs with accessible drop zones that preview selections and chain OCR
5. **Epic 5: Onboarding & Empty States** — Drive new-user activation with contextual empty state copy and real-time checklist completion
6. **Epic 6: AI Curator's Note** — Let users generate an auction-style curator's note for any collection item via Gemini

---

## Epic 1: Portfolio Presentation & Visualisation

**Goal:** Make the portfolio dashboard and item detail pages emotionally engaging by animating the hero value, showing valuation trends as sparklines, surfacing valuation history in a dedicated tab, and signalling card interactivity.

**FRs covered:** FR-01, FR-06, FR-09, FR-10

---

### Story 1.1: Portfolio Count-Up Animation

As a collector,
I want the hero portfolio value to count up from zero when I open the dashboard,
So that the moment feels alive and personal — not like reading a spreadsheet.

**Status:** ✅ Implemented

**Files:** `templates/pages/home.html`

**Acceptance Criteria:**

**Given** an authenticated user opens `/`
**When** the page finishes loading
**Then** the hero `<h1>` value animates from `$0` to the actual portfolio total over approximately 1.4 seconds using a cubic ease-out curve
**And** thousand separators are applied throughout the animation (e.g. `$247,500` not `$247500`)

**Given** an unauthenticated user opens `/`
**When** the page loads
**Then** `$---,---` is displayed statically with no animation

**Given** an authenticated user with a `$0` portfolio opens `/`
**When** the page loads
**Then** `$0` is displayed without any animation errors

---

### Story 1.2: Valuation History Sparkline Chart

As a collector,
I want to see a trend line above my valuation history list on an item's detail page,
So that I can understand appreciation or depreciation at a glance without parsing a table.

**Status:** ✅ Implemented

**Files:** `src/my_garage/templates/my_garage/collection_item_detail.html`, `src/my_garage/views.py`

**Acceptance Criteria:**

**Given** an item has 2 or more valuation history entries
**When** I view the item detail page
**Then** an SVG sparkline is shown above the date/value list, with the line coloured gold for a rising trend and red for a falling trend

**Given** an item has exactly 1 valuation history entry
**When** I view the item detail page
**Then** no sparkline is rendered — only the single list row is shown

**Given** an item has no valuation history
**When** I view the item detail page
**Then** the entire valuation section is hidden

**Given** a provider returns valuation history as a Django QuerySet
**When** the view processes the response
**Then** the QuerySet is converted to a Python list before template rendering so that `|last` and `|first` filters do not raise `ValueError: Negative indexing is not supported`

---

### Story 1.3: Valuations Tab in Item Detail

As a collector,
I want valuation history surfaced inside the existing tab system on the item detail page,
So that the detail page layout feels organised and consistent rather than having separate cards scattered across the page.

**Status:** ✅ Implemented

**Files:** `src/my_garage/templates/my_garage/collection_item_detail.html`

**Acceptance Criteria:**

**Given** an item has valuation history
**When** I view the item detail page
**Then** a "Valuations" tab button appears alongside "Service Records" and "Projects" with a count badge

**Given** I click the "Valuations" tab
**When** the tab activates
**Then** the sparkline chart and date/value list are shown in the tab panel, and the other tab panels are hidden

**Given** I load the item detail page
**When** the page first renders
**Then** the default active tab is "Service Records" — not "Valuations"

**Given** an item has no valuation history
**When** I view the item detail page
**Then** the "Valuations" tab button does not appear

---

### Story 1.4: Recent Acquisitions Hover Overlay

As a collector,
I want a visual affordance on the recent acquisitions cards,
So that I know the cards are clickable without having to guess or rely solely on cursor change.

**Status:** ✅ Implemented

**Files:** `templates/pages/home.html`

**Acceptance Criteria:**

**Given** I hover over a Recent Acquisitions card on the home page
**When** the hover state is active
**Then** a centred "View →" pill with a gold border appears over the card image with a fade transition

**Given** I hover over a Recent Acquisitions card
**When** the hover state is active
**Then** the existing 105% image scale behaviour is preserved alongside the overlay

**Given** an unauthenticated user views the marketing placeholder cards
**When** they hover over the cards
**Then** no hover overlay is shown (these cards are not linked)

---

## Epic 2: Navigation, Discovery & Analytics

**Goal:** Make the app navigable on any device, make search discoverable from the nav bar, and surface a dedicated portfolio analytics page alongside a timeline view of service records.

**FRs covered:** FR-02, FR-03, FR-12, FR-13

---

### Story 2.1: Nav Hamburger Click Toggle

As a user on a touch device,
I want the navigation menu to open when I tap the hamburger icon,
So that I can access all navigation links without a mouse hover.

**Status:** ✅ Implemented

**Files:** `templates/includes/_nav.html`

**Acceptance Criteria:**

**Given** any device (touch or pointer)
**When** the user clicks or taps the hamburger icon
**Then** the dropdown menu opens

**Given** the dropdown is open
**When** the user clicks or taps anywhere outside the menu
**Then** the dropdown closes

**Given** the dropdown is open
**When** the user presses Escape
**Then** the dropdown closes

**Given** the dropdown is open
**When** the user clicks a menu link
**Then** the dropdown closes and the browser navigates to the link destination

**Given** a hover-capable device
**When** the user hovers over the hamburger (without clicking)
**Then** the dropdown does not open — click is required

---

### Story 2.2: Search Icon in Nav

As a user,
I want a visible search icon in the navigation bar,
So that I can discover and access global search without knowing the ⌘K keyboard shortcut.

**Status:** ✅ Implemented

**Files:** `templates/includes/_nav.html`

**Acceptance Criteria:**

**Given** any page in the application
**When** the user looks at the navigation bar
**Then** a magnifying-glass icon is visible in the right-side nav cluster

**Given** the user clicks the search icon
**When** it is clicked
**Then** the search modal opens identically to pressing ⌘K

**Given** a screen reader user focuses the search icon button
**When** they navigate to it
**Then** the announced label is "Search (⌘K)"

---

### Story 2.3: Global Portfolio Insights Page

As a collector,
I want a dedicated analytics page showing my portfolio broken down by category,
So that I can understand allocation, equity, and which asset types are performing best.

**Status:** ✅ Implemented

**Files:** `src/my_garage/views.py` (`portfolio_insights`), `src/config/urls.py`, `src/my_garage/templates/my_garage/portfolio_insights.html`, `templates/includes/_nav.html`

**Acceptance Criteria:**

**Given** an authenticated user navigates to `/insights/`
**When** the page loads
**Then** KPI cards show Total Value, Total Equity, and Items Tracked

**Given** the user has items across multiple collection types
**When** the Insights page loads
**Then** each category is shown as a labelled horizontal bar whose width is proportional to its share of total portfolio value, with value, count, and equity displayed

**Given** the user has no items
**When** the Insights page loads
**Then** the page renders without errors, showing all zeros and no division errors

**Given** an unauthenticated user navigates to `/insights/`
**When** the request is made
**Then** the response redirects to the login page

**Given** the navigation hamburger menu is open
**When** the user looks at the menu items
**Then** an "Insights" link is present and navigates to `/insights/`

---

### Story 2.4: Service Record Timeline View

As a collector,
I want to toggle the All Services page between a table and a vertical timeline layout,
So that I can read maintenance history as a narrative rather than scanning rows.

**Status:** ✅ Implemented

**Files:** `src/my_garage/templates/my_garage/all_services.html`

**Acceptance Criteria:**

**Given** the All Services page has records
**When** the page loads
**Then** "Table" and "Timeline" toggle buttons are visible in the page header, with "Table" as the default active view

**Given** the user clicks "Timeline"
**When** the view changes
**Then** the table is hidden and a vertical timeline appears with a line, colour-coded dots per category (blue=MAINTENANCE, yellow=REPAIR, green=UPGRADE, purple=RESTORATION, pink=APPRAISAL), and per-record cards showing date, item name (linked), vendor, description, and cost

**Given** the user clicks "Table"
**When** the view changes
**Then** the timeline hides and the original table reappears unchanged

**Given** there are no service records
**When** the page loads
**Then** the view toggle buttons are not shown and the existing empty state is displayed

---

## Epic 3: Toast Notification System

**Goal:** Replace inline Django messages (which push page content down) with a fixed-position floating toast layer that is visually consistent with the luxury aesthetic and does not cause layout shift.

**FRs covered:** FR-04

---

### Story 3.1: Floating Toast Notifications

As a user,
I want Django system messages to appear as floating toasts in the top-right corner,
So that action confirmations are visible without disrupting the page layout I was looking at.

**Status:** ✅ Implemented

**Files:** `src/my_garage/templates/my_garage/base.html`

**Acceptance Criteria:**

**Given** a view adds a `messages.success(...)` message and redirects
**When** the redirect page loads
**Then** a floating toast appears in the top-right corner of the viewport, above all page content

**Given** a success toast is displayed
**When** 5 seconds pass
**Then** the toast fades out automatically

**Given** any toast is displayed
**When** the user clicks the X button on the toast
**Then** the toast dismisses immediately with a fade-out transition

**Given** multiple messages are queued
**When** the redirect page loads
**Then** all toasts stack vertically in the top-right corner

**Given** a toast is displayed and the user scrolls the page
**When** scrolling occurs
**Then** the toast remains fixed in the top-right corner — it does not scroll with the page

**Given** a page renders with a toast
**When** the toast appears
**Then** the page content below does not shift or reflow

---

## Epic 4: Drag-and-Drop File Upload

**Goal:** Replace hidden file inputs with accessible, visually clear drop zones that give immediate thumbnail feedback and, on service record forms, chain the existing OCR pipeline automatically.

**FRs covered:** FR-05

---

### Story 4.1: Drag-and-Drop Photo Upload

As a collector adding or editing an item or service record,
I want to drag an image directly onto the upload area,
So that uploading a photo or receipt is as fast as dropping a file from my desktop.

**Status:** ✅ Implemented

**Files:** `src/my_garage/templates/my_garage/collection_item_form.html`, `src/my_garage/templates/my_garage/collection_service_record_form.html`

**Acceptance Criteria:**

**Given** the item add or edit form is open
**When** the user drags an image file over the drop zone
**Then** the drop zone border highlights in gold and the background tints gold

**Given** an image is dropped or selected via the file picker
**When** the file is accepted
**Then** a thumbnail preview of the image appears inside the drop zone with the filename below it

**Given** the user clicks anywhere in the drop zone (not dragging)
**When** clicked
**Then** the native file picker opens

**Given** a non-image file is dragged and dropped
**When** it is dropped
**Then** nothing happens — non-image files are silently ignored

**Given** the service record form and an image is dropped or selected
**When** the file is accepted
**Then** the existing OCR pipeline triggers automatically in addition to showing the preview

**Given** the item edit form is opened for an item that already has a photo
**When** the form loads
**Then** the existing photo URL is shown as the initial preview inside the drop zone

---

## Epic 5: Onboarding & Empty States

**Goal:** Drive new-user activation by making empty states speak to the specific collection being viewed, and by making the onboarding checklist reflect real database state rather than hardcoded defaults.

**FRs covered:** FR-07, FR-08

---

### Story 5.1: Personalized Empty State Copy

As a new user looking at an empty collection,
I want the empty state to speak specifically to the type of collection I'm viewing,
So that I understand what value the platform delivers for this collection and feel motivated to add my first item.

**Status:** ✅ Implemented

**Files:** `src/my_garage/templates/my_garage/collection_list.html`

**Acceptance Criteria:**

**Given** the Automobiles collection has no items
**When** I view the collection list
**Then** the empty state shows "What's in the garage?" with copy describing VIN decoding and market valuation

**Given** the Horology Salon collection has no items
**When** I view the collection list
**Then** the empty state shows "Start your horological journey" with copy describing reference number tracking and valuation

**Given** a custom collection has no items
**When** I view the collection list
**Then** the empty state shows `{{ collection_type.name }} awaits` with generic collection copy

**Given** any empty state
**When** the user clicks the CTA button
**Then** navigation goes to the add item form for that collection type

---

### Story 5.2: Onboarding Step Auto-Completion

As a returning user who has already completed some onboarding steps,
I want the `/welcome/` checklist to reflect my actual progress,
So that I'm not shown as incomplete for things I've already done.

**Status:** ✅ Implemented

**Files:** `src/config/views.py` (`onboarding`), `templates/pages/onboarding.html`

**Acceptance Criteria:**

**Given** a new user with no items, no valuations, and no service records visits `/welcome/`
**When** the page loads
**Then** all three steps show as pending (no gold checkmark, no strikethrough)

**Given** a user who has added at least one item visits `/welcome/`
**When** the page loads
**Then** Step 1 shows as completed with a gold checkmark and strikethrough text

**Given** a user who has a valuation history entry visits `/welcome/`
**When** the page loads
**Then** Step 2 shows as completed with a gold checkmark and strikethrough text

**Given** a user who has a service record visits `/welcome/`
**When** the page loads
**Then** Step 3 shows as completed with a gold checkmark and strikethrough text

**Given** a user who has completed all three steps revisits `/welcome/`
**When** the page loads
**Then** the page auto-redirects to `/` without displaying the checklist

---

## Epic 6: AI Curator's Note

**Goal:** Let users generate a polished, auction-style description for any collection item by clicking a single button — demonstrating AI value concretely and making the app feel premium.

**FRs covered:** FR-11

---

### Story 6.1: AI Curator's Note Generation

As a collector viewing an item I own,
I want to generate an AI-written curator's note for the item with one click,
So that I have a polished, auction-house-style description without writing it myself.

**Status:** ✅ Implemented

**Files:** `src/my_garage/skills/theme_generator.py` (`generate_item_description`), `src/my_garage/views.py` (`collection_item_generate_description`), `src/my_garage/collection_urls.py`, `src/my_garage/templates/my_garage/collection_item_detail.html`

**Acceptance Criteria:**

**Given** I am viewing an item detail page
**When** the Actions panel is visible
**Then** a "Generate Description" button is displayed

**Given** I click "Generate Description"
**When** the API call is in flight
**Then** the button shows "Generating..." and is disabled, preventing duplicate requests

**Given** the API call completes successfully
**When** the response arrives
**Then** the generated curator's note appears in an italic text block below the button, and the button changes to "Regenerate"

**Given** the API call fails (network error or Gemini error)
**When** the failure is received
**Then** the button shows "Failed — Retry" in red and can be clicked again

**Given** `GOOGLE_API_KEY` is not set in the environment
**When** the endpoint is called
**Then** the view returns HTTP 500 with a JSON error body — no unhandled exception reaches the user

**Given** an unauthenticated user POSTs to the generate-description endpoint
**When** the request is received
**Then** the response is HTTP 302 redirecting to the login page

**Given** the view assembles the item context for the Gemini prompt
**When** calling `PromptRenderer.render("collection_item_description.j2", ...)`
**Then** `relevant_docs` is always present in the context dict (fetched via `ContextService.retrieve_relevant_docs()`, falling back to `[]`) because `PromptRenderer` uses Jinja2 `StrictUndefined` and a missing key raises `UndefinedError`

---

## Implementation Notes

### Known Bugs Fixed During This Suite

**Bug 1 — QuerySet `|last` Crash (`ValueError: Negative indexing is not supported`)**
- Root cause: `get_detail_context()` returns a QuerySet; `|last` calls `queryset[-1]`; tests used mocked Python lists and did not catch this
- Fix: `collection_item_detail` view converts `valuation_history` (and any list-like provider context) to a Python list after `get_detail_context()` returns
- Regression test: `test_valuation_history_queryset_renders_without_error` creates real DB rows and asserts `status_code == 200` with no mock

**Bug 2 — Jinja2 `StrictUndefined` Missing `relevant_docs`**
- Root cause: `collection_item_description.j2` references `relevant_docs`, but `CollectionItemContext.dict()` does not include it; `PromptRenderer` uses `StrictUndefined`
- Fix: `collection_item_generate_description` view always adds `relevant_docs` to the context dict (with `[]` fallback) before calling `PromptRenderer.render()`

### Quality Gate

All stories shipped and verified:

```bash
pixi run pytest tests/unit/ tests/functional/ -x -q   # 304 passed
pixi run -- ruff check .                               # 0 errors
pixi run -- ruff format --check .                      # 0 diffs
```

---

*Generated from: `docs/UX-enhancement.md`*
*Template: `_bmad/bmm/workflows/3-solutioning/create-epics-and-stories/templates/epics-template.md`*
*Workflow: BMM 3-Solutioning > Create Epics and Stories*
*Status: All stories implemented and shipped — 2026-05-21*
