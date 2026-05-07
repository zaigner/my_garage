"""
Root conftest.py — configures Django settings for pytest-django.
DJANGO_SETTINGS_MODULE is also set in pyproject.toml [tool.pytest.ini_options],
but this file ensures it's available when modules are imported at collection time.
"""

import os


def pytest_configure(config):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
