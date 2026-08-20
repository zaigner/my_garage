"""Production settings."""

from .base import *

DEBUG = False

# Set this in your environment variables
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Static files — compressed + hashed filenames for long-term caching
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Security settings
# Trust X-Forwarded-Proto header from Traefik — prevents redirect loops when
# Traefik terminates HTTPS and forwards plain HTTP internally to Django.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "True") == "True"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# ALLOWED_HOSTS carries bare hostnames; Django's CSRF check compares against Origin,
# which includes the scheme. For my-garage.local/the LB IP, Traefik's real websecure
# entrypoint always reports https, so Django's default same-origin check passes
# without this. For my-garage.zachelorpad.com the Cloudflare Tunnel hop to Traefik is
# plain HTTP -- Access already terminated TLS at the edge -- so Traefik reports the
# request as http regardless of what the browser actually used, and the same-origin
# check fails against a genuine https Origin from the browser. Trusting the origin
# explicitly, the same fix portfolio-research already needed, sidesteps that.
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host]
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# HSTS settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Email settings - configure for production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
