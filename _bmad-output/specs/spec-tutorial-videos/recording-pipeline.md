# Recording pipeline

How `pixi run record-tutorials` produces the videos (CAP-6), plus the embed partial (CAP-5). This is guidance for implementation. The binding contract is in SPEC.md.

## Prerequisites

- None of this is installed yet. Add `playwright` and `ffmpeg` to `[feature.dev.dependencies]` in `pixi.toml` (the `prod` environment includes no features, so they stay out of the image). Then run `playwright install chromium`.
- BMAD's `tea_use_playwright_utils: true` is only a config setting. It doesn't mean Playwright is installed.

## Steps

1. Create a throwaway SQLite database, migrate it, and seed a fixed demo user with fixed item data. The Video 2 photo is a fixture file committed to the repo.
2. Start the app against that database.
3. Use Playwright `page.route()` to intercept `/collections/api/generate-schema/?topic=…&description=…` (URL name `collections:generate_collection_schema`) and return a fixed JSON schema.
4. Run the three scripted flows.
5. Convert Playwright's WebM (VP8) output to H.264 MP4 with `-pix_fmt yuv420p -movflags +faststart`. Extract one JPEG poster per video.
6. Write everything to `static/tutorials/` and delete the throwaway database.

With a video name (`pixi run record-tutorials video2`), the run performs only that flow and writes only that MP4 and poster. ffmpeg never produces byte-identical files from two encodes. A full run therefore rewrites all three files even when only one flow changed, and every rewrite adds to git history.

If a selector times out or a step fails, the run exits non-zero. A failure usually means the UI has drifted.

## Capture

- Viewport: 390×844, recorded with `device_scale_factor` ≥ 2, then downscaled in ffmpeg so text stays sharp.
- Cursor: Playwright doesn't draw the pointer. Inject a CSS cursor that follows the mouse, plus a click ripple, with `page.add_init_script()`.
- Captions: page overlays tied to script steps, for example a `caption("Pick what you collect")` helper that shows a styled element and waits a fixed time. Style them in the collection theme: gold `#D4AF37` text on navy `#0B1026`, Playfair Display. Fixed waits (no timing that depends on load speed) keep runs identical.

## Scripted flows

| Video | Title | Beats | Target length |
|---|---|---|---|
| 1 | Your vault in 60 seconds | On `/welcome/`, pick two starters, click "Add 2 to my vault", show where they appear | ~60 s |
| 2 | Your first item | Open an empty collection, open the add form, fill a few fields, attach the photo fixture, save, show the card | ~90 s |
| 3 | Build a collection for anything | `/collections/create/`, name a hobby no starter covers, ask Collection Curator, adjust one field, save, show the empty collection, end with a caption pointing to Video 2 | ~2 min |

- Video 3 captions call the suggested fields an example, because a guest who types the same hobby will get different fields from Gemini.
- Video 3 edits at most one or two fields, because field rows stack vertically at phone width.

## Embed partial

`templates/includes/_tutorial_video.html` takes `src`, `poster` and `title`. Markup: `<video controls playsinline preload="none" poster=…>`, with no `autoplay` and no `muted` autoplay trick. A dismiss control hides the embed for the current page view only, with no storage.

## Size

The three MP4s together stay at or under 6 MB (SPEC constraint). After writing its output, the run sums the sizes of all three files in `static/tutorials/` and exits non-zero if the total is over 6 MB. It sums all three even when only one video was re-recorded.

Starting encoder settings: x264 with `-crf 28` to `-crf 30`, `-preset slow`, and `-tune stillimage` or `-tune animation` (whichever gives the smaller file for the same legibility), at 15–24 fps. Mostly static UI compresses well, so expect about 1–2 MB per video. Story 2 measures Video 1 and records the settings it settles on. If captions are no longer legible on a phone at a size that fits the budget, ask the owner before raising the budget.
