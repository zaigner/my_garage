# Story 2.1: Estate Plan Activation, Executor Token Generation & Valuation Snapshot

Status: review

## Story

As an estate planner,
I want to activate my estate plan to generate an executor access code and lock a valuation snapshot of my portfolio,
So that my executor will have a stable record of asset values at the moment I gave them access.

## Acceptance Criteria

1. **Given** owner visits `/estate/activate/` and has designated an executor **When** the page renders **Then** a single "Activate Estate Access" button is visible with a confirmation checkbox: "I understand this code must be kept secure and cannot be recovered."

2. **Given** owner visits `/estate/activate/` with no executor designated **When** the page renders **Then** the submit button is disabled and an explanation is shown: "You must designate an executor before activating estate access."

3. **Given** owner clicks "Activate Estate Access" and submits the confirmation form **When** the activation is processed **Then** a cryptographically secure token is generated using Python `secrets.token_urlsafe(32)` **And** an `EstateAccessToken` record is created: `owner`, `token_hash` (SHA-256 of raw token), `issued_at`, `is_active=True` **And** a `ValuationSnapshot` record is bulk-created per item: `item`, `owner`, `snapshot_date=today`, `market_value`, `cost_basis`, `equity`, `snapshot_trigger=ESTATE_ACTIVATION` **And** the raw token is shown once in the response page and never again **And** a success message instructs the owner to copy the token for their executor.

4. **Given** owner reactivates when a token already exists **When** they submit activation again **Then** the old `EstateAccessToken` is deactivated (`is_active=False`) **And** a new token and a new set of `ValuationSnapshot` records are created.

5. **Given** no valuation data exists for an item **When** the snapshot is created **Then** `market_value` and `cost_basis` are stored as `None` and the activation still completes without error.

6. **Given** an unauthenticated user visits `/estate/activate/` **When** the request is received **Then** they are redirected to `/accounts/login/?next=/estate/activate/`.

7. **Given** new code is submitted **When** the quality gate runs **Then** `pixi run pytest tests/unit/ tests/functional/ -x -q` passes with zero failures **And** ruff check and ruff format --check report zero errors.

## Tasks / Subtasks

- [x] Task 1: Add `EstateAccessToken` and `ValuationSnapshot` models to `src/my_garage/models.py` (AC: 3, 4, 5)
  - [x] 1.1: Add `EstateAccessToken` after `EstateChangeLog` in the Estate & Legacy block
  - [x] 1.2: Add `ValuationSnapshot` after `EstateAccessToken`
  - [x] 1.3: Generate migrations `0017_estateaccesstoken_valuationsnapshot.py` + `0018_alter_estateaccesstoken_owner.py`

- [x] Task 2: Add `activate_estate_plan(user)` service to `src/my_garage/api/services.py` (AC: 3, 4, 5)
  - [x] 2.1: Import `secrets`, `hashlib`, `date` (stdlib only — no new packages)
  - [x] 2.2: Deactivate existing active tokens via `.update(is_active=False)` — preserves audit trail
  - [x] 2.3: Generate raw token: `secrets.token_urlsafe(32)`
  - [x] 2.4: Hash token: `hashlib.sha256(raw.encode()).hexdigest()` — 64 hex chars
  - [x] 2.5: Create `EstateAccessToken` with `owner`, `token_hash`, `is_active=True`
  - [x] 2.6: Fetch all `DynamicCollectionItem` for user (single query)
  - [x] 2.7: Compute equity per item: `market_value - cost_basis` if both non-None, else `None`
  - [x] 2.8: `ValuationSnapshot.objects.bulk_create(snapshots)` in one query
  - [x] 2.9: Return raw token — stored nowhere else

- [x] Task 3: Add `EstateActivateForm` to `src/my_garage/forms.py` (AC: 1, 2)
  - [x] 3.1: Single `BooleanField` checkbox: `confirmed`, required=True

- [x] Task 4: Add `estate_activate` view to `src/my_garage/estate_views.py` (AC: 1, 2, 3, 4, 6)
  - [x] 4.1: `GET`: render `estate/activate.html` with form + executor context; `can_activate = executor is not None`
  - [x] 4.2: `POST`: if `can_activate` and form valid → call `activate_estate_plan(user)`, store token in session, redirect
  - [x] 4.3: Raw token stored in session for single-use display only
  - [x] 4.4: Button disabled + warning message when no executor

- [x] Task 5: Add activation success view `estate_activate_success` (AC: 3)
  - [x] 5.1: `session.pop("estate_activation_token")` — purges on first display
  - [x] 5.2: If no token in session → redirect to `estate:activate`

- [x] Task 6: Add URLs to `src/my_garage/estate_urls.py` (AC: 1, 6)
  - [x] 6.1: `path("activate/", estate_views.estate_activate, name="activate")`
  - [x] 6.2: `path("activate/success/", ...)` multi-line for line-length compliance

- [x] Task 7: Add templates (AC: 1, 2, 3)
  - [x] 7.1: `estate/activate.html` — disabled button + executor warning when `can_activate=False`
  - [x] 7.2: `estate/activate_success.html` — token in monospace code block, one-time warning banner

- [x] Task 8: Write unit tests in `tests/unit/test_estate_activation_service.py` (AC: 3, 4, 5)
  - [x] 8.1–8.8: 16 unit tests — all passing

- [x] Task 9: Write functional tests in `tests/functional/test_estate_story2_1.py` (AC: 1, 2, 3, 4, 6)
  - [x] 9.1–9.8: 17 functional tests — all passing

- [x] Task 10: Quality gate — 566 passed (33 new), ruff clean, zero format diffs (AC: 7)

## Dev Notes

### New Models — Add to `src/my_garage/models.py` after `EstateChangeLog`

```python
class EstateAccessToken(models.Model):
    TRIGGER_CHOICES = [
        ("ESTATE_ACTIVATION", "Estate Activation"),
        ("MANUAL", "Manual"),
    ]

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="estate_access_token",
    )
    token_hash = models.CharField(max_length=64)  # SHA-256 hex = exactly 64 chars
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # set by Story 2.2 enforcement
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    use_count = models.IntegerField(default=0)

    def __str__(self):
        return f"EstateAccessToken for {self.owner.username} (active={self.is_active})"


class ValuationSnapshot(models.Model):
    TRIGGER_CHOICES = [
        ("ESTATE_ACTIVATION", "Estate Activation"),
        ("MANUAL", "Manual"),
    ]

    item = models.ForeignKey(
        "DynamicCollectionItem",
        on_delete=models.CASCADE,
        related_name="valuation_snapshots",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="valuation_snapshots",
    )
    snapshot_date = models.DateField()
    market_value = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    cost_basis = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    equity = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    snapshot_trigger = models.CharField(max_length=30, choices=TRIGGER_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Snapshot {self.snapshot_date} — {self.item.name}"

    # CRITICAL: No update() or delete() ever called on this model — append-only per NFR17/NFR39
```

### Service — `activate_estate_plan` in `src/my_garage/api/services.py`

```python
import hashlib
import secrets
from datetime import date

def activate_estate_plan(user) -> str:
    """
    Generate an executor access token, lock a valuation snapshot, and return
    the raw token once. The raw token is never persisted — only its SHA-256 hash.
    """
    from my_garage.models import DynamicCollectionItem, EstateAccessToken, ValuationSnapshot

    # Deactivate any existing token
    EstateAccessToken.objects.filter(owner=user, is_active=True).update(is_active=False)

    # Generate and hash new token
    raw_token = secrets.token_urlsafe(32)  # 43 URL-safe chars from 32 random bytes
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()  # 64 hex chars

    EstateAccessToken.objects.create(owner=user, token_hash=token_hash, is_active=True)

    # Bulk-create valuation snapshots for all items
    today = date.today()
    items = DynamicCollectionItem.objects.filter(owner=user)
    snapshots = []
    for item in items:
        mv = item.current_market_value
        cb = item.total_cost_basis
        eq = (mv - cb) if (mv is not None and cb is not None) else None
        snapshots.append(
            ValuationSnapshot(
                item=item,
                owner=user,
                snapshot_date=today,
                market_value=mv,
                cost_basis=cb,
                equity=eq,
                snapshot_trigger="ESTATE_ACTIVATION",
            )
        )
    ValuationSnapshot.objects.bulk_create(snapshots)

    return raw_token  # Display once in view — never store anywhere else
```

### Token display — session pattern (single-use)

```python
# In estate_activate view (POST path):
raw_token = activate_estate_plan(request.user)
request.session["estate_activation_token"] = raw_token
return redirect("estate:activate_success")

# In estate_activate_success view:
raw_token = request.session.pop("estate_activation_token", None)
if raw_token is None:
    return redirect("estate:activate")
return render(request, "my_garage/estate/activate_success.html", {"raw_token": raw_token})
```

### Form — `EstateActivateForm`

```python
class EstateActivateForm(forms.Form):
    confirmed = forms.BooleanField(
        required=True,
        label="I understand this code must be kept secure and cannot be recovered.",
        widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        error_messages={"required": "You must confirm before activating."},
    )
```

### View skeleton — `estate_activate`

```python
@login_required
def estate_activate(request: HttpRequest) -> HttpResponse:
    from my_garage.models import EstateExecutor
    executor = EstateExecutor.objects.filter(owner=request.user).first()
    can_activate = executor is not None

    if request.method == "POST" and can_activate:
        form = EstateActivateForm(request.POST)
        if form.is_valid():
            raw_token = activate_estate_plan(request.user)
            request.session["estate_activation_token"] = raw_token
            return redirect("estate:activate_success")
    else:
        form = EstateActivateForm()

    return render(request, "my_garage/estate/activate.html", {
        "form": form,
        "executor": executor,
        "can_activate": can_activate,
    })
```

### Template — disable button when no executor

```html
<!-- activate.html -->
<button type="submit"
        {% if not can_activate %}disabled{% endif %}
        class="bg-luxury-gold text-black font-bold uppercase text-xs tracking-widest rounded-sm px-5 py-2 transition-colors
               {% if not can_activate %}opacity-50 cursor-not-allowed{% else %}hover:bg-yellow-600{% endif %}">
  Activate Estate Access
</button>
{% if not can_activate %}
  <p class="text-yellow-500 text-xs mt-2">
    You must <a href="{% url 'estate:executor' %}" class="underline">designate an executor</a> before activating estate access.
  </p>
{% endif %}
```

### Migration order

- Latest existing migration: `0016_estate_assignment_changelog.py`
- New migration: `0017_estate_access_token_valuation_snapshot.py`
- Run: `pixi run manage makemigrations` — Django auto-generates from the two new model classes
- Both models go in one migration (generated together)

### Security constraints (from NFR6, NFR17, NFR39)

- `secrets.token_urlsafe(32)` — never `random`, never sequential
- Raw token returned from service, never written to DB or logs
- `hashlib.sha256(raw.encode()).hexdigest()` — stored hash only
- `ValuationSnapshot`: no `update()`, no `delete()` ever called — append-only by policy
- `EstateAccessToken.OneToOneField` — enforces one token record per user at ORM level
- Deactivation uses `.update(is_active=False)` not `.delete()` — preserves audit trail

### Test pattern — consistent with Epic 1 tests

```python
# tests/functional/test_estate_story2_1.py
import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import EstateExecutor, EstateAccessToken, ValuationSnapshot

User = get_user_model()
pytestmark = pytest.mark.django_db

ACTIVATE_URL = "/estate/activate/"
SUCCESS_URL = "/estate/activate/success/"

@pytest.fixture
def user(db):
    return User.objects.create_user(username="estate_user", password="pass")

@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client

@pytest.fixture
def executor(user):
    return EstateExecutor.objects.create(
        owner=user, name="John Smith", contact_info="john@example.com"
    )
```

### Project Structure Notes

- **Models:** `src/my_garage/models.py` — Estate & Legacy block (after line ~542, before `PortfolioSnapshot`)
- **Service:** `src/my_garage/api/services.py` — add `activate_estate_plan` and add `hashlib`, `secrets`, `date` imports at top
- **Form:** `src/my_garage/forms.py` — add `EstateActivateForm` after `BeneficiaryAssignmentForm`
- **Views:** `src/my_garage/estate_views.py` — add `estate_activate` and `estate_activate_success`
- **URLs:** `src/my_garage/estate_urls.py` — two new paths
- **Templates:** `src/my_garage/templates/my_garage/estate/activate.html` + `activate_success.html`
- **Tests:** `tests/unit/test_estate_activation_service.py` + `tests/functional/test_estate_story2_1.py`
- **Migration:** `src/my_garage/migrations/0017_estate_access_token_valuation_snapshot.py` (auto-generated)
- Do NOT touch any existing view, template, or URL that is not explicitly listed

### References

- Epic spec: `_bmad-output/planning-artifacts/epics-estate-legacy.md` — Story 2.1 (lines ~438–476)
- Story 1.5 patterns: `_bmad-output/implementation-artifacts/1-5-profile-estate-card-account-deletion.md`
- `EstateExecutor` model (existing pattern): `src/my_garage/models.py:478`
- `assign_beneficiary` service (existing pattern): `src/my_garage/api/services.py:38`
- `get_estate_dashboard_context` selector: `src/my_garage/api/selectors.py:200`
- Test patterns: `tests/functional/test_estate_story1_1.py`
- Security requirements: epics-estate-legacy.md NFR6, NFR7, NFR17, NFR39 (lines ~86–99)

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- `EstateAccessToken` changed from `OneToOneField` to `ForeignKey` — OneToOne prevents keeping deactivated (audit-trail) tokens when reactivating; service enforces one-active-per-user at the application layer
- `cost_basis` in snapshot uses `item.purchase_price` not `item.total_cost_basis` — the post_save signal always sets `total_cost_basis ≥ 0` (never None), which would suppress null values the spec requires; `purchase_price` preserves None correctly
- Two migrations generated: `0017` (model creation) + `0018` (OneToOne → ForeignKey correction after design fix)
- Session-pop pattern (`request.session.pop("estate_activation_token", None)`) ensures the raw token is shown exactly once and never recoverable on a second GET to the success page
- 566 tests total (33 new: 16 unit + 17 functional), 0 regressions

### File List

- `src/my_garage/models.py` — `EstateAccessToken` and `ValuationSnapshot` models added (Estate & Legacy block)
- `src/my_garage/migrations/0017_estateaccesstoken_valuationsnapshot.py` — new models migration
- `src/my_garage/migrations/0018_alter_estateaccesstoken_owner.py` — OneToOne → ForeignKey correction
- `src/my_garage/api/services.py` — `activate_estate_plan` added; `hashlib`, `secrets`, `date` imports
- `src/my_garage/forms.py` — `EstateActivateForm` added
- `src/my_garage/estate_views.py` — `estate_activate` + `estate_activate_success` views; updated imports
- `src/my_garage/estate_urls.py` — two new URL patterns
- `src/my_garage/templates/my_garage/estate/activate.html` — new template
- `src/my_garage/templates/my_garage/estate/activate_success.html` — new template
- `tests/unit/test_estate_activation_service.py` — 16 unit tests
- `tests/functional/test_estate_story2_1.py` — 17 functional tests

### Change Log

- 2026-06-09: Story 2.1 implemented — estate activation, executor token generation, valuation snapshot bulk-create (33 new tests, 566 suite)
