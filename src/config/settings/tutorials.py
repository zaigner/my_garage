"""Settings for the tutorial-video recorder (``pixi run record-tutorials``).

Runs the app against a throwaway SQLite file whose path the recorder passes in
``TUTORIALS_DB_PATH``. It must never fall back to ``db.sqlite3``.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .local import *  # noqa: F403
from .local import INSTALLED_APPS, MIDDLEWARE

_db_path = os.environ.get("TUTORIALS_DB_PATH")
if not _db_path:
    raise ImproperlyConfigured("TUTORIALS_DB_PATH is not set in environment")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": _db_path,
    }
}

# The debug toolbar would overlay every recorded page.
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]
MIDDLEWARE = [m for m in MIDDLEWARE if not m.startswith("debug_toolbar")]
INTERNAL_IPS: list[str] = []

CELERY_TASK_ALWAYS_EAGER = True
