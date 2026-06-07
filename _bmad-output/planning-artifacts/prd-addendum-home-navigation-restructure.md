---
status: approved
completedAt: '2026-06-02'
author: Zaigner77
project: my_garage
type: prd-addendum
parent: prd.md
---

# PRD Addendum — Home Page Navigation Restructure

**Feature:** Home Dashboard Navigation Tiles
**Author:** Zaigner77
**Date:** 2026-06-02
**Scope:** Cosmetic + structural (no new models, no migrations)

---

## Problem Statement

The home page (`/`) and the Collections Hub page (`/collections/`) present near-identical tile grids — both show per-collection cards (Timepieces, Automobiles, custom collections) with item counts and category values. A user navigating home → Collections sees the same information twice in slightly different visual wrappers. This redundancy flattens what should be a clear two-level hierarchy:

- **Home** = financial dashboard ("how is my portfolio doing?")
- **Collections** = asset management hub ("what do I have and where do I manage it?")

The home page collection tiles also grow unboundedly as users add custom collections, eventually producing an unwieldy grid on the dashboard.

---

## Solution

Replace the per-collection tile grid on the home page with three fixed utility tiles that serve a **navigation + action** role rather than a data display role. The financial dashboard sections (total portfolio value, YoY change, NFP card, Recent Acquisitions) are unchanged.

### Three Utility Tiles

| Tile | Destination | State | Purpose |
|---|---|---|---|
| **Collections Hub** | `/collections/` | Active (link) | Single gateway into all collection management |
| **Estate & Legacy** | — | Locked / Coming Soon | Surface PRD-planned feature, create awareness |
| **My Account** | `/accounts/password_change/` | Active (link) | Account security entry point (placeholder pending dedicated account page) |

---

## Design Decisions

### Collections Hub tile
Shows two live stats from context: total collection type count and total item count across all collections. Gives the tile data density without duplicating the per-collection breakdown. Links to `collections:collection_type_list`.

### Estate & Legacy tile
Non-linked, visually locked state (reduced opacity, lock icon, "Coming Soon" badge). Uses PRD tagline language: "Designate beneficiaries, assign an executor, and protect your collection's future." References parent PRD (`prd.md`) — the full feature spec is already written. This tile is a placeholder that drives feature awareness without requiring any backend work.

### My Account tile
Links to Django's built-in `password_change` view as a temporary account management entry point. A dedicated account page (profile, preferences, notification settings) is out of scope for this addendum but should be tracked as a follow-on story under the Estate & Legacy PRD or as a standalone UX epic.

---

## Visual Differentiation

The utility tiles use the same `luxury-card` visual language as the rest of the home page but signal a **navigation/action** role through:
- Prominent centered icon (60px circle) rather than financial data at top
- Descriptive body copy (no item counts or dollar values in the card header)
- "Manage →" CTA at tile bottom
- Locked tile uses reduced opacity + lock icon rather than gold arrow

This distinguishes them from the data tiles above (portfolio value, NFP) and from the collection detail tiles on `collection_types.html`.

---

## What Is Not Changed

- Portfolio value counter (animated, top of page)
- YoY change badge
- Net Financial Position card
- Recent Acquisitions horizontal scroll gallery
- Unauthenticated marketing section (VIN Auto-Decode, Live Market Valuations, Receipt OCR + CTA)
- `collection_types.html` visual style (separate ticket if desired)

---

## View Changes

Add two context variables to `config/views.py` home view:

| Variable | Value | Purpose |
|---|---|---|
| `total_items_count` | `all_collection_items.count()` | Displayed on Collections Hub tile |
| `total_collection_types_count` | `collection_types.count()` | Displayed on Collections Hub tile |

---

## Out of Scope

- Dedicated account/profile page
- Estate & Legacy backend implementation (covered in `prd.md`)
- `collection_types.html` visual alignment (tracked separately)
- Mobile-specific tile layout variations beyond Tailwind responsive grid

---

## Acceptance Criteria

- [ ] Home page for authenticated users shows exactly 3 utility tiles in place of the per-collection grid
- [ ] Collections Hub tile links to `/collections/` and shows correct type + item counts
- [ ] Estate & Legacy tile renders in locked/coming-soon state with no active link
- [ ] My Account tile links to `/accounts/password_change/`
- [ ] Unauthenticated home page: utility tiles do not render (not visible to logged-out visitors)
- [ ] Recent Acquisitions section unchanged
- [ ] All existing home view tests pass
- [ ] New context variables (`total_items_count`, `total_collection_types_count`) covered by functional tests
