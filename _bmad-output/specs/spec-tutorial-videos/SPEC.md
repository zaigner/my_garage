---
id: SPEC-tutorial-videos
companions:
  - recording-pipeline.md
  - brownfield.md
sources:
  - ../../planning-artifacts/briefs/brief-my_garage-2026-10-29/brief.md
  - ../../planning-artifacts/briefs/brief-my_garage-2026-10-29/addendum.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# First-Collection How-To Videos

## Why

Pain to solve, ahead of time. my_garage is about to open to invited friends and family (**guests**), who sign in through Cloudflare Access and land on `/welcome/` with an empty vault, mostly on a phone. Nobody has been stuck yet only because nobody but the **owner** has tried. Guests don't know what a "collection" is here, what "Add 2 to my vault" does, or that a first item unlocks the rest of the checklist, and a guest whose hobby isn't one of the seven starters meets a field builder before seeing any collection. The fallback, texting the owner, doesn't scale past a few relatives. Hand-made screencasts would go stale within a couple of PRs because the UI churns often. The welcome checklist also currently 404s at step 2 for any guest without an Automobiles collection. Now is the moment: the UI is stable enough to record and the invites haven't gone out.

## Capabilities

- **CAP-1**
  - **intent:** A guest with at least one item can follow the welcome checklist's step-2 "View →" link to a collection they own that holds one of their items.
  - **success:** For a guest who adopted only non-Automobiles starters (e.g. Wine Collection only) and added an item, every link in the `/welcome/` checklist returns 200, and the step-2 link resolves to a collection containing one of that guest's items.
- **CAP-2**
  - **intent:** A guest about to pick starter collections can watch Video 1, "Your vault in 60 seconds", showing two starters being adopted and where they then appear.
  - **success:** Video 1 renders above the starter picker on both `/welcome/` and `/collections/templates/`, and the recording shows two starters selected, added, and visible afterwards.
- **CAP-3**
  - **intent:** A guest looking at an empty collection can watch Video 2, "Your first item", showing the add form opened, a few fields filled, a photo attached, the item saved, and the resulting card.
  - **success:** Video 2 renders in a collection list page's empty state and is absent once the collection has an item; the recording shows each of those steps in order.
- **CAP-4**
  - **intent:** A guest whose hobby no starter covers can watch Video 3, "Build a collection for anything", showing a collection named, Collection Curator suggestions requested, one field adjusted, the collection saved and shown empty, ending with a pointer to Video 2.
  - **success:** Video 3 renders on `/collections/create/` in create mode and not when editing an existing collection; its captions present the suggested fields as an example, not what the guest will get.
- **CAP-5**
  - **intent:** A guest can watch any tutorial in place, sound off, and dismiss it when done.
  - **success:** Each embed shows a poster frame, never autoplays, plays inline on iPhone Safari and desktop Chrome, has captions and UI text legible on a phone and on a laptop at the player's default width, and hides on dismiss for the rest of that page view (no persistence across reloads).
- **CAP-6**
  - **intent:** The owner can regenerate all three videos and their posters after a UI change with one command.
  - **success:** `pixi run record-tutorials` on a clean checkout writes both variants (CAP-7) of all three videos, six MP4s and six JPEG posters, to `static/tutorials/` in under 10 minutes, with no manual steps and no AI API calls. Two runs produce the same data, suggested fields, captions and timing. A broken selector fails the run with a non-zero exit. `pixi run record-tutorials <video>` (e.g. `video2`) re-records both variants of only that video and leaves the other files byte-for-byte unchanged. The run also exits non-zero when all the MP4s together exceed 6 MB.
- **CAP-7**
  - **intent:** A guest sees each tutorial recorded in the layout they are looking at: the phone recording on a narrow screen, a desktop recording on a wide one.
  - **success:** Each video has a phone and a desktop variant. When the viewport is at least 768px wide (the `md` breakpoint where the collection grids and page headers change; `_nav.html` has no desktop nav, so the hamburger is the only nav at every width), the embed shows the desktop thumbnail and plays the desktop MP4 with its poster; below 768px it shows and plays the phone ones. Only the chosen MP4 is downloaded, and only once Play is pressed. The desktop player is wider than the phone player's 280px and fits the page column without horizontal scrolling.

## Constraints

- Each video is recorded twice from the same seeded data and script: a phone variant at 390×844 and a desktop variant at a viewport just past the 768px breakpoint (880×680), narrow enough that UI text stays legible in a player about 620px wide (the `/welcome/` column is `max-w-2xl`). Both have on-screen captions, no audio, and a visible cursor and tap/click highlight.
- The variant is chosen in the browser by viewport width, never by user-agent or device detection on the server. A narrow desktop window shows the phone layout, so it gets the phone video.
- Videos are served as Django static files from `static/tutorials/` (WhiteNoise, behind Cloudflare Access). Not `media/`, which holds owner-scoped uploads, and no external host.
- All the tutorial MP4s combined, both variants of all three videos, weigh at most 6 MB. One reason is that static files ship in the Docker image and image pulls on the Pi nodes already take minutes. The other is that the MP4s are committed, so every re-record adds its new files to git history for good. The brief's 15 MB is an outer limit; 6 MB keeps refreshes cheap.
- Each output is H.264 MP4 (`yuv420p`, `+faststart`) with a JPEG poster, which iOS Safari needs for inline playback.
- A recording run makes no external API calls: the Collection Curator schema request returns a fixed response, and every run uses a throwaway SQLite database seeded with fixed demo data, never `db.sqlite3`.
- Every `{% static %}` reference must exist, or manifest storage returns a 500 (`tests/unit/test_static_references.py` enforces this). The generated MP4s and posters are therefore committed to the repo, and an embed can't merge before the files it references.
- Playwright, Chromium and ffmpeg stay out of the prod pixi environment and the Docker image.
- Video 3 changes at most one or two fields on screen, because each field row stacks four inputs at phone width.

## Non-goals

- Valuation and receipt-upload (OCR) videos.
- Estate & Legacy videos, including the beneficiary walkthrough.
- Picking the variant from the user-agent or on the server.
- Switching variant mid-playback when the window is resized; the choice is made when Play is pressed.
- Re-recording one variant of a video on its own; a re-record always produces both.
- Voiceover or any audio (deferred, not rejected).
- Public or external hosting (YouTube, CDN).
- Play analytics.
- Running the recorder in CI.
- Git LFS or any external store for the videos. Revisit this only if cloning the repo becomes slow.
- Persisting video dismissal across visits.

## Success signal

- Every guest in the invite group ends their first session with at least one collection holding at least one item, without contacting the owner. Check this in the database.
- After a UI change that visibly alters a recorded flow, the owner re-records only the affected video(s) (`pixi run record-tutorials <video>`) and commits only the files that changed. A UI change outside the recorded flows needs no re-record.

## Assumptions

- Target video lengths: Video 1 about 60 s, Video 2 about 90 s, Video 3 about 2 min. These come from the brief and are unconfirmed.
- The task name `record-tutorials` comes from the brief and is unconfirmed. The brief's 5-minute run budget became 10 minutes on 2026-11-03, because recording runs in real time and each video is now recorded twice (Video 1 alone took about 66 s per variant).
- The 6 MB size budget was set on 2026-10-29, replacing the brief's 15 MB. Story 3 measured the Video 1 phone variant at 525 KB and the desktop variant at 662 KB (1.16 MB total; Story 2's 193 KB came from the corner-framed DPR-2 recording), so six files should fit easily.
- Story 3 settled the desktop viewport at 880×680: the height keeps the nav dropdown's "Your Collections" links on screen, and the width stays legible in a ~620px player.
- "First session" means the same calendar day as the guest's first sign-in.
- Recordings show only seeded demo data, never real user data.
