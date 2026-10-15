"""
Functional tests for HEIC receipts on the service record form.

iPhone photos are HEIC. ImageField rejected them ("Upload a valid image")
because Pillow could not open them; they are now accepted and stored as JPEG,
since only Safari can display HEIC.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from PIL import Image

from my_garage.forms import GenericServiceRecordForm
from my_garage.models import GenericServiceRecord
from tests.unit.test_image_utils import heic_upload, jpeg_upload

FORM_DATA = {
    "date": "2026-10-14",
    "vendor": "Joe's Auto",
    "description": "Oil change",
    "category": "MAINTENANCE",
    "total_cost": "49.99",
}


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


class TestGenericServiceRecordFormReceipt:
    def test_heic_receipt_is_valid_and_converted_to_jpeg(self, db):
        form = GenericServiceRecordForm(FORM_DATA, {"receipt_image": heic_upload()})

        assert form.is_valid(), form.errors
        receipt = form.cleaned_data["receipt_image"]
        assert receipt.name == "IMG_0423.jpg"
        assert receipt.content_type == "image/jpeg"

    def test_jpeg_receipt_is_kept_as_is(self, db):
        upload = jpeg_upload()
        form = GenericServiceRecordForm(FORM_DATA, {"receipt_image": upload})

        assert form.is_valid(), form.errors
        assert form.cleaned_data["receipt_image"] is upload

    def test_edit_without_new_upload_keeps_stored_receipt(self, migrated_vehicle_item):
        record = GenericServiceRecord.objects.create(
            item=migrated_vehicle_item,
            date="2026-10-01",
            vendor="Joe's Auto",
            description="Oil change",
            total_cost="49.99",
            receipt_image=jpeg_upload("old.jpg"),
        )
        stored_name = record.receipt_image.name

        form = GenericServiceRecordForm(FORM_DATA, {}, instance=record)
        assert form.is_valid(), form.errors
        form.save()

        record.refresh_from_db()
        assert record.receipt_image.name == stored_name


class TestAddServiceViewHeicReceipt:
    def test_heic_receipt_is_stored_as_jpeg(self, auth_client, migrated_vehicle_item):
        item = migrated_vehicle_item
        url = f"/collections/{item.collection_type.slug}/items/{item.id}/add-service/"

        with patch(
            "my_garage.tasks.task_process_generic_service_record_ocr.delay"
        ) as mock_ocr:
            response = auth_client.post(
                url, {**FORM_DATA, "receipt_image": heic_upload()}
            )

        assert response.status_code == 302
        record = GenericServiceRecord.objects.get(item=item)
        assert record.receipt_image.name.endswith(".jpg")
        with Image.open(record.receipt_image.path) as image:
            assert image.format == "JPEG"
        mock_ocr.assert_called_once_with(record.id)
