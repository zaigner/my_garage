---
stepsCompleted: [step-01-document-discovery, step-02-prd-analysis, step-03-epic-coverage, step-04-ux-alignment, step-05-epic-quality, step-06-final-assessment]
status: complete
project: my_garage
date: '2026-05-29'
feature: Net Financial Position (NFP)
documentsAssessed:
  - _bmad-output/planning-artifacts/prd.md
missingDocuments:
  - architecture
  - ux-design
  - epics-nfp
---

# Implementation Readiness Assessment Report

**Date:** 2026-05-29
**Project:** my_garage
**Feature:** Net Financial Position (NFP)

---

## Document Inventory

| Document | File | Status |
|---|---|---|
| PRD | `prd.md` | ✅ Complete |
| Architecture | — | ⚠️ Not created |
| Epics & Stories (NFP) | — | ⚠️ Not created |
| UX Design | — | ⚠️ Not created |
| Epics (prior suite) | `epics-ux-enhancement-suite.md` | ℹ️ Exists — UX Enhancement Suite only |

---

## PRD Analysis

### Functional Requirements (32 total)

**Capability Area 1: Net Financial Position Calculation**
- FR1: The system calculates NFP for any Vehicle: `Market Value − (Purchase Price + Σ ServiceRecord.total_cost + Σ Upgrade.cost [INSTALLED])`
- FR2: The system calculates NFP for any DynamicCollectionItem: `Market Value − (Purchase Price + Σ GenericServiceRecord.total_cost + Σ GenericUpgrade.cost [COMPLETED])`
- FR3: The system calculates NFP for any Timepiece: `Market Value − (Purchase Price + Σ GenericUpgrade.cost [COMPLETED])` — service costs excluded until migration story ships
- FR4: The system produces a cost-component breakdown per asset: purchase price, service costs total, upgrade costs total, cost basis, market value, net position
- FR5: The system represents NFP as null when market value is not set — no zero substitution, no error raised

**Capability Area 2: NFP Cache Management**
- FR6: The system stores a cached `net_financial_position` value on each Vehicle, Timepiece, and DynamicCollectionItem
- FR7: The system refreshes a Vehicle's cached NFP when any associated ServiceRecord is created, updated, or deleted
- FR8: The system refreshes a Vehicle's cached NFP when any associated Upgrade is created, updated, or deleted
- FR9: The system refreshes a DynamicCollectionItem's cached NFP when any associated GenericServiceRecord is created, updated, or deleted
- FR10: The system refreshes a DynamicCollectionItem's cached NFP when any associated GenericUpgrade is created, updated, or deleted
- FR11: The system refreshes a Timepiece's cached NFP when any associated GenericUpgrade is created, updated, or deleted

**Capability Area 3: Asset List View Financial Display**
- FR12: The collector can view a financial summary (cost basis, market value, net position) for each Vehicle in the Vehicle list
- FR13: The collector can view a financial summary for each Timepiece in the Timepiece list
- FR14: The collector can view a financial summary for each item in any DynamicCollectionItem list
- FR15: The collector can distinguish gain from loss on any list row via both colour and symbol simultaneously — not colour alone
- FR16: The collector sees NFP displayed as unavailable — not zero, not error — when market value is unset

**Capability Area 4: Asset Detail View Financial Display**
- FR17: The collector can view a full financial breakdown on the Vehicle detail page: each cost component, cost basis, market value, net position
- FR18: The collector can view a full financial breakdown on the Timepiece detail page: purchase price, completed upgrade costs, cost basis, market value, net position
- FR19: The collector can view a full financial breakdown on the DynamicCollectionItem detail page: each cost component, cost basis, market value, net position
- FR20: The collector sees contextual guidance when market value is unset, directing them to add a valuation

**Capability Area 5: Portfolio-Level Financial Aggregation**
- FR21: The collector can view an aggregate NFP across all assets on the home dashboard
- FR22: The collector can view aggregate NFP broken down by asset type on the Insights page
- FR23: The collector can view per-asset-type NFP totals alongside existing portfolio allocation metrics on the Insights page

**Capability Area 6: Timepiece Upgrade Tracking**
- FR24: The collector can add a GenericUpgrade project to a Timepiece (name, brand, part number, status, cost, ordered date, completion date, notes)
- FR25: The collector can edit an existing Timepiece upgrade project
- FR26: The collector can delete a Timepiece upgrade project
- FR27: The collector can advance a Timepiece upgrade through: Wishlist → Ordered → In Progress → Completed → Cancelled
- FR28: The collector can view all upgrade projects for a Timepiece on the Timepiece detail page

**Capability Area 7: Display Accessibility & Formatting**
- FR29: The system displays NFP values with sign prefix (`+`/`−`) and currency formatting; `—` when null
- FR30: NFP gain/loss signals use both colour and symbol — interpretable without colour perception
- FR31: All NFP monetary values have `aria-label` attributes describing value and meaning in plain language
- FR32: Interactive NFP elements (tooltips, hint links) are keyboard-navigable via `Tab` and activatable via `Enter`/`Space`

### Non-Functional Requirements (15 total)

**Performance**
- NFR1: Asset list pages must not exhibit perceptible load time increase. NFP served from cached field — no aggregation at list render time.
- NFR2: NFP cache refresh completes within HTTP request/response cycle. Updated values visible on next page load.
- NFR3: Portfolio NFP aggregate uses `aggregate(Sum(...))` per asset type — max 3 queries total. Query count regression test required.
- NFR4: NFP breakdown selector on detail pages permitted one additional aggregation query. Must optimise before shipping if user-perceptible degradation detected.

**Security**
- NFR5: All views displaying NFP require `IsAuthenticated`. No NFP accessible to unauthenticated users.
- NFR6: All ORM queries filter by `owner=request.user`. No cross-user NFP visibility.
- NFR7: `refresh_asset_nfp` validates asset ownership before writing.

**Accessibility**
- NFR8: NFP gain/loss indicators satisfy WCAG 2.1 SC 1.4.1 — dual signal (colour + symbol) required.
- NFR9: All NFP monetary values include `aria-label` with value and meaning in plain language.
- NFR10: Interactive NFP elements keyboard-reachable and activatable with visible focus ring.

**Code Quality & Testability**
- NFR11: All new code passes ruff check and format (zero errors/diffs).
- NFR12: Existing 304-test suite passes without regression.
- NFR13: Unit tests cover NFP calculation for all 3 asset types: 5 edge case scenarios.
- NFR14: Portfolio aggregate query bound verified by functional test using `CaptureQueriesContext`.
- NFR15: All model changes accompanied by generated migrations in the same changeset.

### Constraints & Assumptions

- Timepiece service record tracking deferred to a separate migration story (GenericServiceRecord refactor)
- Cache refresh covers both `post_save` AND `post_delete` signals — delete path is the high-risk gap
- Solo developer resource profile — sequential implementation order required
- GenericRelation on Timepiece model requires no migration (GenericFK lives on GenericUpgrade)

### PRD Completeness Assessment

The PRD is well-structured with 32 FRs across 7 capability areas and 15 NFRs across 4 quality dimensions. All FRs are testable and implementation-agnostic. The scope boundary for the separate migration story is explicitly documented. The PRD is complete and suitable for downstream work.

---

## Epic Coverage Validation

### Coverage Matrix

No epics document exists for the NFP feature. The only planning artifact in the epics category is `epics-ux-enhancement-suite.md`, which covers the prior UX Enhancement Suite (shipped 2026-05-21) — a different feature entirely.

| Metric | Value |
|---|---|
| Total PRD FRs | 32 |
| FRs covered in epics | 0 |
| Coverage percentage | 0% |

### Missing Requirements — All 32 FRs

All 32 FRs (FR1–FR32) lack epic coverage. They are documented in full in the PRD Analysis section above.

### Assessment

0% epic coverage is expected for a freshly completed PRD. No epics have been created yet for this feature. This is the primary gap to address before implementation can begin.

---

## UX Alignment Assessment

### UX Document Status

Not found. No UX design document exists for the NFP feature.

### Alignment Issues

No UX document to align against.

### Warnings

⚠️ **UI is heavily implied** — The NFP feature introduces new UI components on every asset list page, every asset detail page, the home dashboard, and the Insights page. The PRD specifies:
- Mini breakdown row components (list views)
- Financial Position card (detail views)
- Aggregate NFP KPI cards (home + Insights)
- Null-safe display with tooltip
- Colour-coded + symbol-prefixed net position display

The PRD documents these at requirements level (FR12–FR23, FR29–FR32, NFR8–NFR10). No wireframes, mockups, or UX spec exists.

**Assessment:** For this brownfield project, UX design is low risk. The existing codebase has established patterns (luxury token palette, Alpine.js components, Tailwind utility classes) that the PRD explicitly references. The UX Enhancement Suite epics demonstrate that UI work in this codebase can be delivered directly from FR-level specifications without a separate UX document. A formal UX document is **recommended but not blocking** for this feature.

---

## Epic Quality Review

### Status

Not applicable — no NFP epics exist to review. This section will be populated when epics are created and this check is re-run.

### Brownfield Indicators for Future Epic Creation

When epics are created, verify:
- [ ] No epic titled "Set up models" or "Create database tables" — model changes belong inside feature stories
- [ ] Each epic delivers shippable user value independently
- [ ] Cache invalidation (signal handlers) is included in the same story as the feature that triggers it — not a separate technical story
- [ ] Timepiece upgrade UI story can be completed without any Vehicle or DynamicCollectionItem story (it uses existing GenericUpgrade model)
- [ ] Portfolio aggregate stories (home + Insights) depend only on the NFP cached field being present — can ship after the per-asset display stories

---

## Summary and Recommendations

### Overall Readiness Status

**NEEDS WORK** — PRD is complete and high quality. Downstream artifacts required before implementation can begin.

### What Is Ready

| Artifact | Status | Quality |
|---|---|---|
| PRD | ✅ Complete | Excellent — 32 FRs, 15 NFRs, clear scope boundaries, 4 user journeys |
| Scope decision | ✅ Locked | Timepiece uses GenericUpgrade + GenericRelation, no new models |
| Risk analysis | ✅ Documented | Cache invalidation delete path identified as high risk |
| Migration story boundary | ✅ Explicit | GenericServiceRecord refactor + Vehicle unification scoped out |

### What Is Missing

| Artifact | Priority | Impact if Missing |
|---|---|---|
| Epics & Stories | 🔴 Required | Cannot implement without sprint-ready stories |
| Architecture Document | 🟠 Recommended | Model changes + signal handler design benefit from arch review |
| UX Design | 🟡 Optional | PRD + existing patterns are sufficient for this brownfield feature |

### Critical Issues Requiring Action

**Issue 1 — No Epics Exist (Blocking)**
32 FRs have 0% epic coverage. No developer can begin implementation without stories. This is the sole blocking gap.

**Issue 2 — Architecture Not Documented (Recommended)**
The PRD specifies a `net_financial_position` cached field, Django signal handlers, `GenericRelation` on Timepiece, and 4 new selector functions. A brief architecture document would lock in the signal handler pattern, confirm the `post_save`/`post_delete` approach, and spec the 4 breakdown selectors before story writing begins. Not strictly blocking but reduces rework risk.

### Recommended Next Steps

1. **Create Epics & Stories** — `/bmad-mmm-create-epics-and-stories` using this PRD as input. Suggested epic structure:
   - Epic 1: NFP Foundation — cached field on all 3 models, calculation selectors, signal handlers
   - Epic 2: Asset Display — mini breakdown in list views + full breakdown on detail views (all 3 types)
   - Epic 3: Timepiece Upgrade Tracking — GenericRelation + upgrade CRUD UI
   - Epic 4: Portfolio Aggregation — home dashboard + Insights page NFP

2. **Optionally create Architecture** — `/bmad-mmm-create-architecture` to document signal handler design and selector contracts before story writing.

3. **Re-run this check** after epics are created to validate FR coverage and epic quality.

### Final Note

This assessment identified **2 gaps** across **2 categories**: missing epics (blocking) and missing architecture (recommended). The PRD itself is production-ready — high information density, complete FR coverage, clear scope boundaries, and explicit risk documentation. Address the epic gap to unlock implementation.

**Report:** `_bmad-output/planning-artifacts/implementation-readiness-report-2026-05-29.md`
