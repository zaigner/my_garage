"""The recorder settings must never fall back to the real database."""

from __future__ import annotations

import importlib
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured

MODULE = "config.settings.tutorials"


@pytest.fixture(autouse=True)
def _clean_module():
    yield
    sys.modules.pop(MODULE, None)


def test_refuses_to_run_without_db_path(monkeypatch):
    monkeypatch.delenv("TUTORIALS_DB_PATH", raising=False)
    sys.modules.pop(MODULE, None)
    with pytest.raises(ImproperlyConfigured, match="TUTORIALS_DB_PATH"):
        importlib.import_module(MODULE)


def test_uses_given_db_and_drops_debug_toolbar(monkeypatch, tmp_path):
    db = str(tmp_path / "t.sqlite3")
    monkeypatch.setenv("TUTORIALS_DB_PATH", db)
    sys.modules.pop(MODULE, None)
    mod = importlib.import_module(MODULE)
    assert mod.DATABASES["default"]["NAME"] == db
    assert not any("debug_toolbar" in a for a in mod.INSTALLED_APPS)
    assert not any("debug_toolbar" in m for m in mod.MIDDLEWARE)
    assert mod.CELERY_TASK_ALWAYS_EAGER is True
