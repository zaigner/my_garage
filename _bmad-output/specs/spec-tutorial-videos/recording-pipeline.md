# Recording pipeline

How `pixi run record-tutorials` produces the videos (CAP-6), plus the embed partial (CAP-5). This is guidance for implementation. The binding contract is in SPEC.md.

## Prerequisites

- Playwright and ffmpeg live in the `tutorials` pixi feature and environment (Story 2), and `record-tutorials` installs Chromium on first run. The `prod` environment includes no features, so none of this reaches the image.
- BMAD's `tea_use_playwright_utils: true` is only a config setting. It doesn't mean Playwright is installed.

## Steps

1. Create a throwaway SQLite database, migrate it, and seed a fixed demo user with fixed item data. The Video 2 photo is a fixture file committed to the repo.
2. Start the app against that database.
3. Use Playwright `page.route()` to intercept `/collections/api/generate-schema/?topic=…&description=…` (URL name `collections:generate_collection_schema`) and return a fixed JSON schema.
4. Run the three scripted flows, each once per variant (phone, then desktop), in fresh browser contexts with the same seeded data.
5. Convert Playwright's WebM (VP8) output to H.264 MP4 with `-pix_fmt yuv420p -movflags +faststart`. Extract one JPEG poster per recording. File names: `videoN.mp4` and `videoN.jpg` for the phone variant (unchanged from Story 2), `videoN-desktop.mp4` and `videoN-desktop.jpg` for the desktop one.
6. Write everything to `static/tutorials/` and delete the throwaway database.

With a video name (`pixi run record-tutorials video2`), the run performs only that flow, in both variants, and writes only that video's four files. ffmpeg never produces byte-identical files from two encodes. A full run therefore rewrites all three files even when only one flow changed, and every rewrite adds to git history.

If a selector times out or a step fails, the run exits non-zero. A failure usually means the UI has drifted.

## Capture

- Variants: a profile per variant sets the viewport, the encode size and the caption copy.
  - Phone: 390×844, recorded at `device_scale_factor` 2, then downscaled in ffmpeg so text stays sharp.
  - Desktop: about 880×550, also recorded at DPR 2 and downscaled. It must be at least 768px wide so the desktop nav (`md:flex` in `_nav.html`) shows. Settle the exact size by checking frames at the real player width.
- Flows: a flow's steps may branch on the variant where the layouts differ. For example, Video 1 opens the hamburger (`button[aria-label="Navigation menu"]`) on the phone, but at 768px and above the desktop nav (`md:flex`) is already showing. Check how it lists collections (inline or in a dropdown) before scripting that step. Fixed glide coordinates such as `glide(rec, 195, 420, …)` are phone-specific. Keep the same beats and caption order in both variants. Caption copy may say "Click" on desktop where the phone says "Tap".
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

**Variant selection (CAP-7).** The partial also takes `desktop_src` and `desktop_poster`, built at the call site with the `{% static … as name %}` form, so the static-reference test guards them too.
- The collapsed card's thumbnail is two `<img>` elements toggled with Tailwind (`md:hidden` and `hidden md:block`). This is pure CSS, so it stays right on resize, and lazy-loading skips the hidden one.
- When Play is pressed, the existing Alpine handler checks `window.matchMedia('(min-width: 768px)')`, sets the `<video>`'s `src` and `poster`, then calls `load()` and `play()`. With `preload="none"`, nothing downloads before that.
- The desktop player gets a wider max width than the phone's 280px, up to the page column.

## Size

All the MP4s together, both variants of every video, stay at or under 6 MB (SPEC constraint). After writing its output, the run sums every MP4 in `static/tutorials/` and exits non-zero if the total is over 6 MB. It sums them all even when only one video was re-recorded.

Starting encoder settings: x264 with `-crf 28` to `-crf 30`, `-preset slow`, and `-tune stillimage` or `-tune animation` (whichever gives the smaller file for the same legibility), at 15–24 fps. Mostly static UI compresses well, so expect about 1–2 MB per video. Story 2 measured the Video 1 phone variant at 193 KB (CRF 26, 20 fps, `-tune animation`). Story 3 measures the desktop variant, which has more pixels and will be larger. If captions are no longer legible on a phone at a size that fits the budget, ask the owner before raising the budget.
