---
title: 'Recorder harness, embed partial and Video 1'
type: 'feature'
created: '2026-11-02'
status: 'done'
baseline_commit: '8a4f78a19ef42fac7b27433c3dc0f97029a40613'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/specs/spec-tutorial-videos/SPEC.md'
  - '{project-root}/_bmad-output/specs/spec-tutorial-videos/recording-pipeline.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Guests choosing starter collections on `/welcome/` or `/collections/templates/` have nothing that shows them what adopting a collection does or where it then appears. There is also no way to produce such videos that survives UI churn (CAP-2, CAP-5, part of CAP-6).

**Approach:** Build `pixi run record-tutorials [video…]`. It migrates a throwaway SQLite DB and seeds a demo user, starts the app on it, drives Chromium with Playwright at 390×844 with cursor and caption overlays, encodes H.264 MP4 plus a JPEG poster into `static/tutorials/`, and enforces the 6 MB total. Build a shared embed partial. Record Video 1, "Your vault in 60 seconds", and embed it above both starter pickers. The MP4 and poster are committed in this PR.

**Decisions (2026-11-02, by user):**
- The embed is a collapsed card: a compact row with the poster thumbnail, the title, the duration and Play. Tapping it expands the inline player in place, so the picker stays above the fold.
- Playwright, Chromium and ffmpeg go in a new pixi feature `tutorials`, in env `tutorials = ["tutorials"]` with solve-group `default`. The `record-tutorials` task lives in `[feature.tutorials.tasks]`. This overrides `stories.yaml`'s "feature.dev" so that CI's default env and prod stay unchanged.
- The full spec is kept, at about 2,300 tokens.

## Boundaries & Constraints

**Always:**
- Every page sits at 390×844 with captions on screen, a visible cursor and a tap ripple, and no audio.
- Every run uses a fresh SQLite file under a temp dir, never `db.sqlite3`, deleted afterwards.
- Browser requests to hosts other than `127.0.0.1` and the CDN allowlist (`cdn.tailwindcss.com`, `cdn.jsdelivr.net`, `unpkg.com`, `cdnjs.cloudflare.com`, `fonts.googleapis.com`, `fonts.gstatic.com`) are aborted, and the run fails if any was attempted.
- Waits are fixed, never load-dependent. A selector timeout (10 s) exits non-zero.
- Output is H.264 `yuv420p` `+faststart`. The run exits non-zero when all MP4s in `static/tutorials/` together exceed 6 MB.
- `pixi run record-tutorials video1` writes only Video 1's files, and other files stay byte-identical.
- Embeds never autoplay, carry `playsinline` and `preload="none"`, show the poster, and dismiss for the current page view only, with no storage.
- The prod env's resolved packages are unchanged (`pixi list -e prod` is identical before and after).

**Never:** Videos 2 and 3 or their embeds. A recorder in CI. Playwright, Chromium or ffmpeg in the prod env or Docker image. Real user data in recordings. Audio.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Full run | `pixi run record-tutorials` | `static/tutorials/video1.mp4` + `video1.jpg`; temp DB gone; exit 0 | N/A |
| Unknown video | `record-tutorials video9` | No files touched | Exit 2, lists valid names |
| UI drift | Selector missing | Partial outputs not written | Exit non-zero naming the step |
| Over budget | MP4 total > 6 MB | Files written | Exit non-zero with the size |
| External call | Page requests a non-allowlisted host | Request aborted | Exit non-zero naming the URL |
| All adopted | Guest owns every starter | No picker, so no Video 1 embed on either page | N/A |

</frozen-after-approval>

## Code Map

- `pixi.toml` -- `[environments]` L88–90 (`default=["dev"]`, `prod=[]`); `[activation] env PYTHONPATH=src` L92. conda-forge has `playwright-python` 1.64.1 (noarch) and `ffmpeg` 9.0.2 for all 5 platforms. Chromium comes from `playwright install chromium`.
- `src/config/settings/local.py` -- SQLite NAME hard-coded L13; debug_toolbar added L25–26, which would overlay the page. `base.py:23` requires `DJANGO_SECRET_KEY`, and `.env` provides it. Celery is not needed for Video 1 (no `.delay()` on the onboarding path).
- `templates/pages/onboarding.html` -- standalone page with Tailwind and Alpine from CDNs and a 1 s `.fade-in` on `<main>`. The picker is `{% if not all_adopted %}` L84 → `<section x-data="{ picked: [] }">` L85; the embed goes between them. Selectors: `input[name=blueprints][value=<slug>]` (sr-only, so click its `<label>`), and the button by role, name `/Add 2 to my vault/`. The success message is inline at L67–75.
- `src/my_garage/templates/my_garage/collection_templates.html` -- extends `my_garage/base.html`. The embed goes inside `{% else %}` before `<form>` (~L47).
- `templates/includes/_nav.html` -- the hamburger is `button[aria-label="Navigation menu"]`; collections are `a[data-testid="nav-collection-link"]`. It needs the `quick_add_collections` context processor.
- `src/my_garage/templates/my_garage/base.html:~48` -- the Alpine dismiss pattern to reuse (`x-data="{ show: true }"`, `aria-label="Dismiss"`).
- `src/my_garage/templates/registration/login.html` -- `#id_username`, `#id_password`, `button[type=submit]`. `LOGIN_REDIRECT_URL="/"`.
- `tests/unit/test_static_references.py:20` -- the regex only matches `{% static '…' %}`; the `as var` form is missed.
- `pyproject.toml` -- ruff lints `.`; pytest `pythonpath=["src"]`, `testpaths=["tests"]`.

## Tasks & Acceptance

**Execution:**
- [x] Probe first: install the deps in the `tutorials` env and `playwright install chromium`, then launch headless Chromium on WSL. If system libs are missing and need sudo, HALT and ask the owner.
- [x] `pixi.toml` + `pixi.lock` -- add `[feature.tutorials.dependencies]` (`playwright-python`, `ffmpeg`), the env, and `[feature.tutorials.tasks]` `record-tutorials` (depends on `playwright install chromium`). Confirm `pixi list -e prod` is unchanged.
- [x] `src/config/settings/tutorials.py` -- import local; NAME from the required env `TUTORIALS_DB_PATH`; remove debug_toolbar; `CELERY_TASK_ALWAYS_EAGER=True`.
- [x] `src/my_garage/management/commands/seed_tutorial_demo.py` -- create a fixed demo user (`demo`, fixed password, no collections); idempotent.
- [x] `scripts/record_tutorials/` (`__main__.py`, `harness.py`, `overlays.py`, `flows.py`, `encode.py`) -- the CLI with a flow registry `{"video1": …}`, temp-DB lifecycle, a server on a free port, the request allowlist, overlays via `add_init_script`, an injected `[data-tutorial-video]{display:none}` so embeds don't record themselves, ffmpeg encode plus a poster, and the size check. Import Playwright lazily.
- [x] `flows.py` Video 1 -- log in; on `/welcome/`, adopt Wine Collection and Horology Salon; show the success message; open the nav to "Your Collections"; tap Wine Collection to reach its empty list. Target length about 60 s. Captions: "Pick what you collect" → "Tap two starters" → "Add them to your vault" → "Your collections live in the menu" → "Open one to add your first item".
- [x] `templates/includes/_tutorial_video.html` -- takes `src`, `poster`, `title` and `duration`; wrapper `data-tutorial-video`; a collapsed card that expands to the inline player, plus Dismiss.
- [x] `onboarding.html`, `collection_templates.html` -- `{% static 'tutorials/video1.mp4' as … %}` and the include, at the Code Map spots.
- [x] `tests/unit/test_static_references.py` -- also match `{% static '…' as name %}`.
- [x] `static/tutorials/video1.mp4`, `video1.jpg` -- recorded output, committed.
- [x] Tests: `tests/unit/test_record_tutorials.py` (CLI names, ffmpeg args, size check, allowlist; pytest `pythonpath` gains `scripts`); `tests/unit/test_seed_tutorial_demo.py`; functional embed tests for both pages (present, absent when all adopted, attributes).
- [x] `CLAUDE.md` §3 -- add `record-tutorials` to the pixi task list.

**Acceptance Criteria:**
- Given a clean checkout, when `pixi run record-tutorials` runs, then it finishes in under 5 min without manual steps and `db.sqlite3` is untouched.
- Given Video 1, when it is watched at phone size, then two starters are selected, added and shown in the menu, with captions legible.
- Given `/welcome/` on iPhone Safari and desktop Chrome, when Play is tapped, then the video plays inline. Dismiss hides it until reload.

## Implementation Notes

- **Probe:** headless Chromium launched on WSL after `playwright install chromium`, with no system packages and no sudo.
- **Env:** `tutorials = { features = ["tutorials"], solve-group = "default" }`. `pixi run record-tutorials` picks this env automatically because it's the only one with the task. The task depends on `install-chromium` and sets `PYTHONPATH=src:scripts`. In `pixi.lock`, the `prod` and `default` env package lists are identical to baseline 8a4f78a, checked by parsing the YAML. The lock diff is large because the new env lists its packages for all 5 platforms.
- **Video 1:** 60.3 s, 193 KB (0.18 MB of the 6 MB budget). Encoding is H.264 Main, `yuv420p`, `+faststart`, 390×844, 20 fps, CRF 26, `-preset slow -tune animation`, no audio. It's captured at DPR 2 (780×1688) and downscaled with lanczos. The poster is taken at 1.5 s. Frames at 2, 9, 20, 32, 45 and 56 s were checked by eye: picker, both starters ticked, "Added 2 collections", the menu listing both, and the empty Wine list. Captions are legible.
- **Runs:** two full runs took about 66 s each, exited 0, and produced identical step and caption logs. `db.sqlite3` was unchanged by checksum, and no temp dirs were left behind.
- **Sign-in:** happens in a separate, unrecorded browser context, and its storage state is reused, so the video opens on `/welcome/`. The opening load and the 1.5 s fade-in are trimmed by wall-clock offset. This is the one load-dependent number, and it only affects where the video starts.
- **Debugging:** `TUTORIALS_DEBUG_DIR` saves per-step and failure screenshots. It's off by default.
- **Edge-case tests:** after the implementation pass, the step-03 audit added harness-level tests. They cover UI drift (no outputs, step named, CLI exit 1), an external request with or without a failing flow (URL named, no outputs), a full run (exit 0, temp DB removed), and over budget (files kept, exit 1). The browser, server and ffmpeg are stubbed.
- **Not checked yet:** inline playback on iPhone Safari and desktop Chrome is left for the owner. The recorder needs the CDNs to be reachable, and if they aren't, frames would render unstyled without the run noticing.

## Review Triage Log

Pass 1, 2026-11-02. Layers: Verification Gap (VG), Blind Hunter (BH), Edge Case Hunter (EC). No Story 1 triage row covers these findings.

- VG1 medium → patch: nothing asserts that the `as`-form regex finds the tutorial references. If it regresses, they silently drop out of the parametrization, and the non-empty check still passes because other templates match.
- VG2 medium → patch: no test checks the env the harness passes to `_manage`/`_start_server`. Without `DJANGO_SETTINGS_MODULE`, `manage.py` would fall back to `config.settings.local`, which is the real `db.sqlite3`.
- VG3, BH4 medium → patch: no test imports `config.settings.tutorials`, so neither its refuse-to-fall-back guard nor the debug_toolbar removal is pinned.
- VG-O1, BH2 low → patch: the demo credentials are duplicated in the harness and the seed command, and drift would break sign-in. The fix is a direct import.
- VG-O2, BH1, EC8 medium → patch: the seed command ships in the image and would create or reset `demo` with a password that's in the repo, under any settings. It now refuses unless the settings module is `config.settings.tutorials`.
- BH3, EC7 maybe-false (medium if true) → defer: server-side calls bypass the browser allowlist, and the tutorials settings inherit the real `.env` keys with eager Celery. Video 1's flow reaches no `.delay()`. The only server-side callers are the valuation, enrich and OCR views (`views.py:562/602/885`), and per brownfield.md `collection_item_add` starts no task. It becomes real if a later flow reaches one of those views.
- BH5 low → reject: the flow's copy and selector hooks aren't guarded in CI. That's by design: a broken selector fails the re-record (CAP-6), and the recorder isn't in CI (a SPEC non-goal). A new functional test is more than a direct correction. The inaccurate docstring part → patch.
- BH6 low → reject: title and duration are hard-coded. ffprobe shows a duration of 60.3 s, so "1:00" is correct today, and `Flow.title` is only logged.
- BH7, EC1 low → reject: an over-budget run overwrites the committed MP4 before the check. The frozen matrix row says "Files written; exit non-zero", and git restores the committed copy.
- BH7b low → patch: nothing tests that the committed MP4s stay under budget between re-records. Added a test that calls `check_budget` on `static/tutorials/`.
- BH8, EC6 low → reject: server output is discarded, and a 500 on login waits 60 s before saying "did not become ready". This is developer-only and rare, and the fix adds log plumbing.
- BH9 low → reject: the CDNs and the Alpine `3.x.x` version float. These are pre-existing template choices, the limitation is recorded in the Implementation Notes, and re-records follow UI changes anyway.
- BH10, EC10 low → patch: Dismiss doesn't pause a playing video, so it keeps decoding while hidden. Dismiss now also calls `$refs.player.pause()`.
- BH11a low → patch: the static `aria-expanded="false"` never changes. Removed.
- BH11b, EC11 low → reject: the `play()` promise is unhandled. A failure only logs to the console, and a `.catch` wouldn't give the user feedback either.
- BH12 low → defer: CLAUDE.md doesn't document `scripts/`, the tutorials settings, `TUTORIALS_DEBUG_DIR` or the env. Edits to agent-context files are deferred.
- BH13a low → patch: `overlays.clear_caption` is unused. Deleted.
- BH13b false: the "show the success message" step reshows the "Add them to your vault" caption on purpose. The POST reload clears overlays, and the five-caption sequence in the task list is preserved.
- BH13c low → reject: `trim_s` is set outside `__init__` and passed through `trim.txt`, and debug screenshot numbers skip. Both are cosmetic.
- BH13d, EC4 low → reject: the failure-path screenshot can raise and mask the step error. It only runs when `TUTORIALS_DEBUG_DIR` is set, and the fix adds a guard.
- BH14a false: `django_db` in a unit test. 45 files in `tests/unit/` already use `django_db`.
- BH14b false: raw `create_user` instead of factory-boy. `tests/functional/test_collection_provisioning.py` uses raw creates, which is the established local pattern.
- EC2 false: the poster can't be paired with a stale MP4 if poster encoding fails. Both ffmpeg calls run in `work/` before any copy, and `check=True` raises first.
- EC3 low → reject: a trimmed video shorter than 1.5 s gives no poster frame. The flow is 60 s of fixed waits, so this can't happen.
- EC5 low → reject: when the box is None on every poll, the error says "never stopped moving" instead of "no bounding box". It still fails and names the step.
- EC9 false: a stale `demo` user (inactive, or owning collections). Every run migrates a fresh temp DB.
- EC12 false: rendering the include without `src`/`poster`. Both call sites pass them, and there is no other caller.
- EC13 low → reject: a clean checkout without `.env` fails. `base.py` requires `DJANGO_SECRET_KEY` for every pixi task, so it's the repo's standing precondition. The Chromium system-library probe passed on WSL.

## Design Notes

The embed's URLs use `{% static '…' as var %}` at the call site, not inside the partial. That keeps the static-reference test guarding them, since a missing file 500s under manifest storage. The recorder lives outside `src/` so it never ships in the image.

## Verification

**Commands:**
- `pixi run record-tutorials` twice -- expected: exit 0, then the same step and caption log both times.
- `pixi list -e prod` before and after -- expected: identical.
- The four §16 gates -- expected: all pass.

**Manual checks:**
- Play `video1.mp4` and note its size and encoder settings in Implementation Notes (target about 2 MB). The owner checks playback on iPhone Safari.
