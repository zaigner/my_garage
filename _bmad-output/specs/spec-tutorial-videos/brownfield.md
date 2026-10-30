# Brownfield notes

Code facts this feature depends on. All were verified at commit `6e7bb76` (2026-10-29), so the line numbers will drift.

## Defect (CAP-1)

- `templates/pages/onboarding.html:190`: the step-2 ("Get a market valuation") "View →" link is `{% url 'collections:collection_list' 'automobiles' %}`. It renders whenever `has_items` is true.
- `collection_list` uses `get_object_or_404(CollectionType, slug=..., owner=request.user)`, so this link 404s for any guest without an Automobiles collection.
- The view is `onboarding` in `src/config/views.py:179`. Its context today has `has_items`, `has_valuation`, `has_service`, `catalog`, `has_collections` and `all_adopted`, but no collection slug. It needs to pass the slug of a collection that holds one of the guest's items.
- The other checklist links already resolve for every guest: step 1 → `collections:collection_type_list`, step 3 → `collections:all_services`.

## Ways to create a collection

- **Starters.** Seven blueprints in `src/my_garage/collection_blueprints.py`: Automobiles, Horology Salon, The Gun Safe, Coin Collection, Wine Collection, Hand Bags, Football Cards. Guests adopt them on `/welcome/` (POST to `onboarding`) or `/collections/templates/` (`collection_templates`, `src/my_garage/views.py:162`). Both call `provision_collections()`.
- **Custom builder.** `/collections/create/` (`collection_type_create`, `views.py:226`). Its Collection Curator panel (`collection_type_form.html:140`, button `#generate-schema-btn`) fetches `/collections/api/generate-schema/` (`collection_type_form.html:378`; route at `src/my_garage/collection_urls.py:17–19`), which calls Gemini.

## External calls during the recorded flows

- `collection_item_add` (`views.py:384`) starts no Celery task and calls no external API.
- The `.delay()` calls in `views.py` (valuation refresh, enrich, OCR) are all in other views.
- So the schema suggestion request is the only external call in v1.

## Embed locations

| Video | Template | Where |
|---|---|---|
| 1 | `templates/pages/onboarding.html` | Starter picker section |
| 1 | `src/my_garage/templates/my_garage/collection_templates.html` | Above the picker |
| 2 | `src/my_garage/templates/my_garage/collection_list.html:174` | The `{% else %}` empty state ("Add your first item to begin tracking this collection.") |
| 3 | `src/my_garage/templates/my_garage/collection_type_form.html` | Create mode only, not edit |

`templates/includes/` currently holds only `_nav.html`.

## Phone layout of the custom builder

`collection_type_form.html` falls back to a single column at 390 px:

- The header grid (line 103) is `md:grid-cols-2`.
- Field rows (line 259) are `md:grid-cols-4`, so on a phone each row stacks four inputs vertically.
- The Curator input and button share one flex row (line 146). The input is narrow but usable.

## Static files and the image

- `STATICFILES_DIRS = [BASE_DIR / "static"]`, `STATIC_ROOT = staticfiles/` (`src/config/settings/base.py:105–107`).
- Production uses `CompressedManifestStaticFilesStorage` (`src/config/settings/production.py`), where a missing `{% static %}` target raises ValueError and returns a 500. `tests/unit/test_static_references.py` guards this.
- The Dockerfile copies `static/` into the builder stage and runs `collectstatic`. The runtime image ships only `staticfiles/`. Anything in `static/tutorials/` must be in the repo when the image is built.
- WhiteNoise 6.12 serves `HTTP_RANGE` with 206 responses (`whitenoise/responders.py:89–150`). iOS Safari `<video>` needs this.

## pixi

- `[environments]`: `default = ["dev"]`, `prod = []`. No `record-tutorials` task exists yet, and there's no `tests/e2e/`.
