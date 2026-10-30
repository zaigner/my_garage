---
title: 'Fix the welcome checklist step-2 link'
type: 'bugfix'
created: '2026-10-29'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** On `/welcome/`, the step-2 ("Get a market valuation") "View →" link is hard-coded to `{% url 'collections:collection_list' 'automobiles' %}` (`templates/pages/onboarding.html:190`), so it 404s for any guest with items but no Automobiles collection (CAP-1; brownfield.md "Defect").

**Approach:** The `onboarding` view (`src/config/views.py`, not `my_garage/views.py`) passes the slug of the guest's active collection that holds their most recently added item. Only collections whose service provider supports valuation count: today that is Automobiles and Horology Salon. The template's step-2 "View →" link goes there. When the guest has no item in such a collection, step 2 shows a short note ("Valuations are available for vehicles and watches") and no link, so it never 404s or leads to a dead end. Regression test: a guest with only Wine Collection and one item gets 200 from every link on /welcome/ and sees the note instead of a step-2 link.

**Decision (2026-10-29, review F1, by user):** The first approach linked to the latest item's collection whatever its type. It was replaced because only the vehicle and timepiece providers can run a valuation, so for any other collection step 2 could never be completed. The user chose "prefer a valuation-capable collection, else explain".

</frozen-after-approval>

## Implementation Notes

- `src/config/views.py` `onboarding`: adds `valuation_collection_slug`, one `values_list(...).first()` query over the user's items in active collections they own, newest first. The query is inline ORM like its three neighbours (`has_items` and the others); it was not moved to a selector. The file is CRLF, so it was edited with Edit and the line endings were preserved.
- `templates/pages/onboarding.html`: the step-2 href uses the slug, and falls back to `collections:collection_type_list` when the slug is None.
- `tests/functional/test_collection_provisioning.py`: new `TestOnboardingChecklistLinks` with 4 tests. Every `href="/..."` on /welcome/ is fetched and must return 200 for a Wine-only guest. Also covered: picking the latest item's collection, no leak of another user's items, and the fallback when the only collection is inactive. All 4 failed with the fix stashed.
- Surprise: `provision_collections` returns collections in catalogue order, not request order. The first test draft unpacked them wrongly, so it now looks them up by slug.
- Out of scope, recorded in deferred-work: `templates/base.html:23` (Vehicles/Timepieces nav) also hard-codes the `automobiles` and `horology-salon` slugs. `collection_item_confirm_delete.html` extends `base.html`, so guests can reach those links.

- After review F1 (user decision), replaced the item query with a `CollectionType` query: active, owned, holding the user's items, annotated `Max("items__created_at")`, ordered `("-latest_item", "-pk")`. It returns the first one whose `get_collection_services(service_provider_key).supports_valuation_refresh()` is True. The capability check reuses the provider registry rather than hard-coding slugs. The note copy does say "vehicles and watches", which matches today's two providers.
- Template: `{% elif valuation_collection_slug %}` shows the View link (`data-testid="step2-view-link"`). `{% elif has_items %}` shows the note (`data-testid="step2-unavailable-note"`). The `collection_type_list` fallback was dropped.
- Tests rewritten: 7 in `TestOnboardingChecklistLinks`. 5 fail with the fix stashed. The 2 that pass without the fix (no items; another user's items) guard the new branches.
- Gates: unit 499, functional 714, lint and format all clean.

## Review Triage Log

Pass 1 (Blind Hunter, 11 findings):

- F1 high (HALT, resolved by user, now patched): step 2 can't be completed for a Wine-only guest. `supports_valuation_refresh()` is True only for the vehicle and timepiece providers, and only those write `GenericValuationHistory`. So the link no longer 404s, but it leads to a collection with no valuation action. The frozen intent is the user's own decision, so this goes to the human.
- F2 medium, patched: the link tests were vacuous. `_nav.html` (included at `onboarding.html:54`) already renders `collection_type_list` and per-collection links. Added `data-testid="step2-view-link"` and a `_step2_href` helper. With the template forced to always fall back, 3 of 4 tests fail.
- F3 low, patched: `order_by("-created_at")` had no tie-breaker. Changed to `("-created_at", "-pk")`.
- F4 low, rejected (now moot): `has_items` and the slug query disagree on `is_active`. Nothing in `src/` sets `CollectionType.is_active=False` (only the admin can), so a guest can't reach that state. After F1 the fallback link is gone, and the template only builds a URL when the slug is set.
- F5 low, rejected: the view uses inline ORM instead of a selector. It matches the three neighbouring queries in `onboarding`, and a new selector would be more than a simple correction.
- F6 low, patched: the module docstring didn't mention the checklist-link tests. Docstring updated.
- F7–F11 deferred (deferred-work.md): spec gaps for Stories 2–4 and the success signal. These are the themed-list empty state, the throwaway DB and login path, git history growth from MP4s, the determinism comparison method, and the first-sign-in field.

