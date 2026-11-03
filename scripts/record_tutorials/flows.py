"""Scripted flows. Waits are fixed so two runs produce the same timing.

A flow receives a ``Recorder`` (see harness.py) whose page already has the
demo user signed in. Selectors mix roles, aria-labels and data-testid with a few CSS
``:has()`` selectors and copy regexes (button and message text), so a copy change
can break them. When one times out the run fails naming the step.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from . import overlays


@dataclass(frozen=True)
class Flow:
    title: str
    start_path: str  # first page; the video starts once its anchor shows
    anchor: str  # selector proving the first page is ready
    run: Callable
    poster_at_s: float  # seconds into the trimmed video


def video1(rec) -> None:
    from playwright.sync_api import expect  # lazy: Playwright only in the tutorials env

    page = rec.page

    rec.step("pick what you collect")
    overlays.caption(rec, "Pick what you collect", 4500)
    wine = page.locator("label:has(input[name=blueprints][value=wine-collection])")
    horology = page.locator("label:has(input[name=blueprints][value=horology-salon])")
    overlays.glide(rec, *rec.variant.center, 900)
    page.wait_for_timeout(2500)

    verb = rec.variant.verb
    rec.step(f"{verb.lower()} two starters")
    overlays.caption(rec, f"{verb} two starters", 1500)
    overlays.tap(rec, wine)
    page.wait_for_timeout(3500)
    overlays.tap(rec, horology)
    page.wait_for_timeout(4500)

    rec.step("add them to your vault")
    overlays.caption(rec, "Add them to your vault", 1500)
    add_button = page.get_by_role("button", name=re.compile(r"Add 2 to my vault"))
    expect(add_button).to_be_enabled()
    overlays.tap(rec, add_button, glide_ms=900)
    expect(page.get_by_text(re.compile(r"Added 2 collections"))).to_be_visible()
    page.wait_for_timeout(500)
    rec.step("show the success message")
    # The page reloaded after the POST, which cleared the caption.
    overlays.caption(rec, "Add them to your vault", 6500)

    rec.step("open the menu")
    overlays.caption(rec, "Your collections live in the menu", 1500)
    overlays.tap(rec, page.locator('button[aria-label="Navigation menu"]'))
    page.wait_for_selector('a[data-testid="nav-collection-link"]')
    page.wait_for_timeout(7000)

    rec.step("open Wine Collection")
    overlays.caption(rec, "Open one to add your first item", 1500)
    link = page.locator(
        'a[data-testid="nav-collection-link"]', has_text="Wine Collection"
    )
    overlays.tap(rec, link)
    page.wait_for_url(re.compile(r"/collections/wine-collection/"))
    page.wait_for_load_state("load")
    overlays.caption(rec, "Open one to add your first item", 9000)


FLOWS: dict[str, Flow] = {
    "video1": Flow(
        title="Your vault in 60 seconds",
        start_path="/welcome/",
        anchor="input[name=blueprints][value=wine-collection]",
        run=video1,
        poster_at_s=1.5,
    ),
}
