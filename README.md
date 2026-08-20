# My Garage: The Asset Management Platform for Collectors

**Track. Value. Manage. Enjoy.**

![Python](https://img.shields.io/badge/python-3.12-blue)
![Django](https://img.shields.io/badge/django-5.2_LTS-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

My Garage is a professional-grade, **self-hosted** asset management system for automotive enthusiasts, horologists, and collectors of all kinds. Whether you have a garage full of Porsches, a safe full of Patek Philippes, or a cellar full of vintage wines, My Garage tracks your portfolio's financial performance, manages service history, and plans your next big project.

**Own Your Data.** No subscriptions. No third-party accounts. Your collection, your server, your rules.

---

## What It Does

- Tracks vehicles, watches, and any custom collection type in one unified platform
- Pulls real market data to keep valuations current
- Manages service history, project kanban boards, and cost tracking
- Shows portfolio-level financial performance with year-over-year value tracking and a dedicated Insights analytics page
- Generates AI curator's notes for any collection item using Google Gemini
- Runs entirely on your own hardware — local dev, Docker Compose, or Kubernetes

---

## Core Features

### Unified Collection Architecture

Everything is a collection. Vehicles and timepieces are pre-configured system collections ("Garage" and "Horology Salon") built on the same engine as your custom collections. Add items, define custom fields, and manage service records and upgrades the same way across every asset type.

- **Custom Schemas**: Define fields (Vintage, Region, Artist, Edition) for any collection type
- **AI-Generated UI**: Gemini generates a Tailwind + Alpine.js component for each collection's item view
- **Personalized Empty States**: Collection-specific copy nudges users toward the first action ("What's in the garage?" for Automobiles, "Start your horological journey" for watches, etc.)
- **Item Relationships**: Link related items across collections (paired with, part of, inspired by)
- **File Attachments**: Attach receipts, certificates, appraisals, and manuals to any item

### Navigation & Notifications

- **Click-toggle hamburger**: Alpine.js click toggle with keyboard Escape and click-outside dismiss — works on touch devices
- **Floating toast notifications**: Django messages rendered as fixed top-right toasts (auto-dismiss after 5 s for success, dismissible X button, stacked for multiple messages — no page layout shift)
- **Onboarding checklist auto-completion**: `/welcome/` step-completion state driven by real DB queries — Steps 1/2/3 check off as the user adds items, gets a valuation, and logs a service record

### Portfolio Dashboard

The home page gives a live read on your entire collection's financial state:
- **Count-up animation** — hero portfolio value animates from 0 on each page load (cubic ease-out, 1.4 s)
- Total value broken out by asset category (Garage, Horology, custom collections)
- Year-over-year portfolio value change — backed by daily snapshots or purchase-price baseline when snapshots aren't yet available
- Recent acquisitions carousel with hover "View →" overlay
- Global search (⌘K) across every item you own, plus a persistent search icon in the nav

### Portfolio Insights

A dedicated `/insights/` analytics page provides:
- KPI cards: Total Value, Total Equity, and Items Tracked
- Category allocation bar chart — horizontal bars proportional to each category's share of portfolio value
- Top 3 items by current market value
- Year-over-year change badge (green/red)

### Cross-Collection Views

Navigate your entire portfolio from one place:
- **All Items** — every item across every collection, filterable
- **Value History** — valuation timeline across all assets
- **All Services** — unified service record log with **table/timeline toggle** (vertical timeline with colour-coded category dots)
- **All Upgrades** — kanban board spanning every collection

### Service & Project Management

- **Digital Service History**: Upload receipts, extract data via OCR, and categorize maintenance automatically
- **Drag-and-Drop Photo Upload**: Drop zone on item and service record forms — highlights gold on drag, shows thumbnail preview, chains OCR on service record receipts
- **Project Kanban Boards**: Plan upgrades and restorations with a drag-and-drop board — Wishlist → Ordered → In Progress → Completed
- **Cost Tracking**: Purchase price vs. current market value equity per item and across the portfolio

### AI-Powered Intelligence

- **Smart Valuations**: Live Marketcheck data for vehicles; brand/condition multiplier model for watches
- **Valuation Sparkline**: Item detail pages show an SVG sparkline trend chart above the valuation history list — gold for appreciation, red for depreciation
- **Receipt OCR**: Photograph a service receipt — vendor, date, cost, and line items are extracted automatically via pytesseract
- **AI Curator's Note**: One-click "Generate Description" on any item detail page — produces an auction-style curator's note via Gemini, displayed inline with a Regenerate button
- **Image Generation**: Create reference vehicle images via Google Gemini
- **Claude Code Integration**: Full MCP server — query your garage, look up valuations, and enrich asset data directly from Claude Code

### MCP Server

Six tools registered as a real FastMCP server on port 8001:

| Tool | Description |
|---|---|
| `lookup_vehicle_details` | Decode any VIN via NHTSA (free, no key) |
| `search_market_listings` | Find comparable vehicle listings via Marketcheck |
| `get_sales_stats` | Sold vehicle statistics by make/model/zip |
| `get_sales_history_by_vin` | Historical sale events for a specific VIN |
| `get_watch_valuation` | Estimated watch value by brand, condition, and completeness |
| `generate_vehicle_image` | Generate reference images via Google Gemini |
| `search_google_images` | Scrape stock photo URLs for any query |

---

## Stack

| Layer | Technology | Port |
|---|---|---|
| Web app | Django 5.2 LTS (ASGI via Uvicorn) | 8000 |
| AI / MCP services | FastAPI + FastMCP | 8001 |
| Task queue | Celery + Redis | — |
| Task scheduler | Celery Beat (DB-backed) | — |
| Primary DB | PostgreSQL (SQLite in dev) | 5432 |
| Vector / trace store | MongoDB 6.x | 27017 |
| Cache / broker | Redis 7 | 6379 |
| AI | Google Gemini (embeddings, image gen) | — |
| Package management | Pixi (conda-based, hermetic) | — |

---

## Getting Started

### Local Development (Recommended)

[Pixi](https://prefix.dev/) manages the Python environment. Docker Compose spins up the infrastructure services.

**Prerequisites:** Pixi, Docker

```bash
# 1. Clone
git clone https://github.com/zaigner/my-garage.git
cd my_garage

# 2. Install Python dependencies
pixi install

# 3. Configure environment
cp .env.example .env
# Edit .env — at minimum set SECRET_KEY and REDIS_URL

# 4. Start infrastructure (Postgres, Redis, MongoDB)
docker compose up postgres redis mongodb -d

# 5. Apply migrations and start services
pixi run migrate
pixi run server       # Django on :8000
pixi run fastapi      # FastAPI + MCP on :8001
pixi run worker       # Celery worker (background tasks)
```

Open `http://localhost:8000` and register an account.

### Full Container Stack (Docker Compose)

Runs everything — app services included — from the built image. Useful for testing the production image before deploying.

```bash
docker compose --profile app up --build
```

Django will be available at `http://localhost:8000`.

> **Note:** The production settings enforce `SECURE_SSL_REDIRECT=True`. Set `SECURE_SSL_REDIRECT=False` in your `.env` or the compose `environment` block when testing locally without HTTPS. Note that `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` stay `True` regardless, so login will not work over plain HTTP — see [Deployment Architecture](#ingress-and-tls).

### Kubernetes

Production manifests live in `k8s/`. The namespace, ConfigMap, Secrets, and per-service Deployments/StatefulSets/Services are all included.

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets/        # fill in secrets first — see k8s/secrets/README.md
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/postgres/
kubectl apply -f k8s/redis/
kubectl apply -f k8s/mongodb/
kubectl apply -f k8s/django/
kubectl apply -f k8s/fastapi/
kubectl apply -f k8s/celery/
kubectl apply -f k8s/ci/             # optional — self-hosted deploy runner
```

The Django deployment uses `ghcr.io/zaigner/my-garage:latest`. The image is built with a multi-stage Dockerfile (pixi prod environment → lean Debian runtime) and includes tesseract-ocr for the OCR service.

---

## Deployment Architecture

The reference deployment is a two-node **K3s** cluster on Raspberry Pi 5s, backed by a Synology NAS. Everything below is described by role — concrete addresses live in a separate private infrastructure repository, never in application config.

```
                 ┌──────────── GitHub ────────────┐
   git push  ──▶ │  CI  ──▶  Build  ──▶  Deploy   │
                 └────────────────┬───────────────┘
                    ghcr.io image │ (job claimed by
                                  │  runner, outbound)
   ┌──────────────────────────────┼─────────────────────────────┐
   │  K3s cluster                 ▼                             │
   │   ┌────────────────┐   ┌──────────────┐                    │
   │   │ control plane  │   │ worker node  │  self-hosted runner│
   │   └────────────────┘   └──────────────┘  (ci namespace)    │
   │                                                            │
   │   Traefik Ingress ──▶ django :8000 · fastapi :8001         │
   │        ▲ MetalLB LoadBalancer address                      │
   │        │                                                   │
   │   Storage:  nfs-client (NAS)  ·  local-path (node-local)   │
   └────────────────────────────────────────────────────────────┘
```

### Ingress and TLS

Traefik terminates TLS and routes by path — `/api/mcp` to FastAPI, everything else to Django. The Ingress must be bound to **both** the `web` and `websecure` entrypoints:

```yaml
traefik.ingress.kubernetes.io/router.entrypoints: web,websecure
```

**HTTPS is required, not optional.** `config/settings/production.py` sets `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE`, so over plain HTTP the browser never returns the session or CSRF cookie — the login form accepts a password and silently bounces you back. With `web` alone, Traefik serves no HTTPS router while Django's `SECURE_SSL_REDIRECT` still redirects to `https://`, producing a 301 → 404 loop.

`SECURE_PROXY_SSL_HEADER` trusts Traefik's `X-Forwarded-Proto`, so Django knows the original request was HTTPS even though the internal hop is plain HTTP. Without a real certificate, Traefik serves its built-in self-signed one — expect a one-time browser warning.

Any host used to reach the app must appear in `ALLOWED_HOSTS` (`k8s/configmap.yaml`), or Django returns `400 DisallowedHost`.

**`my-garage.zachelorpad.com` is the exception to all of the above.** It's reached through the Cloudflare Tunnel (`zaigner/infra`'s `dns.cloudflare.routes`), which dials this same Traefik LoadBalancer over plain HTTP — Cloudflare Access terminates TLS at the edge instead, so there's no in-cluster HTTPS hop for this host at all. `SECURE_SSL_REDIRECT` is set to `False` in `k8s/configmap.yaml` so Django doesn't try to force an already-secure-at-the-edge request into a redirect loop the way it would with `web` alone for `my-garage.local`. `SESSION_COOKIE_SECURE`/`CSRF_COOKIE_SECURE` stay `True` either way. An Access application in the Cloudflare Zero Trust dashboard (Access controls → Applications, Public DNS, host `my-garage.zachelorpad.com`) gates who can reach it before the request ever hits this Ingress.

### Storage

Two storage classes, chosen deliberately per workload:

| Workload | Class | Why |
|---|---|---|
| PostgreSQL | `nfs-client` (NAS) | Survives node loss; NFS is fine for its access pattern |
| MongoDB | `local-path` (node-local) | **Must not** run on NFS — see below |
| Django media | `nfs-client` (NAS) | Shared across replicas |

> **MongoDB on NFS corrupts.** WiredTiger requires POSIX locking and write-ordering guarantees that NFS does not provide. Running it on an NFS PersistentVolume produced `WiredTiger metadata corruption detected` and thousands of crash-restarts. A single-replica StatefulSet gains nothing from network storage, so it uses `local-path`. The trade-off is that its data is pinned to one node.

NFS-backed PersistentVolumes have an important constraint: **`spec.nfs.server` is immutable.** If the NAS address changes, the PVs cannot be patched — they must be deleted and recreated with the same `spec.nfs.path`. Verify `persistentVolumeReclaimPolicy: Retain` on every PV before deleting anything, or the provisioner may remove the underlying directory.

### CI/CD

```
push to main → CI (lint + tests) → Build (multi-arch amd64/arm64 → ghcr.io) → Deploy
```

Each stage triggers on the previous one's success via `workflow_run`, so a failing test never produces an image and a failed build never deploys.

**Deploy runs on a self-hosted runner inside the cluster** (`k8s/ci/`), not on a GitHub-hosted runner. This is a requirement, not a preference: the cluster sits on a private network with no inbound route from GitHub's cloud, so a hosted runner cannot reach it at all — whether by SSH or any other means.

The runner polls GitHub outbound, which means:

- no inbound firewall rule or port forwarding
- no SSH private key stored in GitHub secrets
- authentication via ServiceAccount rather than a root-owned kubeconfig

Its RBAC (`k8s/ci/rbac.yaml`) grants only `get`/`list`/`watch`/`patch` on Deployments in the app namespace — enough for `kubectl set image` and `kubectl rollout status`, and nothing else. It cannot read Secrets, touch other namespaces, or create Pods.

Registration survives pod restarts: an initContainer seeds the runner home onto a PVC, so the runner's credentials persist and no long-lived personal access token has to be stored in the cluster.

> Never enable this runner for pull requests from forks. A fork PR would execute untrusted code on a runner holding cluster credentials. The `workflow_run` on `main` trigger is safe.

---

## Key Commands

```bash
pixi run server           # Django dev server (:8000)
pixi run fastapi          # FastAPI + MCP server (:8001)
pixi run worker           # Celery worker
pixi run beat             # Celery Beat scheduler
pixi run migrate          # Apply database migrations
pixi run pytest           # Run all tests
pixi run lint             # Ruff lint
pixi run format           # Ruff format
pixi run refresh-context  # Rebuild BMAD portfolio context file
pixi run manage build_knowledge_index  # Rebuild RAG index from docs
```

---

## Environment Variables

Copy `.env.example` to `.env`. The required variables:

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key |
| `REDIS_URL` | Yes | Celery broker (`redis://localhost:6379/0`) |
| `MONGO_URI` | Yes | MongoDB connection (`mongodb://localhost:27017/`) |
| `GOOGLE_API_KEY` | For AI features | Gemini embeddings, image generation |
| `MARKETCHECK_API_KEY` | For vehicle valuations | Live market listings + sales stats |
| `DB_*` | Production only | PostgreSQL connection (dev uses SQLite) |

---

## Project Structure

```
src/
  config/                   # Django project config (settings, urls, celery)
  my_garage/                # Primary Django application
    models.py               # CollectionType, DynamicCollectionItem, and supporting models
    views.py                # Collection, item, service, upgrade, kanban views
    api/                    # DRF ViewSets, selectors (read queries), services (writes)
    services/               # ContextService — AI context assembly (RAG + structured data)
    skills/                 # CollectionThemeGenerator — AI schema + UI generation
    utils/                  # mongo.py, tracing.py, chunker.py, prompt_renderer.py
    prompts/                # Jinja2 prompt templates (vehicle_valuation, receipt_analysis, etc.)
    tasks.py                # Celery tasks (OCR, valuations, snapshots, enrichment)
  fastapi_services/         # FastAPI application (port 8001)
    mcp/                    # FastMCP server — tool registration and implementations
    ocr/                    # OCR router (pytesseract + receipt parser)
tests/
  unit/                     # Pure Python — utils, context service, selectors
  functional/               # Django test client — views, models, forms
  fastapi/                  # FastAPI TestClient — MCP tools, OCR routes
  eval/                     # MCP tool quality + RAG retrieval evals (hits real APIs)
k8s/                        # Kubernetes manifests
  django/ fastapi/ celery/  # app Deployments, Services, Ingress
  postgres/ mongodb/ redis/ # StatefulSets and their storage classes
  ci/                       # self-hosted GitHub Actions runner + scoped RBAC
docs/                       # Implementation plans and UX specs
```

---

## Roadmap

- [x] Unified collection architecture — all asset types on one engine
- [x] Vehicle tracking (Garage collection) with VIN decoding
- [x] Timepiece tracking (Horology Salon collection) with condition grading
- [x] Custom collection schemas with AI-generated UI components
- [x] Kanban project boards for upgrades and restorations
- [x] Receipt OCR — vendor, date, and cost extracted from photos
- [x] Vehicle market valuations via Marketcheck
- [x] Watch valuations — brand/condition/completeness model
- [x] Portfolio dashboard with year-over-year value tracking and count-up animation
- [x] Cross-collection unified views (all items, all services with timeline toggle, all upgrades, value history)
- [x] MCP server — Claude Code integration with 6 registered tools
- [x] RAG knowledge layer — MongoDB-backed vector search over project docs
- [x] Docker Compose + Kubernetes deployment
- [x] **HTTPS ingress via Traefik** — TLS termination with secure session/CSRF cookies
- [x] **Automated deploys** — self-hosted in-cluster runner with least-privilege RBAC
- [x] **Portfolio Insights page** — category allocation bars, KPI cards, top items
- [x] **AI Curator's Note** — Gemini-generated auction-style item descriptions
- [x] **Valuation sparkline** — SVG trend chart in item detail Valuations tab
- [x] **Drag-and-drop photo upload** — drop zone with preview on item and service record forms
- [x] **Floating toast notifications** — fixed top-right, auto-dismiss, luxury aesthetic
- [x] **Click-toggle navigation** — Alpine.js hamburger with keyboard / touch support
- [x] **Personalized empty states** — collection-type-specific copy
- [x] **Onboarding auto-completion** — checklist driven by real DB state
- [ ] **WatchCharts Integration**: Live secondary market data for timepieces (currently a mock model)
- [ ] **Price Alerts**: Notify when a comparable listing drops below a threshold
- [ ] **360° Spin Viewer**: Interactive vehicle rotation via Imagin.Studio or similar

---

## Contributing

This is a personal project in active development — issues and ideas welcome. If you want to contribute, open an issue to discuss first.

---

*Built with ADHD*
