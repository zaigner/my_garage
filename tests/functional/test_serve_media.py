"""
Tests for serving uploaded media (GET /media/<path>).

Production only routed /media/ when DEBUG was on, so every uploaded photo,
receipt and attachment was a 404 there. Uploads are private, so the view
serves a file only to the user who owns the record that references it.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import CollectionItemAttachment, GenericServiceRecord
from tests.unit.test_image_utils import jpeg_upload

User = get_user_model()


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def photo_item(migrated_vehicle_item):
    migrated_vehicle_item.photo = jpeg_upload("cayman.jpg")
    migrated_vehicle_item.save()
    return migrated_vehicle_item


@pytest.fixture
def other_client(db):
    client = Client()
    client.force_login(User.objects.create_user(username="other", password="x"))
    return client


def _get(client, field_file):
    return client.get(field_file.url)


class TestServeMedia:
    def test_owner_gets_photo(self, auth_client, photo_item):
        response = _get(auth_client, photo_item.photo)

        assert response.status_code == 200
        assert b"".join(response.streaming_content).startswith(b"\xff\xd8")  # JPEG
        assert response["Cache-Control"] == "private, max-age=86400"

    def test_other_user_gets_404(self, other_client, photo_item):
        assert _get(other_client, photo_item.photo).status_code == 404

    def test_anonymous_is_sent_to_login(self, client, photo_item):
        response = _get(client, photo_item.photo)

        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_unreferenced_path_is_404(self, auth_client, photo_item):
        response = auth_client.get("/media/collections/2026/10/not-a-record.jpg")
        assert response.status_code == 404

    def test_record_whose_file_is_missing_is_404(self, auth_client, photo_item):
        photo_item.photo.storage.delete(photo_item.photo.name)
        assert _get(auth_client, photo_item.photo).status_code == 404

    def test_path_traversal_is_404(self, auth_client, photo_item):
        response = auth_client.get("/media/../src/config/settings/base.py")
        assert response.status_code == 404

    def test_owner_gets_receipt(self, auth_client, migrated_vehicle_item):
        record = GenericServiceRecord.objects.create(
            item=migrated_vehicle_item,
            date="2026-10-01",
            vendor="Porsche Grapevine",
            description="10K service",
            total_cost="837.39",
            receipt_image=jpeg_upload("receipt.jpg"),
        )

        assert _get(auth_client, record.receipt_image).status_code == 200

    def test_owner_gets_attachment(self, auth_client, migrated_vehicle_item):
        attachment = CollectionItemAttachment.objects.create(
            item=migrated_vehicle_item,
            file=jpeg_upload("title.jpg"),
            file_type="CERTIFICATE",
        )

        assert _get(auth_client, attachment.file).status_code == 200
