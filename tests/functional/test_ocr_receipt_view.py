"""
Functional tests for the inline receipt scan endpoint
(POST /collections/<slug>/items/<id>/ocr-receipt/), which relays the upload
to FastAPI's /ocr/process.

FastAPI's reason for a failure lives in the response body's "detail"; before
these tests the view logged and returned only str(HTTPError) — the status
and the internal FastAPI URL — so the real cause never reached the logs.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import patch

import requests
from django.core.files.uploadedfile import SimpleUploadedFile


def _fastapi_response(status: int, body: dict) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = "http://fastapi:8001/ocr/process"
    response._content = json.dumps(body).encode()
    return response


def _post_receipt(client, item):
    url = f"/collections/{item.collection_type.slug}/items/{item.id}/ocr-receipt/"
    receipt = SimpleUploadedFile("IMG_0423.HEIC", b"fake", content_type="image/heic")
    return client.post(url, {"receipt": receipt})


class TestOcrReceiptView:
    def test_success_returns_parsed_fields(self, auth_client, migrated_vehicle_item):
        body = {"vendor": "JOE'S AUTO", "total_cost": 49.99}
        with patch("requests.post", return_value=_fastapi_response(200, body)):
            response = _post_receipt(auth_client, migrated_vehicle_item)

        assert response.status_code == 200
        assert response.json() == {"success": True, **body}

    def test_rejected_upload_passes_detail_through_as_400(
        self, auth_client, migrated_vehicle_item, caplog
    ):
        detail = "Unsupported image format. Upload a JPEG, PNG or HEIC (iPhone) photo."
        with (
            patch(
                "requests.post",
                return_value=_fastapi_response(400, {"detail": detail}),
            ),
            caplog.at_level(logging.ERROR, logger="my_garage.views"),
        ):
            response = _post_receipt(auth_client, migrated_vehicle_item)

        assert response.status_code == 400
        assert response.json() == {"success": False, "error": detail}
        assert detail in caplog.text

    def test_server_failure_logs_detail_without_internal_url(
        self, auth_client, migrated_vehicle_item, caplog
    ):
        detail = "OCR processing failed: tesseract exploded"
        with (
            patch(
                "requests.post",
                return_value=_fastapi_response(500, {"detail": detail}),
            ),
            caplog.at_level(logging.ERROR, logger="my_garage.views"),
        ):
            response = _post_receipt(auth_client, migrated_vehicle_item)

        assert response.status_code == 500
        assert response.json()["error"] == detail
        assert "fastapi:8001" not in response.json()["error"]
        assert detail in caplog.text
