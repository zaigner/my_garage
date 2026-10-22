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
# Base images are pinned by digest. A floating tag (`latest`, `bookworm-slim`)
# silently changes whenever upstream republishes, which rebuilds every layer and
# turns a ~6 MB code-only deploy into a full ~330 MB pull on each Pi
# (2026-10-22). Bump these deliberately: `docker buildx imagetools inspect <tag>`
# prints the index digest. Expect a full re-pull on the deploy that bumps them.
FROM ghcr.io/prefix-dev/pixi:0.82.1@sha256:f83a5fc6d1bb9a2ced27faf2b26c04c5eb618eed22fe13eb60f9225db4817ce0 AS builder

WORKDIR /app

# Dependency manifests first → layer cache reuse when only src changes
COPY pixi.toml pixi.lock ./

# Install production environment only (no pytest, ruff, ipython, etc.)
# prod = [] in pixi.toml → base [dependencies] + [pypi-dependencies] only
RUN pixi install --environment prod --locked

# Precompile dependency bytecode. PyPI packages ship without .pyc files, so
# every container start used to compile thousands of modules before serving —
# slow on a Pi, and repeated on each restart because the cache died with the
# container. unchecked-hash makes Python trust these files without comparing
# source mtimes, which do not survive image layering reliably.
# Some packages bundle files that are not valid Python 3; ignore those.
RUN .pixi/envs/prod/bin/python -m compileall -q -j 0 \
        --invalidation-mode unchecked-hash \
        .pixi/envs/prod/lib/python3.12/site-packages || true

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

# Same for the application code. -f replaces the mtime-based .pyc files that
# collectstatic just wrote as a side effect of importing the project.
RUN .pixi/envs/prod/bin/python -m compileall -q -f \
        --invalidation-mode unchecked-hash src

# ──────────────────────────────────────────────────
# Stage 2: Runtime — lean image, no pixi tooling
# ──────────────────────────────────────────────────
FROM debian:bookworm-slim@sha256:7ff6ba31527b9e336162fa061746c366c4b2032f4d2cff2078bea43f78efe3f8 AS runtime

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

# Writable directories Django needs at runtime. Created before the big COPYs
# and chowned non-recursively on purpose: a trailing `chown -R /app` rewrote
# every file into a new layer, duplicating the whole conda environment (~240 MB
# compressed) in a layer that changed on every build. Each deploy made the Pis
# download and unpack that copy again, which is what pushed rollouts past the
# deploy timeout.
RUN mkdir -p /app/logs /app/media \
    && chown appuser:appuser /app /app/logs /app/media

# Copy the pixi production conda environment to the same path as the builder
# so hardcoded shebangs (e.g. #!/app/.pixi/envs/prod/bin/python) still resolve.
# Left root-owned: nothing writes to it at runtime. This layer only changes
# when pixi.lock does, so nodes that already have it skip it on deploy.
COPY --from=builder /app/.pixi/envs/prod /app/.pixi/envs/prod

# Copy application source and manage.py. These small layers are all a node
# has to pull for a code-only change.
COPY --from=builder --chown=appuser:appuser /app/src /app/src
COPY --from=builder --chown=appuser:appuser /app/manage.py /app/manage.py
COPY --from=builder --chown=appuser:appuser /app/templates /app/templates
COPY --from=builder --chown=appuser:appuser /app/staticfiles /app/staticfiles

# The raw static/ sources are not copied: Django serves staticfiles/, which
# collectstatic built from them, and shipping both put every static asset in
# the image twice. The directory only has to exist because STATICFILES_DIRS
# names it; an absent one makes every startup print a system-check warning.
# Created here, not with logs/ above, because changing that earlier step would
# invalidate the dependency layer below it and force every node to re-pull it.
RUN mkdir /app/static

# Entrypoint runs migrations then execs the CMD
COPY --chown=appuser:appuser --chmod=755 entrypoint.sh /app/entrypoint.sh

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
