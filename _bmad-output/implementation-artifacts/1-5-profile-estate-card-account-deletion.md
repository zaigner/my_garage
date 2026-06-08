# Story 1.5: Profile Page Estate Status Card & Account Deletion Safeguard

Status: review

## Story

As a collector,
I want to see my estate plan status on my profile page and have a confirmed path to delete my account,
So that account management is in one place and my beneficiary data is fully protected if I leave.

## Acceptance Criteria

1. **Given** authenticated owner visits `/accounts/profile/` **When** the page renders **Then** an "Estate & Legacy" card is visible showing executor status, items assigned count vs total, and a "Manage Estate Plan →" link to `/estate/`

2. **Given** owner has no executor designated **When** the profile page renders **Then** the estate card shows a warning indicator: "No executor designated"

3. **Given** owner has all items assigned **When** the profile page renders **Then** the estate card shows a completion indicator

4. **Given** owner expands the "Danger Zone" section on the profile page and clicks "Delete Account" **When** they confirm in the modal **Then** a POST to `/accounts/delete/` deletes the `User` record **And** all `Beneficiary`, `EstateExecutor`, `BeneficiaryAssignment`, `EstateChangeLog` records are cascade-deleted via FK **And** the owner is logged out and redirected to the home page

5. **Given** new code is submitted **When** the quality gate runs **Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes with zero failures **And** ruff check and ruff format --check report zero errors

## Tasks / Subtasks

- [x] Task 1: Update `profile` view in `src/config/views.py`
  - [x] 1.1: Import `get_estate_dashboard_context` from `my_garage.api.selectors`
  - [x] 1.2: Call `get_estate_dashboard_context(user)` and extract `executor`, `items_total`, `items_assigned`, `completeness_pct`
  - [x] 1.3: Pass `executor_designated`, `estate_executor_name`, `estate_items_total`, `estate_items_assigned`, `estate_completeness_pct` to template context

- [x] Task 2: Add `delete_account` view to `src/config/views.py`
  - [x] 2.1: Import `logout` from `django.contrib.auth` and `require_POST` from `django.views.decorators.http`
  - [x] 2.2: `@login_required @require_POST` view: store user ref, call `logout(request)`, call `user.delete()`, redirect to `home`

- [x] Task 3: Add URL to `src/config/urls.py`
  - [x] 3.1: `path("accounts/delete/", views.delete_account, name="delete_account")`

- [x] Task 4: Add Estate & Legacy card to `templates/pages/profile.html`
  - [x] 4.1: Card 4 after existing Card 3 (Account Information) — header "Estate & Legacy"
  - [x] 4.2: Executor row — green dot + name if designated; yellow dot + "No executor designated" if not
  - [x] 4.3: Completeness row — "X of Y items assigned" with colored text (green=100%, gold=partial, yellow=0%)
  - [x] 4.4: "Manage Estate Plan →" link to `{% url 'estate:estate_dashboard' %}`

- [x] Task 5: Add Danger Zone card to `templates/pages/profile.html`
  - [x] 5.1: Card 5 — "Danger Zone" header with red border
  - [x] 5.2: "Delete Account" button opens Alpine.js confirmation modal (`x-data`/`x-show`)
  - [x] 5.3: Modal contains warning text + POST form to `{% url 'delete_account' %}` with CSRF token

- [x] Task 6: Write unit tests in `tests/unit/test_profile_estate_context.py`
  - [x] 6.1: Profile view context contains `executor_designated=False` when no executor
  - [x] 6.2: Profile view context contains `executor_designated=True` when executor set
  - [x] 6.3: `estate_items_total` and `estate_items_assigned` reflect actual item counts
  - [x] 6.4: `estate_completeness_pct` is correct

- [x] Task 7: Write functional tests in `tests/functional/test_profile_estate_story1_5.py`
  - [x] 7.1: Profile page returns 200 for auth user
  - [x] 7.2: Estate & Legacy card heading present
  - [x] 7.3: "No executor designated" shown when no executor
  - [x] 7.4: Executor name shown when designated
  - [x] 7.5: Completeness count present (items_assigned / items_total pattern)
  - [x] 7.6: "Manage Estate Plan" link to `/estate/` present
  - [x] 7.7: Danger Zone section present
  - [x] 7.8: DELETE — POST to `/accounts/delete/` deletes user and redirects to home
  - [x] 7.9: DELETE — cascades beneficiary, executor, assignment, changelog records
  - [x] 7.10: DELETE — GET to `/accounts/delete/` is rejected (405)
  - [x] 7.11: DELETE — unauthenticated POST redirects to login

- [x] Task 8: Quality gate — 533 passed (24 new), ruff clean, zero format diffs

## Dev Notes

### Profile view update

```python
from my_garage.api.selectors import get_estate_dashboard_context, ...

@login_required
def profile(request):
    ...
    ctx = get_estate_dashboard_context(user)
    return render(request, "pages/profile.html", {
        "form": form,
        "total_items": total_items,
        "executor_designated": ctx["executor"] is not None,
        "estate_items_total": ctx["items_total"],
        "estate_items_assigned": ctx["items_assigned"],
        "estate_completeness_pct": ctx["completeness_pct"],
    })
```

### Delete account view

```python
from django.contrib.auth import logout
from django.views.decorators.http import require_POST

@login_required
@require_POST
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    return redirect("home")
```

### Alpine.js modal pattern (consistent with existing modals)

```html
<div x-data="{ showDeleteModal: false }">
  <button @click="showDeleteModal = true" type="button">Delete Account</button>
  <div x-show="showDeleteModal" x-cloak ...>
    <form method="post" action="{% url 'delete_account' %}">
      {% csrf_token %}
      <button type="submit">Permanently Delete My Account</button>
    </form>
    <button @click="showDeleteModal = false">Cancel</button>
  </div>
</div>
```

### Cascade coverage

`User.delete()` cascades via FK `on_delete=CASCADE`:
- `Beneficiary` (owner FK)
- `EstateExecutor` (owner OneToOneField)
- `BeneficiaryAssignment` → via `Beneficiary` or item's owner cascade
- `EstateChangeLog` (owner FK)
- All `DynamicCollectionItem` and related records

No manual deletion needed — ORM CASCADE handles all estate PII.

### Reference files

- `src/config/views.py` — existing profile view
- `src/config/urls.py` — URL config
- `templates/pages/profile.html` — profile template (standalone, not extending base)
- `src/my_garage/api/selectors.py` — `get_estate_dashboard_context`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Profile view now calls `get_estate_dashboard_context(user)` — reuses the same 3-query selector from Story 1.4 with no additional DB cost beyond what the profile already issued
- Added `estate_executor_name` to context (beyond the story spec) so the executor card can display the name, not just a boolean; the test caught this gap immediately in RED phase
- `delete_account` order: `logout(request)` before `user.delete()` — session is cleared before the user row is removed, avoiding any FK or session lookup issues
- CASCADE coverage is complete via FK `on_delete=CASCADE` on all estate models — no manual deletion needed
- 533 tests total (24 new: 8 unit + 16 functional), 0 regressions

### File List

- `src/config/views.py` — `profile` view calls estate context; new `delete_account` view; added `logout`, `require_POST`, `get_estate_dashboard_context` imports
- `src/config/urls.py` — added `path("accounts/delete/", views.delete_account, name="delete_account")`
- `templates/pages/profile.html` — Card 4 (Estate & Legacy) + Card 5 (Danger Zone with Alpine.js delete modal)
- `tests/unit/test_profile_estate_context.py` — 8 unit tests for profile view context
- `tests/functional/test_profile_estate_story1_5.py` — 16 functional tests

### Change Log

- 2026-06-08: Story 1.5 implemented — profile estate card, Danger Zone delete-account modal, cascade PII deletion (24 new tests, 533 suite)
