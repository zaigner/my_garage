---
title: 'Desktop variant for tutorial videos'
type: 'feature'
created: '2026-11-03'
status: 'done'
baseline_commit: '46163bdb883dbe08446f25b14d1350679b68a137'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/specs/spec-tutorial-videos/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-tutorial-videos/recording-pipeline.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Video 1 exists only as a 390×844 phone recording. On a laptop it plays in a 280px-wide portrait strip that shows a layout the viewer isn't looking at (CAP-7).

**Approach:** Give the recorder a desktop profile beside the phone one, and re-record Video 1 in both variants. The embed partial shows the right thumbnail with CSS (768px) and loads the matching MP4 and poster only when Play is pressed. The desktop player is wider. Phone files keep their names, and the desktop files are `video1-desktop.mp4` and `video1-desktop.jpg`.

**Decisions (2026-11-03, by user):**
- Keep 768px. `_nav.html` has no desktop nav (the hamburger is the only nav at every width), so both variants open the hamburger and share one flow. 768px stays because it's the `md` breakpoint where the collection grids and page headers change. This PR corrects the false nav rationale in SPEC.md (CAP-7 and Constraints) and in recording-pipeline.md ("Capture" and "Variant selection").
- Keep the full spec, at about 2,300 tokens.

## Boundaries & Constraints

**Always:**
- Both variants run from the same seeded data and the same flow, with the same beats and caption order. Desktop captions say "Click" where the phone says "Tap".
- The desktop viewport is at least 768px wide. Its width is settled by checking frames scaled to about 620px, starting near 880. Its height is whatever keeps every element the flow taps in view, including the nav dropdown's "Your Collections" links.
- `record-tutorials video1` writes all four Video 1 files, or none of them if either variant fails.
- The `<video>` has no `src`, `<source>` or `poster` until Play is pressed. The handler picks the variant with `matchMedia('(min-width: 768px)')`, sets `src` and `poster`, then calls `load()` and `play()`.
- Every rule from Story 2 still holds: no autoplay, `playsinline`, `preload="none"`, page-view-only dismiss, the request allowlist, fixed waits, the 6 MB total, and an unchanged prod env.

**Never:** Videos 2 and 3. User-agent or server-side variant choice. Switching variants mid-playback. Re-recording one variant alone.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Re-record | `record-tutorials video1` | `video1{,-desktop}.{mp4,jpg}` written; exit 0 | N/A |
| Desktop step fails | Phone recorded, desktop selector missing | None of the four files touched | Exit non-zero naming the variant and step |
| Wide viewport | ≥768px, Play pressed | Desktop thumbnail shown; only `video1-desktop.mp4` requested | N/A |
| Narrow viewport | <768px (phone, or a narrow desktop window) | Phone thumbnail; only `video1.mp4` requested | N/A |
| Over budget | Six MP4s total > 6 MB | Files written | Exit non-zero with the size |

</frozen-after-approval>

## Code Map

- `scripts/record_tutorials/harness.py` -- `VIEWPORT` (L26) is used by both the login and recording contexts. `Recorder.mouse_xy` starts at (195, 700), which is below a 550px-tall viewport. `record_one` copies the files into `OUT_DIR` right after encoding, and this must wait until both variants have encoded. `StepError` messages need the variant name.
- `scripts/record_tutorials/encode.py` -- the module constants `WIDTH, HEIGHT` feed `encode_args`'s scale filter. These must become per-variant. Keep FPS 20, CRF 26, `-tune animation` and lanczos unless the desktop size forces a change.
- `scripts/record_tutorials/overlays.py` -- `INIT_SCRIPT` hard-codes the cursor start `[195, 700]`, which must come from the variant. The caption box is a fixed 350px at 21px type. Keep it unless the desktop frames show it too small.
- `scripts/record_tutorials/flows.py` -- `video1`'s `glide(rec, 195, 420, …)` is phone-specific: use a variant-relative point such as the viewport centre. The caption "Tap two starters" becomes "Click…" on desktop. The other copy stays the same.
- `templates/includes/_tutorial_video.html` -- add the `desktop_src` and `desktop_poster` params. There are two thumbnails: the phone one is `w-12 h-[104px]` with `md:hidden`, and the desktop one is landscape with `hidden md:block`. Move the URLs to `data-*` attributes on the `<video>` and drop the static `<source>` and `poster`. The player's max width is `280px` for phone and the desktop encode width for desktop, bound on the variant chosen, not with an `md:` class. The page column is ~624px on `/welcome/` (`max-w-2xl`) and up to 1024px on templates (`max-w-5xl`), so capping at the encode width avoids upscaling.
- `templates/pages/onboarding.html:85-87`, `src/my_garage/templates/my_garage/collection_templates.html:47-50` -- add `{% static 'tutorials/video1-desktop.*' as … %}` and pass them to the include.
- `templates/includes/_nav.html` -- the dropdown is `absolute` inside a `sticky` nav, so page scrolling can't bring its lower links into view. That is what limits the desktop height.
- `tests/unit/test_static_references.py:45` -- extend the expected set with both desktop files on both pages.
- `tests/functional/test_tutorial_video_embed.py` -- `test_video_attributes` and `test_source_and_dismiss_without_storage` assert a static `poster=` and the MP4 in the HTML. Rewrite these for the `data-*` form.
- `tests/unit/test_record_tutorials.py` -- tests that stub `_record` or `record_one` (L104-190) and the `encode.WIDTH` assertion (L38) change with the variant signature.

## Tasks & Acceptance

**Execution:**
- [x] `scripts/record_tutorials/variants.py` -- a frozen `Variant` (name, viewport, file suffix, tap verb, cursor start) with `PHONE` (390×844, suffix `""`, "Tap") and `DESKTOP` (≈880 wide, suffix `-desktop`, "Click"), plus `VARIANTS = (PHONE, DESKTOP)`.
- [x] `harness.py`, `encode.py`, `overlays.py` -- thread the variant through the contexts, video size, encode size, cursor start and log or error text. `record_one` records and encodes both variants in `work/` and then copies all four files.
- [x] `flows.py` -- `video1` uses `rec.variant` for the glide point and the tap verb. Keep one flow for both variants.
- [x] `_tutorial_video.html` + both call sites -- the two thumbnails, the `data-*` URLs, the Play handler, and the variant-bound player width.
- [x] Tests -- matrix rows 1, 2 and 5 at harness level, with the browser and ffmpeg stubbed. Encode args per variant. Static references for both desktop files on both pages. A functional embed test for both thumbnails, the `data-*` URLs, and no `src`, `<source>` or `poster` on the `<video>`.
- [x] Settle the desktop viewport. Record with `TUTORIALS_DEBUG_DIR`, scale the frames to about 620px wide, and check that captions and UI text are legible and that the Wine Collection nav link is tapped on screen.
- [x] `static/tutorials/video1{,-desktop}.{mp4,jpg}` -- re-record and commit all four.
- [x] `SPEC.md`, `recording-pipeline.md` -- replace the "desktop nav" rationale with the grid/header breakpoint, and drop the hamburger-branch guidance.

**Acceptance Criteria:**
- Given a clean checkout, when `pixi run record-tutorials` runs twice, then both runs exit 0 in under 10 minutes and give the same step and caption log per variant.
- Given `video1-desktop.mp4` at about 620px wide, when it is watched, then two starters are clicked, added and shown in the menu, with the captions and UI text legible.
- Given `/welcome/` at 1280px and at 390px in Chrome, when Play is pressed, then the network log shows only the matching MP4.

## Implementation Notes

- **Viewport:** desktop is 880×680. At 600 tall, the nav dropdown's Wine Collection link sat on the bottom edge, so the height went up to 680. The desktop cursor starts at (440, 600).
- **DPR 1, not 2:** with DPR 2 and a 2× `record_video_size`, Playwright drew the page at 1× in the top-left quarter of the frame. The Story 2 poster committed to `main` shows exactly this (page in the corner, grey elsewhere), and Story 2's frame check missed it. Both variants now record at DPR 1 with the record size equal to the viewport, so no downscale is needed. recording-pipeline.md "Capture" is updated to match.
- **DB reset per variant:** the phone run adopts the starters, so the desktop run would open on an already-filled vault. `run()` copies the seeded DB to `pristine.sqlite3` after seeding, and `record_one` restores it before each variant. This works because runserver's connections close after each request (CONN_MAX_AGE 0) and SQLite runs in the default rollback-journal mode.
- **Sizes:** `video1.mp4` 525 KB, 390×844, 60.7 s. `video1-desktop.mp4` 662 KB, 880×680, 60.75 s. The MP4 total is 1.16 MB of the 6 MB budget. Encoder settings are unchanged for both: H.264 Main, `yuv420p`, `+faststart`, 20 fps, CRF 26, `-preset slow -tune animation`, lanczos, no audio, poster at 1.5 s. The phone MP4 grew from 193 KB because the page now fills the whole frame.
- **Frames:** desktop frames at 9, 33 and 50 s, scaled to 620 px wide, show legible captions and UI text. They cover the picker, "Added 2 collections" and the empty Wine Collection list. A phone frame at 33 s fills the frame.
- **Runs:** `record-tutorials video1` exited 0 four times, with the same per-variant step and caption log each time. A full run takes about 2 minutes.
- **Browser check (matrix rows 3–4):** a scratch Playwright script, not committed, loaded `/welcome/` in Chromium at 1280, 768, 767 and 390 px wide and pressed Play. At 768 px and up, only `video1-desktop.jpg` was visible and `video1-desktop.mp4` was the only MP4 requested, with a 598 px player. At 767 px and below, only `video1.jpg` and `video1.mp4`, with a 280 px player. Before Play, no MP4 was requested and only the visible thumbnail loaded. `scrollWidth` equalled the viewport width every time. Playwright isn't in the default env, so CI covers these rows only through the markup tests.
- **Gates (after review patches):** unit 547 passed and functional 726 passed. Lint and format are clean. The browser check re-ran after the aspect-ratio patch with the same requests: a 598×462 desktop player and a 280×606 phone player.
- **Not checked:** playback on a real laptop and iPhone is left for the owner.

## Spec Change Log

## Review Triage Log

Pass 1, 2026-11-03. Layers: Verification Gap (VG), Blind Hunter (BH), Edge Case Hunter (EC). I checked the Story 1 and 2 triage logs for earlier rejections, and BH12/EC4 matched one.

- VG1 medium → defer: the Play handler's variant choice is checked only as source text, so swapping the ternary or getting a dataset key wrong would pass every test. Covering it needs a browser test in CI, and Playwright lives only in the `tutorials` env. This story checked it by hand in Chromium at 1280, 768, 767 and 390 px (see Implementation Notes).
- BH1 low → patch: the desktop thumbnail was 96×65, the shape of 880×600, so `object-cover` cropped the 880×680 poster. It's now 96×74.
- BH2 low → patch: the "Embed partial" paragraph in recording-pipeline.md still listed `src, poster, title` and a static `poster=`. Updated.
- BH3 low → patch: SPEC.md L78 and recording-pipeline.md L57 still cited 193 KB (the corner-framed recording) and "Story 3 measures…". Both now give 525, 662 and 1,160 KB.
- BH4 medium → patch: the `[variant]` prefix was added in `_record`, which no test runs, and the desktop-failure test's stub wrote "[desktop]" itself while pre-creating only one file. The prefix now comes from `record_one`, the stub raises an unprefixed error, and the test pre-creates all four files and asserts they're unchanged.
- BH5 low → patch: `reset_db` was only counted. The tests now assert the order `reset, phone, reset, desktop`, and that the callback `run()` passes restores the seeded bytes.
- BH6, EC2 low → patch (a comment only): overwriting the SQLite file under a live runserver is safe only with CONN_MAX_AGE 0 and a rollback journal. Both are true today: neither is set in `base.py`, `local.py` or `tutorials.py`, and the flow ends on a finished page load, with a 500 ms wait before `ctx.close()`. A comment now says so, and no guard was added, because no drift has been shown.
- BH7, EC5 low → reject: the partial has no fallback when the desktop params are missing. Both call sites pass all four URLs, and Stories 4 and 5 record both variants. A `|default:` would hide a missing desktop file instead of surfacing it.
- BH8 low → reject: `max-w-[880px]` and the 768 in `matchMedia` repeat values defined elsewhere. Linking the template to `variants.py` adds plumbing, and the browser check measured a 598 px desktop player, wider than 280 and within the column.
- BH9 low → patch: with no static poster, the `<video>` opened at 300×150 and then jumped. A per-variant `aspect-[880/680]` or `aspect-[390/844]` now sits next to the max-width class. The re-check measured 598×462 and 280×606.
- BH10 low → patch: `encode_args` silently defaulted to PHONE. `variant` is now required.
- BH11 false: the story file is missing from the diff by design. The workflow gives the spec only to the edge-case layer, as its claims file.
- BH12, EC4 low → human, 2026-11-03: the `play()` promise is unhandled. Story 2 rejected this as BH11b/EC11. The owner chose to leave it as it is: the native controls stay visible for a retry, and the only cost is a console error.
- EC1 low → reject: `record_one` without `reset_db` would record the desktop variant on the DB the phone run changed. The only caller, `run()`, passes it, and leaving it out fails loudly, because the already-owned starter's input is gone and the selector times out naming the step.
- EC3 low → reject: a copy failing partway (disk full) could leave mixed variants. That's unlikely, a temp-file-and-replace fix adds machinery, and git restores the committed files.
- EC6 low → reject: a nav link below the viewport gives a `wait_for_url` timeout instead of an "off screen" message. The run still fails, naming the step "open Wine Collection", and 680 px keeps the link on screen today.

## Design Notes

The URLs stay `{% static … as … %}` at the call site so the static-reference test guards all four files. On the `<video>`, they move into `data-phone-src`, `data-desktop-src`, `data-phone-poster` and `data-desktop-poster`. A static `src` would let the browser pick a file before the viewport is checked. A static `poster` would fetch the phone poster on desktop.

## Verification

**Commands:**
- `pixi run record-tutorials video1` -- expected: exit 0, four files, an MP4 total under 6 MB.
- The four §16 gates -- expected: all pass.

**Manual checks:**
- Record the desktop variant's size and encoder settings here. The owner checks playback on a laptop and on an iPhone.
