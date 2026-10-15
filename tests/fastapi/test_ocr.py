"""
Tests for the OCR router (POST /ocr/process).

pytesseract is mocked: CI runners need not have the tesseract binary, and
these tests are about which uploads reach OCR, not OCR accuracy.
"""

import io
import logging
from unittest.mock import patch

import pillow_heif
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from fastapi_services.main import app
from fastapi_services.ocr.main import UNSUPPORTED_IMAGE_DETAIL

RECEIPT_TEXT = "JOE'S AUTO\n01/15/2024\nOil change 49.99\nTOTAL 49.99\n"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_gemini():
    """These tests cover the tesseract path; never call the real Gemini API."""
    with patch(
        "fastapi_services.ocr.main.extract_receipt_with_gemini", return_value=None
    ):
        yield


def _encode(fmt: str) -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (64, 32), "white")
    if fmt == "HEIF":
        # Encode through pillow_heif directly so the test does not depend on
        # the opener registration it is meant to check.
        pillow_heif.from_pillow(image).save(buffer)
    else:
        image.save(buffer, format=fmt)
    return buffer.getvalue()


def _post(client, data: bytes, filename: str, content_type: str):
    return client.post("/ocr/process", files={"file": (filename, data, content_type)})


@pytest.mark.parametrize(
    ("fmt", "filename", "content_type"),
    [
        ("JPEG", "receipt.jpg", "image/jpeg"),
        ("PNG", "receipt.png", "image/png"),
        # iPhone photos stay HEIC when emailed — this was a 500 before.
        ("HEIF", "IMG_0423.HEIC", "image/heic"),
    ],
)
@patch("fastapi_services.ocr.main.pytesseract.image_to_string")
def test_supported_formats_are_parsed(mock_ocr, client, fmt, filename, content_type):
    mock_ocr.return_value = RECEIPT_TEXT

    response = _post(client, _encode(fmt), filename, content_type)

    assert response.status_code == 200, response.text
    assert response.json()["vendor"] == "JOE'S AUTO"
    mock_ocr.assert_called_once()


@patch("fastapi_services.ocr.main.pytesseract.image_to_string")
def test_unreadable_file_is_400_not_500(mock_ocr, client):
    response = _post(client, b"%PDF-1.4\n%%EOF", "receipt.pdf", "application/pdf")

    assert response.status_code == 400
    assert response.json()["detail"] == UNSUPPORTED_IMAGE_DETAIL
    mock_ocr.assert_not_called()


@patch("fastapi_services.ocr.main.pytesseract.image_to_string")
def test_processing_failure_is_logged(mock_ocr, client, caplog):
    mock_ocr.side_effect = RuntimeError("tesseract exploded")

    with caplog.at_level(logging.ERROR, logger="fastapi_services.ocr.main"):
        response = _post(client, _encode("PNG"), "receipt.png", "image/png")

    assert response.status_code == 500
    assert "tesseract exploded" in response.json()["detail"]
    assert "tesseract exploded" in caplog.text
