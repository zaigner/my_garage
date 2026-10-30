---
title: "Product Brief: First-Collection How-To Videos"
status: final
created: 2026-10-29
updated: 2026-10-29
---

# Product Brief: First-Collection How-To Videos

## Executive Summary

my_garage is about to be opened to friends and family. They'll sign in through Cloudflare Access and arrive at `/welcome/` with nothing in the app yet, most of them on a phone. Nobody has gotten stuck yet, because nobody but the owner has tried. This feature makes sure the first guests can set up a collection and add an item without texting for help.

We'll ship three short, captioned how-to videos placed on the screens where they're needed:
- picking a starter collection
- adding a first item
- designing a custom collection

A Playwright script generates the videos from the real app, and one command re-records all of them after a UI change. The feature also fixes a 404 in the welcome checklist that would otherwise break the guided path.

The timing is right: the UI has stabilized enough to record, and the invites haven't gone out. Only one of the three flows calls an external API, and a fixed response can replace it during recording.

## The Problem

A first-time guest sees the starter picker, with seven starter collections, and then a three-step checklist. Each step makes sense to someone who already knows the app. A guest doesn't know what a "collection" means here, or what happens after they click "Add 2 to my vault." They also don't know that their first item is what makes the rest of the checklist (valuations, service records) unlock. A guest whose hobby isn't one of the seven starters has it harder: the custom builder asks them to design fields before they've seen what a collection looks like.

The usual fallback is calling the owner. That works once and gets old by the third relative. Hand-recorded screencasts would help briefly, but this UI changes often. The "Generate UI" feature and a full theme pass both shipped in the last few months, so hand-made videos would be out of date within a couple of PRs.

There's also a current bug in the guided path. On `/welcome/`, the step-2 "View →" link always points to the `automobiles` collection (`templates/pages/onboarding.html:190`). A guest who only picked Wine Collection gets a 404 at exactly the point where the app is trying to guide them.

## Who This Serves

**Primary: guests**, the invited friends and family. They have a real collection (coins, wine, watches, a car or two, sometimes something stranger) and no patience for software. Most will open the app on a phone. Success is when a guest ends their first visit with a collection that has one real item in it, without ever having to ask how.

**Secondary: the owner.** Fewer support texts, and visual proof that both ways of creating a collection still work after each UI change.

## The Solution

**Video 1: "Your vault in 60 seconds."**
- Shown above the starter picker on `/welcome/` and on `/collections/templates/`.
- It picks two starter collections, adds them, and shows where they appear.

**Video 2: "Your first item."**
- Shown in the empty state of a collection's list page.
- It opens the add form, fills in a few fields, attaches a photo, saves, and shows the resulting card.

**Video 3: "Build a collection for anything."**
- Shown on the custom builder at `/collections/create/`.
- It names a collection no starter covers, asks the AI field suggester ("Collection Curator") for fields, adjusts one field, saves, and shows the empty collection. It ends by pointing to Video 2.
- Captions present the suggested fields as an example. A guest who types the same hobby will get different fields from Gemini.

All three videos:
- Are recorded at phone size (390×844).
- Have on-screen captions and no audio, so they make sense with the sound off.
- Show a visible cursor and tap highlights.
- Play inline with a poster frame, never autoplay, and are dismissible.

**Re-recording** is one command (`pixi run record-tutorials`). It seeds demo data, replaces the field-suggestion call with a fixed response, runs the scripted flows and writes MP4s to `static/tutorials/`. If a selector breaks, the run fails loudly, which is the first sign the UI has drifted.

## What Makes This Different

- **Re-recording costs one command instead of an afternoon.** That matters for an app with one maintainer and a UI that changes often.
- **Hosting stays inside the app,** behind the same Cloudflare Access login as everything else, with no external accounts and nothing public.

## Success Criteria

- Every guest ends their first session with at least one collection and one item, without contacting the owner. You can check this in the database for the small invite group.
- `pixi run record-tutorials` regenerates all three videos in under 5 minutes, from a clean checkout, with no manual steps and no AI API calls.
- All three videos play inline on iPhone Safari and desktop Chrome, and the captions are legible on a phone screen.
- Combined video size is at most 15 MB.
- Recordings look the same across runs: same data, same suggested fields, same captions, same timing.
- The welcome checklist links never 404, whichever starter collections the guest picked.

## Scope

**In:**
- Install Playwright (Chromium) and ffmpeg through pixi.
- Demo-data seeding and a fixed field-suggestion response.
- The recording script, plus the caption and cursor overlay.
- A video embed partial on four screens.
- The `onboarding.html:190` fix.
- Tests for the embeds and the fix.

**Out (v1):**
- Valuation and receipt-upload videos.
- Desktop-size recordings.
- Voiceover or audio.
- Public or external hosting.
- Play analytics.
- Running the recorder in CI.
- Videos for Estate & Legacy features.

## Risks

- **Video 3 runs long on a phone.** Each custom-builder field row stacks vertically at phone width, so the script should change only one or two fields on screen.
- **Video 3 shows example fields, not live suggestions.** The caption wording above handles this. If it isn't clear, guests may expect the same fields when they try it themselves.

## Assumptions to Confirm

- Video lengths: Video 1 about 60 seconds, Video 2 about 90 seconds, Video 3 about 2 minutes.
- Task name: `pixi run record-tutorials`.
- Re-record time budget: under 5 minutes.
- Size budget: 15 MB for all three videos combined.
- "First session" means the same day.

## Vision

A short, scripted, self-refreshing clip next to every feature a guest might use for the first time: valuations, receipt OCR, and eventually the Estate & Legacy beneficiary walkthrough. Over time the recording scripts become the app's end-to-end smoke suite: if a tutorial can't be recorded, something guests depend on is broken.
