"""
Guards for production static file handling.

Production serves static files through WhiteNoise's manifest storage, where
``{% static 'path' %}`` raises ValueError — a 500 — for any file collectstatic
did not find. Tests run with plain storage and would not notice, so check the
references directly.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.staticfiles import finders

STATIC_TAG_RE = re.compile(r"""\{%\s*static\s+['"]([^'"]+)['"]\s*%\}""")

TEMPLATE_DIRS = [
    Path(settings.BASE_DIR) / "templates",
    Path(settings.BASE_DIR) / "src" / "my_garage" / "templates",
]


def _static_references() -> list[tuple[str, str]]:
    refs = set()
    for template_dir in TEMPLATE_DIRS:
        for template in template_dir.rglob("*.html"):
            for path in STATIC_TAG_RE.findall(template.read_text(encoding="utf-8")):
                refs.add((str(template.relative_to(settings.BASE_DIR)), path))
    return sorted(refs)


STATIC_REFERENCES = _static_references()


def test_templates_reference_static_files():
    """The scan must find something, or the test below passes vacuously."""
    assert STATIC_REFERENCES


@pytest.mark.parametrize(("template", "path"), STATIC_REFERENCES)
def test_static_reference_resolves(template, path):
    assert finders.find(path) is not None, f"{template} references missing {path}"


def test_production_uses_whitenoise_manifest_storage():
    production = importlib.import_module("config.settings.production")

    assert production.STORAGES["staticfiles"]["BACKEND"] == (
        "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )
    # Removed in Django 5.1 and silently ignored — it must not come back as
    # the only place the storage is configured.
    assert not hasattr(production, "STATICFILES_STORAGE")
