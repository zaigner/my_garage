# AI Harness & Context Engineering — Revised Implementation Plan

**Status:** Decisions locked — ready to execute
**Objective:** Elevate `my_garage` to best-in-class AI harness and context engineering practices by building on existing infrastructure (BMAD, FastAPI MCP, MongoDB) rather than around it.

## Decisions Locked

| Question | Decision | Rationale |
|---|---|---|
| Embedding model | **Google Embedding API** (`google-genai` already in `pixi.toml`) | `sentence-transformers` pulls ~2GB PyTorch with identical code surface |
| MCP transport | **HTTP (FastAPI service)** — keep single service on port 8001 | Simpler ops; Django→FastAPI bridge already established |
| BMAD project context | **Live data** — management command refreshes on schedule | Context stays accurate as project evolves |
| Trace retention | **30-day TTL** index on `ai_traces` MongoDB collection | Enough for debugging; prevents unbounded growth |

---

## Situation Assessment

Before a single line is written, here is what already exists and must be preserved:

| Existing Asset | What It Is | Status |
|---|---|---|
| `_bmad/` + `.claude/commands/` | Full BMAD agent harness (~70 slash commands) | **Keep as-is. Build on top.** |
| `src/fastapi_services/mcp/` | Custom REST API that mimics MCP | **Convert to real MCP server** |
| `src/fastapi_services/mcp/tools/` | Typed Python functions with Pydantic input models | **Keep. Already correct pattern.** |
| `src/fastapi_services/mcp/config.py` | Pydantic Settings for API keys | **Extend, not replace** |
| `src/my_garage/api/` | DRF selectors/services layer | **Compose into Context Service** |
| `utils/mongo.py` | MongoDB connection utility | **Foundation for RAG store** |
| `.specify/specs/` | Platform specification docs | **Primary RAG knowledge source** |

**The single most impactful architectural decision:** The current MCP setup is a custom FastAPI REST router (`/mcp/execute`). This is not an MCP server. Converting it to use the `mcp` Python SDK creates a real MCP server that Claude Code connects to natively — all tools become directly available in Claude without any Django→FastAPI HTTP bridge.

---

## Phase 0 — Prerequisite: Real MCP Server

**Why first:** Every subsequent phase depends on a proper tool interface. The current if/elif dispatch in `mcp/main.py` is a dead end — it doesn't support tool discovery, schema generation, or native Claude Code integration.

### 0.1 — Convert FastAPI MCP Router to MCP SDK Server

**Current state:** `src/fastapi_services/mcp/main.py` dispatches tool calls via a manual if/elif chain. Claude cannot discover tools; every call requires knowing the exact `tool_name` string.

**Target state:** A proper MCP server where each tool is registered with its schema, discoverable by Claude Code, and callable directly without the HTTP bridge.

**Transport: HTTP.** The FastAPI service stays on port 8001. Claude Code connects to it via `http` transport in `mcpServers` config. The existing Django→FastAPI bridge is preserved.

**Steps:**
1. Add `mcp[fastapi]` to `pixi.toml` dependencies
2. Refactor `src/fastapi_services/mcp/main.py`:
   - Remove `MCPRequest` router and if/elif dispatch
   - Instantiate `FastApiMCP` and register each tool with `@mcp.tool()` decorator
   - Each tool's input schema auto-generates from the existing Pydantic `*Input` models (already written)
3. Mount the MCP server in `src/fastapi_services/main.py` via `mcp.mount()` — keeps `/docs`, `/ocr`, and `/mcp` all in one service
4. Register in `.claude/settings.local.json`:
   ```json
   "mcpServers": {
     "my-garage": {
       "type": "http",
       "url": "http://localhost:8001/mcp"
     }
   }
   ```
5. Verify: `pixi run fastapi` then `claude mcp list` shows all 7 tools

**Files to change:**
- `src/fastapi_services/mcp/main.py` — full refactor
- `src/fastapi_services/main.py` — mount MCP server
- `.claude/settings.local.json` — add `mcpServers` config
- `pixi.toml` — add `mcp` dependency

**Acceptance:** Running `pixi run fastapi` and then `/mcp` in Claude Code shows all tools (vehicle_lookup, market_valuation, sales_stats, watch_valuation, image_generation, google_search + ocr).

---

## Phase 1 — Context Engineering

### 1.1 — Context Service

**Problem:** Context for AI calls is gathered ad-hoc in views and Celery tasks. There is no single place that knows how to assemble context for a given asset.

**Solution:** A `ContextService` class that composes the existing DRF selector/service layer. It does not bypass the ORM — it calls the selectors that already exist in `src/my_garage/api/`.

**Location:** `src/my_garage/services/context_service.py`

**Interface (to implement):**
```python
class ContextService:
    def get_vehicle_context(self, vehicle_id: int, user) -> dict
    def get_timepiece_context(self, timepiece_id: int, user) -> dict
    def get_collection_item_context(self, item_id: int, user) -> dict
    def get_portfolio_summary(self, user) -> dict
    def retrieve_relevant_docs(self, query: str, k: int = 5) -> list[str]  # RAG
```

Each method returns a typed dict (Pydantic model) that can be serialized directly into a prompt template. The `retrieve_relevant_docs` method is wired to the RAG pipeline in 1.2.

**Files to create/change:**
- `src/my_garage/services/context_service.py` — new file
- `src/my_garage/services/__init__.py` — new file (package)

### 1.2 — RAG Pipeline for Knowledge Docs

**Problem:** The project has rich unstructured domain knowledge in `.md` files (`SERVICE_RECORDS_GUIDE.md`, `UPGRADES_KANBAN_GUIDE.md`, `DYNAMIC_COLLECTIONS_GUIDE.md`, `.specify/specs/`) that the AI cannot access without retrieval.

**Solution:** Use MongoDB Atlas Vector Search (already in-stack, zero new infrastructure) to index chunked `.md` files. The `ContextService.retrieve_relevant_docs()` method queries this index.

**Steps:**
1. No new dependencies — `google-genai` is already in `pixi.toml`
2. Create `src/my_garage/management/commands/build_knowledge_index.py`:
   - Reads all `.md` files from `docs/`, project root, and `.specify/specs/`
   - Chunks by section (split on `##` headers, max 500 tokens per chunk)
   - Embeds each chunk via `google.genai.embed_content(model="text-embedding-004", ...)`
   - Upserts to MongoDB collection `knowledge_chunks` with fields: `content`, `source`, `embedding`
3. Create MongoDB Vector Search index on `knowledge_chunks.embedding` (local MongoDB supports this from v7.0+; verify `mongod --version`)
4. Wire `ContextService.retrieve_relevant_docs()` to embed the query and run `$vectorSearch` aggregation

**Files to create:**
- `src/my_garage/management/commands/build_knowledge_index.py`
- `src/my_garage/utils/chunker.py` — text chunking utilities

**Run once to build index:**
```bash
pixi run manage build_knowledge_index
```

### 1.3 — Pydantic Config Validation

**Problem:** `config.py` in the MCP service uses `Optional[str] = None` for all API keys, allowing the server to start silently with broken tools.

**Solution:** Extend `config.py` with validation that warns (but does not crash) at startup when keys are missing, and tags which tools are available. This feeds the MCP tool registry so Claude does not call tools that will fail.

**Files to change:**
- `src/fastapi_services/mcp/config.py` — add `@property` methods for `available_tools`

---

## Phase 2 — Prompt Engineering & Harness Integration

### 2.1 — Prompt Templates

**Problem:** Prompts are inline strings scattered across views and tasks. Changes are risky and untestable.

**Solution:** Jinja2 templates for all prompts. Templates live in `src/my_garage/prompts/` as `.j2` files. The `ContextService` assembles context dicts that feed directly into these templates.

**Template structure:**
```
src/my_garage/prompts/
├── vehicle_valuation.j2
├── service_record_analysis.j2
├── condition_assessment.j2
└── collection_item_description.j2
```

Each template receives a typed Pydantic context dict. No string formatting outside of Jinja2.

**Files to create:**
- `src/my_garage/prompts/` directory with `.j2` templates
- `src/my_garage/utils/prompt_renderer.py` — thin wrapper around `jinja2.Environment`

### 2.2 — BMAD Integration (Extend, Don't Replace)

The BMAD system in `_bmad/` + `.claude/commands/` is the AI harness. It already provides agent definitions, workflows, and slash commands. **Do not build a parallel orchestrator.**

**Gap to fill:** BMAD agents currently have no project-specific context injection. When a BMAD agent runs, it doesn't automatically load vehicle data, service records, or the platform spec.

**Solution:** Create a `_bmad/_config/` project context file that the `bmad-bmm-generate-project-context` command already supports. This wires the platform spec and current data model into every BMAD session.

**Steps:**
1. Run `/bmad-bmm-generate-project-context` to create the initial `_bmad/_memory/project-context.md`
2. Edit the output to include: live data model summary, active API tools list, URL structure, current collection types
3. Create `src/my_garage/management/commands/refresh_bmad_context.py`:
   - Queries current stats: vehicle count, timepiece count, active collections, total portfolio value
   - Reads the static sections from `_bmad/_memory/project-context.md`
   - Rewrites the `## Current Project State` section with fresh data
   - Safe to run on a schedule (idempotent)
4. Add `pixi run refresh-context` task to `pixi.toml`
5. Add to Celery Beat schedule: run `refresh_bmad_context` daily at midnight

**Files to create/update:**
- `_bmad/_memory/project-context.md` — generated, then kept live
- `src/my_garage/management/commands/refresh_bmad_context.py` — new file
- `pixi.toml` — add `refresh-context` task
- Celery Beat schedule in `config/settings/base.py`

### 2.3 — Claude Code Hooks for Development Workflow

Use Claude Code hooks (configured in `.claude/settings.local.json`) to automate context injection for recurring development patterns.

**Hooks to add:**
- **Pre-tool hook on `Edit` for `migrations/`**: Remind to run `makemigrations` after model changes
- **Post-tool hook on model file edits**: Auto-suggest updating `context_service.py` if new model fields added
- **PreToolUse on Bash**: Warn if running `python` without `PYTHONPATH=src`

These are configured in `.claude/settings.local.json` under `hooks`, not in Python code.

---

## Phase 3 — Evaluation & Monitoring

### 3.1 — Structured Trace Logging

**Problem:** No visibility into what context was assembled, what prompt was sent, or what the model returned for any given AI interaction.

**Solution:** Every LLM interaction logs a structured trace to MongoDB (`ai_traces` collection). Traces are queryable and support debugging without external services.

**Trace schema:**
```python
class AITrace(BaseModel):
    task_id: str          # UUID
    timestamp: datetime
    tool_name: str        # which MCP tool or context method
    context_summary: dict # keys and sizes of context assembled
    prompt_template: str  # template name used
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: int
    success: bool
    error: str | None
```

**Implementation:** A `@trace_ai_call` decorator in `src/my_garage/utils/tracing.py` that wraps MCP tool calls and context service methods. Writes async to MongoDB so it never blocks the main request.

Create a **30-day TTL index** on `ai_traces.timestamp` at startup:
```python
db.ai_traces.create_index("timestamp", expireAfterSeconds=2592000)
```

**Files to create:**
- `src/my_garage/utils/tracing.py`

### 3.2 — Evaluation Framework (Golden Dataset)

**Problem:** No way to know if a prompt or context change improves or degrades AI output quality.

**Solution:** A pytest-based eval framework with a golden dataset. This is the most important reliability investment.

**Structure:**
```
tests/
└── eval/
    ├── conftest.py           # loads golden dataset, initializes ContextService
    ├── golden_dataset.json   # 10-15 representative tasks with expected outputs
    ├── test_vehicle_context.py
    ├── test_rag_retrieval.py
    └── test_mcp_tools.py
```

**Golden dataset format:**
```json
[
  {
    "task": "get_vehicle_context",
    "input": {"vehicle_id": 1},
    "expected_keys": ["make", "model", "service_history", "valuation"],
    "expected_rag_docs": ["SERVICE_RECORDS_GUIDE"]
  }
]
```

Eval tests check structure and key presence, not LLM output verbatim (non-deterministic). For MCP tools, tests mock external APIs and verify correct parameters are passed.

**Run evals:**
```bash
pixi run pytest tests/eval/ -v
```

**Files to create:**
- `tests/eval/` directory with initial dataset and test files

---

## Execution Order

| # | Task | Phase | Effort | Dependency |
|---|---|---|---|---|
| 1 | Convert MCP to real MCP SDK server | 0.1 | Medium | None |
| 2 | Register MCP in `.claude/settings.local.json` | 0.1 | Small | #1 |
| 3 | Create ContextService skeleton | 1.1 | Small | None |
| 4 | Wire DRF selectors into ContextService | 1.1 | Medium | #3 |
| 5 | Build knowledge index management command | 1.2 | Medium | None |
| 6 | Wire RAG into ContextService | 1.2 | Small | #4, #5 |
| 7 | Add config validation + available_tools | 1.3 | Small | #1 |
| 8 | Create prompt templates directory + renderer | 2.1 | Small | #4 |
| 9 | Generate BMAD project context file | 2.2 | Small | None |
| 10 | Add Claude Code hooks to settings | 2.3 | Small | None |
| 11 | Implement trace decorator + MongoDB writer | 3.1 | Medium | #1, #4 |
| 12 | Golden dataset + eval test suite | 3.2 | Medium | #4, #5 |

Items 1, 3, 5, 9, 10 can be parallelized (no dependencies between them).

---

## What This Plan Deliberately Does NOT Do

- **No custom Orchestrator class** — BMAD already provides this via slash commands
- **No custom LLM client abstraction** — the real MCP server + Claude's native tool use replaces this
- **No LangSmith / LangChain** — MongoDB traces + pytest evals cover the same ground with zero new dependencies
- **No parallel AI provider abstraction** — optimize for Claude first; multi-provider is a future concern
- **No new databases** — MongoDB Atlas Vector Search is already in-stack

