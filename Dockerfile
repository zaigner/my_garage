# ─────────────────────────────────────────────────────────────────
# PREREQUISITE: linux-aarch64 must be in pixi.toml platforms list
# before building for the K3s cluster (Raspberry Pi 5 = ARM64).
# Add it and regenerate the lock file:
#   1. Edit pixi.toml platforms → add "linux-aarch64"
#   2. Run: pixi install          (updates pixi.lock)
#   3. Commit pixi.toml + pixi.lock
# ─────────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────
# Stage 1: Builder — install pixi + production deps
# ──────────────────────────────────────────────────
FROM ghcr.io/prefix-dev/pixi:latest AS builder

WORKDIR /app

# Dependency manifests first → layer cache reuse when only src changes
COPY pixi.toml pixi.lock ./

# Install production environment only (no pytest, ruff, ipython, etc.)
# prod = [] in pixi.toml → base [dependencies] + [pypi-dependencies] only
RUN pixi install --environment prod --locked

# Copy source after deps are installed
COPY src/ ./src/
COPY manage.py ./

# ──────────────────────────────────────────────────
# Stage 2: Runtime — lean image, no pixi tooling
# ──────────────────────────────────────────────────
FROM debian:bookworm-slim AS runtime

WORKDIR /app

# System dependencies:
#   tesseract-ocr  → required by pytesseract (OCR service)
#   libpq5         → PostgreSQL client library for psycopg2
#   ca-certificates→ HTTPS calls to external APIs
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libpq5 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for container security
RUN useradd -m -u 1000 -s /bin/bash appuser

# Copy the pixi production conda environment (not pixi itself)
COPY --from=builder /app/.pixi/envs/prod /opt/env

# Copy application source and manage.py
COPY --from=builder /app/src /app/src
COPY --from=builder /app/manage.py /app/manage.py

# Create writable directories Django needs at runtime
RUN mkdir -p /app/logs /app/media /app/staticfiles \
    && chown -R appuser:appuser /app

USER appuser

# Activate the conda environment by putting it on PATH
ENV PATH="/opt/env/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV DJANGO_SETTINGS_MODULE="config.settings.production"

# Document ports — actual binding controlled by CMD / K8s
EXPOSE 8000 8001

# ──────────────────────────────────────────────────
# Default: Django via uvicorn (ASGI)
# Override CMD in K8s Deployments for other services:
#
#   FastAPI + MCP server:
#     uvicorn fastapi_services.main:app --host 0.0.0.0 --port 8001 --workers 1
#
#   Celery worker:
#     celery -A config.celery_app worker -l info
#
#   Celery beat (always 1 replica — never scale):
#     celery -A config.celery_app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
#
# NOTE: production.py has SECURE_SSL_REDIRECT = True. When running behind
# Traefik (which terminates SSL), this causes redirect loops for HTTP traffic.
# Add to src/config/settings/production.py before deploying:
#   SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# This lets Django trust Traefik's X-Forwarded-Proto header instead.
# ──────────────────────────────────────────────────
CMD ["uvicorn", "config.asgi:application", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2"]
