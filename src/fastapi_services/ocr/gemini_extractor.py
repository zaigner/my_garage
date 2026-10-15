"""
Receipt extraction with a Gemini vision model.

Tesseract reads clean, flat receipts but not phone photos of multi-column
dealer invoices: it misses the totals box and garbles dates like "01OCT26".
Gemini reads the photo and returns the fields directly. Any failure (no key,
timeout, bad response) returns None so the caller falls back to tesseract.
"""

from __future__ import annotations

import io
import logging
import time
from datetime import date
from typing import Any, Optional

from PIL import Image
from pydantic import BaseModel, Field, ValidationError

from ..mcp.config import settings
from ..mcp.tools.redaction import redact

logger = logging.getLogger(__name__)

MODEL = "gemini-2.5-flash"
TIMEOUT_MS = 20_000
# Plenty for receipt text, and keeps the upload small on a home connection.
MAX_SIDE = 2048

PROMPT = """\
This is a photo of a receipt or service invoice, possibly one page of several.
Extract:
- vendor: the business that issued it (e.g. "Porsche Grapevine"), not the customer.
- date: the invoice or service date as YYYY-MM-DD. Two-digit years are 20xx.
  Prefer the invoice date over other dates. null if none is legible.
- total_cost: the final amount the customer pays, e.g. "PLEASE PAY THIS AMOUNT",
  "Amount Due", "Total". null if this page has no final total.
- description: a short summary of the work, e.g. "10K service, brake flush".
- line_items: each charged part or service with its price.
Use only what is printed on the page; do not guess.
"""


class LineItem(BaseModel):
    item: str
    price: float


class ReceiptExtraction(BaseModel):
    vendor: Optional[str] = None
    date: Optional[str] = Field(None, description="YYYY-MM-DD")
    total_cost: Optional[float] = None
    description: Optional[str] = None
    line_items: list[LineItem] = Field(default_factory=list)


def _jpeg_bytes(image: Image.Image) -> bytes:
    image = image.convert("RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


def _valid_date(value: Optional[str]) -> Optional[str]:
    """Keep only real YYYY-MM-DD dates; the form's date input rejects others."""
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def extract_receipt_with_gemini(image: Image.Image) -> Optional[dict[str, Any]]:
    """
    Return {vendor, date, total_cost, description, line_items} read by Gemini,
    or None if Gemini is not configured or the call fails.

    `image` must already be upright (EXIF rotation applied).
    """
    api_key = settings.google_api_key
    if not api_key:
        return None

    from google import genai
    from google.genai import types

    started = time.monotonic()
    try:
        client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=TIMEOUT_MS)
        )
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=_jpeg_bytes(image), mime_type="image/jpeg"),
                PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReceiptExtraction,
                temperature=0,
                # Reading a receipt needs no reasoning; skipping it saves seconds.
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
        extraction = ReceiptExtraction.model_validate_json(response.text)
    except (ValidationError, ValueError, TypeError) as e:
        logger.warning("Gemini receipt extraction returned unusable output: %s", e)
        return None
    except Exception as e:
        logger.warning("Gemini receipt extraction failed: %s", redact(str(e), api_key))
        return None

    logger.info("Gemini receipt extraction took %.1fs", time.monotonic() - started)
    result = extraction.model_dump()
    result["date"] = _valid_date(extraction.date)
    return result
