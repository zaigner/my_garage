"""
Image upload helpers.

iPhone photos are HEIC by default and stay HEIC when emailed or downloaded.
Pillow reads them once pillow-heif's opener is registered (MyGarageConfig.ready),
but only Safari displays HEIC, so uploads are stored as JPEG instead.
"""

from __future__ import annotations

import io
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from PIL import Image, ImageOps

HEIF_FORMATS = frozenset({"HEIF", "HEIC"})
JPEG_QUALITY = 90


def convert_heif_to_jpeg(upload: UploadedFile) -> UploadedFile:
    """
    Return a JPEG copy of a HEIC/HEIF upload, or the upload unchanged if it is
    any other format.
    """
    upload.seek(0)
    with Image.open(upload) as image:
        if image.format not in HEIF_FORMATS:
            upload.seek(0)
            return upload
        # Bake in any EXIF rotation so the JPEG displays (and OCRs) upright.
        image = ImageOps.exif_transpose(image).convert("RGB")
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=JPEG_QUALITY)

    name = f"{Path(upload.name).stem}.jpg"
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")
