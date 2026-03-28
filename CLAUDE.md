# CLAUDE.md — my_garage

This file provides project-specific guidance for Claude Code when working in the `my_garage` project.

## Project Overview

`my_garage` is a Django 5.2 LTS + FastAPI personal asset management platform for vehicles, timepieces, and dynamic collections. See `docs/IMPLEMENTATION_PLAN.md` for the full AI harness architecture.

## Key Commands

```bash
pixi run server        # Django dev server
pixi run fastapi       # FastAPI service (port 8001, MCP server lives here)
pixi run worker        # Celery worker
pixi run pytest        # Run all tests
pixi run manage <cmd>  # Django management commands
pixi run mongo         # Start local MongoDB
pixi run manage build_knowledge_index  # Rebuild RAG knowledge index
pixi run refresh-context               # Refresh BMAD project context
```

## Architecture Quick Reference

- Django app: `src/my_garage/`
- FastAPI + MCP server: `src/fastapi_services/` (port 8001, `/mcp-sdk` endpoint)
- Context service: `src/my_garage/services/context_service.py`
- Prompt templates: `src/my_garage/prompts/*.j2`
- AI tracing: `src/my_garage/utils/tracing.py`
- Tests: `tests/` (unit + eval + fastapi)

## Development Conventions

- Python 3.12, Pydantic v2 (`model_config = SettingsConfigDict(...)`, not `class Config`)
- All new features need unit tests alongside them
- Run `pixi run pytest` before declaring any task complete
- PYTHONPATH must include `src/` — use `pixi run` tasks, not bare `python`

---

## Session Retrospective Protocol

**At the end of every working session, run a retrospective and update memory.**

This is not optional — it is how agent interactions improve over time.

### When to run

- When the user signals the session is wrapping up
- When the user explicitly asks for a retrospective
- After any session where something broke, required multiple fix attempts, or where an assumption turned out to be wrong

### What to capture

A good retrospective covers three things:

1. **What went well** — approaches that worked, decisions that held up, patterns worth repeating
2. **What went wrong** — bugs introduced, wrong assumptions, wasted iterations, things that required multiple attempts
3. **What to change** — concrete rule changes for future sessions

### Output: two artifacts

**1. Session log** — Written to `memory/retros/YYYY-MM-DD.md` (use today's date).

Format:
```markdown
# Retrospective — YYYY-MM-DD
**Session focus:** <one line summary of what was worked on>

## Went Well
- <bullet per item>

## Went Wrong
- <bullet per item — include root cause, not just symptom>

## Rule Changes
- <concrete, actionable rules — same format as feedback memories>
```

**2. Memory updates** — For every "went wrong" item that represents a *repeatable mistake*, save or update a memory file:
- New pattern → new `feedback_<topic>.md` file
- Updated understanding of project facts → update `project_<topic>.md`
- Add/update the pointer in `MEMORY.md`

### What NOT to log

- Task lists or implementation details (those are in git)
- Things that only apply to this specific session and won't recur
- Positive outcomes that are obvious or expected

### Memory file location

`/home/zaigner77/.claude/projects/-home-zaigner77-projects-zaigner/memory/`

Session logs: `.../memory/retros/YYYY-MM-DD.md`
