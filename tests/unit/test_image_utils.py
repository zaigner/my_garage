"""Unit tests for my_garage.utils.images.convert_heif_to_jpeg."""

from __future__ import annotations

import io

import pillow_heif
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from my_garage.utils.images import convert_heif_to_jpeg


def heic_upload(name: str = "IMG_0423.HEIC") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    pillow_heif.from_pillow(Image.new("RGB", (64, 32), "red")).save(buffer)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/heic")


def jpeg_upload(name: str = "receipt.jpg") -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 32), "red").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/jpeg")


class TestConvertHeifToJpeg:
    def test_heic_becomes_jpeg(self):
        converted = convert_heif_to_jpeg(heic_upload())

        assert converted.name == "IMG_0423.jpg"
        assert converted.content_type == "image/jpeg"
        with Image.open(converted) as image:
            assert image.format == "JPEG"
            assert image.size == (64, 32)

    def test_other_formats_are_returned_unchanged_and_rewound(self):
        upload = jpeg_upload()

        converted = convert_heif_to_jpeg(upload)

        assert converted is upload
        assert converted.tell() == 0
