"""
Rendering checks for the Document Scan panel on the add-service page.

The panel was click-only: a receipt dropped on it fell through to the
browser, which opened the photo and left the page. These pin the Alpine
wiring that routes a drop (and the file picker) into scan(), and the
window-level guard that stops a near-miss drop from navigating away.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def page(auth_client, migrated_vehicle_item):
    item = migrated_vehicle_item
    response = auth_client.get(
        f"/collections/{item.collection_type.slug}/items/{item.id}/add-service/"
    )
    assert response.status_code == 200
    return response.content.decode()


def test_drop_on_scan_zone_runs_scan(page):
    assert (
        '@drop.prevent="dragging = false; scan($event.dataTransfer.files[0])"' in page
    )


def test_file_picker_runs_scan(page):
    assert "@change=\"scan($event.target.files[0]); $event.target.value = ''\"" in page


def test_window_drop_guard_present(page):
    assert '@dragover.window.prevent=""' in page
    assert '@drop.window.prevent="dragging = false"' in page


def test_scan_posts_to_item_ocr_endpoint(page, migrated_vehicle_item):
    item = migrated_vehicle_item
    assert (
        f"fetch('/collections/{item.collection_type.slug}/items/{item.id}/ocr-receipt/'"
        in page
    )
