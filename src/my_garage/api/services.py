"""
Service layer for my_garage.

Vehicle-specific functions were retired in Phase 5. New functions follow
the collection services pattern.
"""

import logging
import os

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class VehicleServiceError(Exception):
    """Kept for backwards-compatibility; new code should use the collection
    services provider pattern instead."""


def process_generic_service_record_ocr(record) -> dict:
    """
    Call the FastAPI OCR service for a GenericServiceRecord's receipt image.

    Pre-fills vendor/description/total_cost only when those fields are blank
    so manual edits are never silently overwritten. Sets is_verified=False to
    flag the result for human review.

    Returns the raw OCR dict on success, empty dict on failure.
    """
    if not record.receipt_image:
        return {}

    try:
        image_file = record.receipt_image
        filename = os.path.basename(image_file.name)

        image_file.open("rb")
        image_bytes = image_file.read()
        image_file.close()

        ocr_url = f"{settings.FASTAPI_BASE_URL}/ocr/process"
        response = requests.post(
            ocr_url,
            files={"file": (filename, image_bytes, "image/jpeg")},
            timeout=30,
        )
        response.raise_for_status()
        ocr_data: dict = response.json()

        record.ocr_raw_data = ocr_data

        if not record.vendor and ocr_data.get("vendor"):
            record.vendor = ocr_data["vendor"]
        if not record.description and ocr_data.get("description"):
            record.description = ocr_data["description"]
        if not record.total_cost and ocr_data.get("total_cost"):
            record.total_cost = ocr_data["total_cost"]

        record.is_verified = False
        record.save()

        return ocr_data

    except Exception:
        logger.exception(
            "OCR processing failed for GenericServiceRecord pk=%s", record.pk
        )
        return {}
