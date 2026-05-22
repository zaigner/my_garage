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
COPY templates/ ./templates/
COPY static/ ./static/

# Collect static files into staticfiles/ at build time.
# Uses a placeholder key — collectstatic doesn't touch the database.
# logs/ must exist before Django starts: production settings wire a RotatingFileHandler
# that dictConfig opens at import time, before collectstatic even runs.
RUN mkdir -p logs

RUN DJANGO_SECRET_KEY=build-placeholder \
    ALLOWED_HOSTS=localhost \
    PYTHONPATH=/app/src \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DJANGO_ENVIRONMENT=production \
    .pixi/envs/prod/bin/python manage.py collectstatic --noinput

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

# Copy the pixi production conda environment to the same path as the builder
# so hardcoded shebangs (e.g. #!/app/.pixi/envs/prod/bin/python) still resolve.
COPY --from=builder /app/.pixi/envs/prod /app/.pixi/envs/prod

# Copy application source and manage.py
COPY --from=builder /app/src /app/src
COPY --from=builder /app/manage.py /app/manage.py
COPY --from=builder /app/templates /app/templates
COPY --from=builder /app/static /app/static
COPY --from=builder /app/staticfiles /app/staticfiles

# Entrypoint runs migrations then execs the CMD
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create writable directories Django needs at runtime
RUN mkdir -p /app/logs /app/media \
    && chown -R appuser:appuser /app

USER appuser

ENV PATH="/app/.pixi/envs/prod/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV DJANGO_SETTINGS_MODULE="config.settings.production"

# Document ports — actual binding controlled by CMD / K8s
EXPOSE 8000 8001

# ──────────────────────────────────────────────────
# Default: Django via uvicorn (ASGI)
# entrypoint.sh runs migrations before exec'ing this CMD.
#
# Override CMD in K8s Deployments for other services:
#   FastAPI + MCP server:
#     uvicorn fastapi_services.main:app --host 0.0.0.0 --port 8001 --workers 1
#   Celery worker:
#     celery -A config.celery_app worker -l info
#   Celery beat (always 1 replica — never scale):
#     celery -A config.celery_app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
# ──────────────────────────────────────────────────
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "config.asgi:application", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2"]
