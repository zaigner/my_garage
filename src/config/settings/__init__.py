"""Settings package initialization."""

import os

# Resolve which environment to activate.
# Prefer DJANGO_SETTINGS_MODULE (Django's own mechanism) so that explicit
# module overrides (e.g. in the Dockerfile or test runners) always win.
# Fall back to DJANGO_ENVIRONMENT for convenience in local dev.
_dsm = os.environ.get("DJANGO_SETTINGS_MODULE", "")
if "production" in _dsm:
    _env = "production"
elif "test" in _dsm:
    _env = "test"
else:
    _env = os.environ.get("DJANGO_ENVIRONMENT", "local")

if _env == "production":
    from .production import *
elif _env == "test":
    from .test import *
else:
    from .local import *
