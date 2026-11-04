"""Video 1 embed above both starter pickers."""

from __future__ import annotations

import re

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from my_garage.collection_blueprints import COLLECTION_BLUEPRINTS
from my_garage.services.collection_provisioning import provision_collections

User = get_user_model()
ALL_SLUGS = [bp["slug"] for bp in COLLECTION_BLUEPRINTS]
PAGES = ["onboarding", "collections:collection_templates"]


@pytest.fixture
def guest(db):
    return User.objects.create_user(username="guest", password="pass")


def _video_tag(html: str) -> str:
    match = re.search(r"<video\b[^>]*>", html)
    assert match, "no <video> element rendered"
    return match.group(0)


@pytest.mark.parametrize("url_name", PAGES)
def test_embed_renders_above_picker(client, guest, url_name):
    client.force_login(guest)
    html = client.get(reverse(url_name)).content.decode()
    assert "data-tutorial-video" in html
    assert "Your vault in 60 seconds" in html
    assert html.index("data-tutorial-video") < html.index('name="blueprints"')


@pytest.mark.parametrize("url_name", PAGES)
def test_video_attributes(client, guest, url_name):
    client.force_login(guest)
    tag = _video_tag(client.get(reverse(url_name)).content.decode())
    assert "playsinline" in tag
    assert 'preload="none"' in tag
    assert "controls" in tag
    assert "autoplay" not in tag
    assert "muted" not in tag


@pytest.mark.parametrize("url_name", PAGES)
def test_video_has_no_src_source_or_poster_until_play(client, guest, url_name):
    client.force_login(guest)
    html = client.get(reverse(url_name)).content.decode()
    tag = _video_tag(html)
    # data-* attributes carry the URLs; the bare attributes must not exist.
    bare = re.sub(r'data-[\w-]+="[^"]*"', "", tag)
    assert " src=" not in bare and " poster=" not in bare
    assert "<source" not in html[html.index("<video") : html.index("</video>")]
    assert re.search(r'data-phone-src="[^"]*tutorials/video1\.mp4"', tag)
    assert re.search(r'data-phone-poster="[^"]*tutorials/video1\.jpg"', tag)
    assert re.search(r'data-desktop-src="[^"]*tutorials/video1-desktop\.mp4"', tag)
    assert re.search(r'data-desktop-poster="[^"]*tutorials/video1-desktop\.jpg"', tag)


@pytest.mark.parametrize("url_name", PAGES)
def test_both_thumbnails_are_toggled_by_css(client, guest, url_name):
    client.force_login(guest)
    html = client.get(reverse(url_name)).content.decode()
    phone = re.search(r'<img[^>]*src="[^"]*tutorials/video1\.jpg"[^>]*>', html)
    desktop = re.search(
        r'<img[^>]*src="[^"]*tutorials/video1-desktop\.jpg"[^>]*>', html
    )
    assert phone and desktop
    assert 'class="md:hidden' in phone.group(0)
    assert 'class="hidden md:block' in desktop.group(0)


@pytest.mark.parametrize("url_name", PAGES)
def test_play_picks_variant_by_media_query_and_dismiss_without_storage(
    client, guest, url_name
):
    client.force_login(guest)
    html = client.get(reverse(url_name)).content.decode()
    assert "matchMedia('(min-width: 768px)')" in html
    assert 'aria-label="Dismiss"' in html
    embed = html[html.index("data-tutorial-video") :]
    embed = embed[: embed.index("</video>")]
    assert "localStorage" not in embed and "sessionStorage" not in embed


@pytest.mark.parametrize("url_name", PAGES)
def test_no_embed_when_every_starter_adopted(client, guest, url_name):
    client.force_login(guest)
    provision_collections(guest, ALL_SLUGS)
    html = client.get(reverse(url_name)).content.decode()
    assert "data-tutorial-video" not in html
    assert "<video" not in html
