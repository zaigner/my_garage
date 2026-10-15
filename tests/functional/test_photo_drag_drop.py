"""
Item photo uploads: drag-and-drop wiring and HEIC handling.

On the item detail page the photo area was click-only, so a dropped photo
fell through to the browser, which opened it and left the page. iPhone
photos are HEIC, which only Safari displays, so they are stored as JPEG.
"""

from __future__ import annotations

import pytest
from PIL import Image

from my_garage.forms import DynamicCollectionItemForm
from my_garage.models import DynamicCollectionItem
from tests.unit.test_image_utils import heic_upload, jpeg_upload


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def _detail_url(item):
    return f"/collections/{item.collection_type.slug}/items/{item.id}/"


class TestDetailPageDropZone:
    @pytest.fixture
    def page(self, auth_client, migrated_vehicle_item):
        response = auth_client.get(_detail_url(migrated_vehicle_item))
        assert response.status_code == 200
        return response.content.decode()

    def test_drop_on_photo_block_attaches_file(self, page):
        assert (
            '@drop.prevent="dragging = false; dropPhoto($event.dataTransfer.files)"'
            in page
        )
        assert "input.dispatchEvent(new Event('change'))" in page

    def test_drop_switches_to_edit_mode(self, page):
        assert "editing = true;" in page

    def test_window_drop_guard_present(self, page):
        assert '@dragover.window.prevent=""' in page
        assert '@drop.window.prevent="dragging = false"' in page

    def test_file_input_accepts_heic(self, page):
        assert 'id="photo-upload" accept="image/*,.heic,.heif"' in page


class TestAddPageDropZone:
    @pytest.fixture
    def page(self, auth_client, automobiles_type):
        response = auth_client.get(f"/collections/{automobiles_type.slug}/items/add/")
        assert response.status_code == 200
        return response.content.decode()

    def test_window_drop_guard_present(self, page):
        assert '@dragover.window.prevent=""' in page
        assert '@drop.window.prevent="dragging = false"' in page

    def test_heic_matched_by_extension(self, page):
        assert r"/\.(heic|heif)$/i.test(file.name)" in page
        assert 'name="photo" accept="image/*,.heic,.heif"' in page


class TestHeicPhotoStoredAsJpeg:
    def test_form_converts_heic_photo(self, automobiles_type):
        form = DynamicCollectionItemForm(
            {"name": "Cayman"},
            {"photo": heic_upload()},
            collection_type=automobiles_type,
        )

        assert form.is_valid(), form.errors
        assert form.cleaned_data["photo"].name == "IMG_0423.jpg"

    def test_form_keeps_jpeg_photo(self, automobiles_type):
        upload = jpeg_upload()
        form = DynamicCollectionItemForm(
            {"name": "Cayman"}, {"photo": upload}, collection_type=automobiles_type
        )

        assert form.is_valid(), form.errors
        assert form.cleaned_data["photo"] is upload

    def test_add_view_stores_heic_as_jpeg(self, auth_client, automobiles_type):
        response = auth_client.post(
            f"/collections/{automobiles_type.slug}/items/add/",
            {"name": "Cayman", "photo": heic_upload()},
        )

        assert response.status_code == 302
        item = DynamicCollectionItem.objects.get(name="Cayman")
        assert item.photo.name.endswith(".jpg")
        with Image.open(item.photo.path) as image:
            assert image.format == "JPEG"

    def test_detail_edit_stores_heic_as_jpeg(self, auth_client, migrated_vehicle_item):
        item = migrated_vehicle_item
        response = auth_client.post(
            _detail_url(item), {"name": item.name, "photo": heic_upload()}
        )

        assert response.status_code == 302
        item.refresh_from_db()
        assert item.photo.name.endswith(".jpg")
        with Image.open(item.photo.path) as image:
            assert image.format == "JPEG"
