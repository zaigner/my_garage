"""
Tests for Gemini receipt extraction and the EXIF rotation applied before OCR.

The Gemini client is mocked throughout; nothing here calls the real API.
"""

from __future__ import annotations

import io
import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from fastapi_services.ocr import gemini_extractor
from fastapi_services.ocr.gemini_extractor import extract_receipt_with_gemini
from fastapi_services.ocr.main import extract_receipt

API_KEY = "sekrit-google-key"

EXTRACTION = {
    "vendor": "Porsche Grapevine",
    "date": "2026-10-01",
    "total_cost": 837.39,
    "description": "10K service, brake flush",
    "line_items": [{"item": "BRAKE FLUID", "price": 64.88}],
}


@pytest.fixture
def api_key():
    with patch.object(gemini_extractor.settings, "google_api_key", API_KEY):
        yield


def _client_returning(text: str = "", error: Exception | None = None) -> MagicMock:
    client = MagicMock()
    if error is not None:
        client.models.generate_content.side_effect = error
    else:
        client.models.generate_content.return_value = MagicMock(text=text)
    return client


def _image(size=(300, 200)) -> Image.Image:
    return Image.new("RGB", size, "white")


def _sideways_phone_photo() -> Image.Image:
    """A 300x200 JPEG flagged EXIF orientation 6, as iPhones store photos."""
    image = _image()
    exif = image.getexif()
    exif[0x0112] = 6  # Orientation: rotate 90° CW to display
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    buffer.seek(0)
    return Image.open(buffer)


class TestExtractReceiptWithGemini:
    def test_no_api_key_skips_gemini(self):
        with (
            patch.object(gemini_extractor.settings, "google_api_key", None),
            patch("google.genai.Client") as client_class,
        ):
            assert extract_receipt_with_gemini(_image()) is None
        client_class.assert_not_called()

    def test_returns_extracted_fields(self, api_key):
        client = _client_returning(json.dumps(EXTRACTION))
        with patch("google.genai.Client", return_value=client):
            result = extract_receipt_with_gemini(_image())

        assert result == EXTRACTION
        kwargs = client.models.generate_content.call_args.kwargs
        assert kwargs["model"] == "gemini-2.5-flash"
        assert kwargs["config"].response_mime_type == "application/json"

    def test_large_photo_is_downscaled_before_upload(self, api_key):
        client = _client_returning(json.dumps(EXTRACTION))
        with patch("google.genai.Client", return_value=client):
            extract_receipt_with_gemini(_image((4032, 3024)))

        image_part = client.models.generate_content.call_args.kwargs["contents"][0]
        sent = Image.open(io.BytesIO(image_part.inline_data.data))
        assert max(sent.size) == gemini_extractor.MAX_SIDE

    @pytest.mark.parametrize("bad_date", ["01OCT26", "2026-13-45", ""])
    def test_unusable_date_becomes_none(self, api_key, bad_date):
        client = _client_returning(json.dumps({**EXTRACTION, "date": bad_date}))
        with patch("google.genai.Client", return_value=client):
            result = extract_receipt_with_gemini(_image())

        assert result["date"] is None
        assert result["total_cost"] == 837.39

    def test_page_without_total_keeps_total_none(self, api_key):
        client = _client_returning(json.dumps({**EXTRACTION, "total_cost": None}))
        with patch("google.genai.Client", return_value=client):
            result = extract_receipt_with_gemini(_image())

        assert result["total_cost"] is None

    def test_malformed_response_returns_none(self, api_key):
        client = _client_returning("not json")
        with patch("google.genai.Client", return_value=client):
            assert extract_receipt_with_gemini(_image()) is None

    def test_api_error_returns_none_and_logs_without_key(self, api_key, caplog):
        error = RuntimeError(f"403 Forbidden for ...?key={API_KEY}")
        client = _client_returning(error=error)
        with (
            patch("google.genai.Client", return_value=client),
            caplog.at_level(logging.WARNING, logger=gemini_extractor.__name__),
        ):
            assert extract_receipt_with_gemini(_image()) is None

        assert "403 Forbidden" in caplog.text
        assert API_KEY not in caplog.text


class TestExtractReceipt:
    def test_uses_gemini_result_when_available(self):
        with (
            patch(
                "fastapi_services.ocr.main.extract_receipt_with_gemini",
                return_value=dict(EXTRACTION),
            ),
            patch("fastapi_services.ocr.main.pytesseract.image_to_string") as ocr,
        ):
            result = extract_receipt(_image())

        assert result["source"] == "gemini"
        assert result["total_cost"] == 837.39
        ocr.assert_not_called()

    def test_falls_back_to_tesseract(self):
        with (
            patch(
                "fastapi_services.ocr.main.extract_receipt_with_gemini",
                return_value=None,
            ),
            patch(
                "fastapi_services.ocr.main.pytesseract.image_to_string",
                return_value="JOE'S AUTO\nTOTAL 49.99\n",
            ),
        ):
            result = extract_receipt(_image())

        assert result["source"] == "tesseract"
        assert result["vendor"] == "JOE'S AUTO"
        assert result["total_cost"] == 49.99

    def test_sideways_photo_is_rotated_before_gemini_and_tesseract(self):
        """The production bug: OCR read EXIF-rotated phone photos sideways."""
        seen = {}

        def gemini(image):
            seen["gemini"] = image.size

        def tesseract(image):
            seen["tesseract"] = image.size
            return ""

        with (
            patch("fastapi_services.ocr.main.extract_receipt_with_gemini", gemini),
            patch("fastapi_services.ocr.main.pytesseract.image_to_string", tesseract),
        ):
            extract_receipt(_sideways_phone_photo())

        # Stored 300x200; displayed (and read) upright as 200x300.
        assert seen == {"gemini": (200, 300), "tesseract": (200, 300)}
