---
title: "Addendum: First-Collection How-To Videos"
created: 2026-10-29
updated: 2026-10-29
---

# Addendum: First-Collection How-To Videos

Technical detail for architecture and story work, kept out of the brief. Line numbers are as of 2026-10-29 (commit `6e7bb76`), so they will drift.

**Key constraints:**
- Playwright isn't installed.
- Videos are static files built into the Docker image.
- Video 3 needs the Gemini call replaced with a fixed response.
- Recordings are phone-size.
- One link bug must be fixed first.

## Defect to fix first

`templates/pages/onboarding.html:190`: the step-2 "View →" link is `{% url 'collections:collection_list' 'automobiles' %}`. `collection_list` uses `get_object_or_404(CollectionType, slug=..., owner=request.user)`, so a guest without an Automobiles collection gets a 404 from the guided path.

## Verified technical facts

**Two ways to create a collection.**
- *Starter collections.* Seven are defined in `src/my_garage/collection_blueprints.py`: Automobiles, Horology Salon, The Gun Safe, Coin Collection, Wine Collection, Hand Bags and Football Cards. Guests adopt them on `/welcome/` (POST to `onboarding`) or on `/collections/templates/` (`collection_templates`, `src/my_garage/views.py:161`). Both pages call `provision_collections()`.
- *Custom builder.* `/collections/create/` (`collection_type_create`). It includes an AI field-suggestion panel, "Collection Curator" (`src/my_garage/templates/my_garage/collection_type_form.html:140`), that calls `generate_collection_schema` (Gemini).

**Recording v1: external API calls.**
- `collection_item_add` (`src/my_garage/views.py:384`) starts no Celery tasks and calls no external APIs.
- The `.delay()` calls in `views.py` are at line 562 (valuation refresh), line 602 (enrich) and line 885 (OCR), all in other views.
- The custom builder's field-suggestion call is therefore the only external call in v1 (see Recording pipeline notes).

**Static hosting.**
- WhiteNoise 6.12.0 handles `HTTP_RANGE` and returns 206 responses (`whitenoise/responders.py:89–150`). iOS Safari needs this to play `<video>`.
- Production uses `CompressedManifestStaticFilesStorage` (`src/config/settings/production.py:20`).
- `tests/unit/test_static_references.py` checks that every `{% static %}` reference exists, because a missing referenced file causes a 500 under manifest storage.

**Custom builder at phone width (390 px).** `src/my_garage/templates/my_garage/collection_type_form.html` falls back to one column:
- The header grid (line 103) is `md:grid-cols-2`.
- The field rows (line 259) are `md:grid-cols-4`. On a phone, each field row stacks four inputs vertically, which is why Video 3 should change only one or two fields.
- The Collection Curator input and button share one flex row (line 146). The input is narrow but usable.

## Recording pipeline notes

**Prerequisites.**
- Playwright isn't installed. The Test Architect (TEA) config setting `tea_use_playwright_utils: true` is only a BMAD setting.
- Neither `pixi.toml` nor `pyproject.toml` lists Playwright, and there's no `tests/e2e/`.
- Add `playwright` and `ffmpeg` through pixi, then install the browser (`playwright install chromium`).

**Pipeline steps** (`pixi run record-tutorials`):
1. Start the app with a seeded demo user and fixed data.
2. Replace the field-suggestion call with a fixed response.
3. Run the scripted flows.
4. Convert Playwright's WebM output to H.264 MP4.
5. Write the files to `static/tutorials/`.

**Field-suggestion interception (Video 3).**
- Video 3's builder page fetches `/collections/api/generate-schema/?topic=…&description=…` (`collection_type_form.html:378`; URL name `collections:generate_collection_schema`, `src/my_garage/collection_urls.py:18`).
- Intercept it with Playwright `page.route()` and return a fixed JSON schema.
- Without the interception, each re-recording shows different fields and consumes Gemini quota.

**Output format.**
- Playwright records WebM (VP8). Convert it to H.264 MP4 with `-movflags +faststart` so playback starts before the whole file downloads, and set the pixel format to `yuv420p` for iOS compatibility.
- Generate a poster frame (JPEG) for each video, for the `<video poster>` attribute.
- Keep the files small. Static files are built into the Docker image, and image pulls on the Raspberry Pi cluster nodes (slowest on aignerpi-2) already take minutes. That is the reason for the brief's 15 MB budget.

**Viewport.**
- Phone, 390×844 (decided 2026-10-29).
- Record with `device_scale_factor` 2 or higher, then downscale in ffmpeg to keep text sharp.

**Cursor.** Playwright doesn't draw the mouse pointer in recordings. Use `page.add_init_script()` to inject a CSS cursor element that follows the mouse, plus a click ripple.

**Captions.**
- Draw them as page overlays timed to script steps, for example a `caption("Pick what you collect")` helper that shows a styled element and waits.
- Match the collection theme: gold (`#D4AF37`) text on navy (`#0B1026`), Playfair Display.

**Repeatable results.**
- Seed a fixed demo user with fixed item data and a photo fixture committed to the repo.
- Use a throwaway SQLite database for each recording run. Never record against `db.sqlite3`.

**Where the videos go.**
- Video 1: `templates/pages/onboarding.html` (starter picker section) and `src/my_garage/templates/my_garage/collection_templates.html`.
- Video 2: the empty state in `src/my_garage/templates/my_garage/collection_list.html:174` ("Add your first item to begin tracking this collection.").
- Video 3: `src/my_garage/templates/my_garage/collection_type_form.html`, create mode only, not when editing.
- A single `templates/includes/_tutorial_video.html` partial that accepts `src`, `poster` and `title` keeps the markup in one place.

## Considered and rejected

- **Hand-recorded screencasts.** Rejected because UI changes would make them stale. For example, the Generate UI removal (PR #18) and the collection theme pass would each have forced a manual re-recording.
- **YouTube or external hosting.** Rejected because the audience is friends and family behind Cloudflare Access. In-app static files keep everything private and need no extra accounts.
- **Media folder hosting.** Rejected because `media/` holds user uploads served to their owners. Tutorials are shared app assets and belong in `static/`.
- **Voiceover.** Deferred, not rejected. It adds an audio-generation step and possibly a paid API, and captions cover the muted-phone case.

## Parked for later versions

- Desktop-size recordings: either a second set of files chosen by screen width, or a single desktop-only set.
- A valuation video, which needs Marketcheck interception.
- A receipt-upload video, which needs a fixture receipt image and an OCR stub.
- Running the recorder in CI as a smoke check for UI drift.
- Estate & Legacy beneficiary walkthrough video.
