"""
AI call tracing — structured logging for every LLM/tool interaction.

Traces are written asynchronously to MongoDB `ai_traces` collection
with a 30-day TTL index so they never block the main request.

Usage:
    from my_garage.utils.tracing import trace_ai_call

    @trace_ai_call(tool_name="vehicle_valuation")
    def my_ai_function(vehicle_context: dict) -> str:
        ...

    # Or call manually:
    from my_garage.utils.tracing import record_trace, AITrace

    record_trace(AITrace(
        tool_name="search_market_listings",
        context_summary={"vehicle_id": 42, "make": "Porsche"},
        prompt_template="vehicle_valuation.j2",
        model="claude-sonnet-4-6",
        input_tokens=800,
        output_tokens=200,
        duration_ms=1450,
        success=True,
    ))
"""

from __future__ import annotations

import functools
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, Field
from pymongo.errors import ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

_MONGO_COLLECTION = "ai_traces"
_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
_ttl_index_ensured = False
_ttl_lock = threading.Lock()


class AITrace(BaseModel):
    """Schema for a single AI interaction trace."""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    tool_name: str
    context_summary: dict[str, Any] = Field(default_factory=dict)
    prompt_template: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0
    success: bool = True
    error: str | None = None


def record_trace(trace: AITrace) -> None:
    """
    Write a trace to MongoDB in a background thread.
    Never raises — tracing failures are logged and swallowed so they
    don't impact the main request.
    """
    thread = threading.Thread(
        target=_write_trace,
        args=(trace.model_dump(mode="json"),),
        daemon=True,
    )
    thread.start()


def _write_trace(trace_dict: dict) -> None:
    """Background worker that writes a trace document to MongoDB."""
    try:
        from my_garage.utils.mongo import get_collection

        collection = get_collection(_MONGO_COLLECTION)
        _ensure_ttl_index(collection)
        collection.insert_one(trace_dict)
    except ServerSelectionTimeoutError:
        logger.debug("MongoDB unavailable — trace not written")
    except Exception as e:
        logger.debug(f"Trace write failed (non-critical): {e}")


def _ensure_ttl_index(collection) -> None:
    """Create the 30-day TTL index on `timestamp` if it doesn't exist yet."""
    global _ttl_index_ensured

    if _ttl_index_ensured:
        return

    with _ttl_lock:
        if _ttl_index_ensured:
            return
        try:
            collection.create_index(
                "timestamp",
                expireAfterSeconds=_TTL_SECONDS,
                name="ai_traces_ttl",
                background=True,
            )
            _ttl_index_ensured = True
        except Exception:
            # Index may already exist with different options — not critical
            _ttl_index_ensured = True


def trace_ai_call(
    tool_name: str = "",
    prompt_template: str = "",
    model: str = "",
) -> Callable:
    """
    Decorator that wraps an AI-calling function and records a trace.

    The wrapped function may return any value. If it raises, the trace
    records `success=False` and the exception is re-raised.

    Context summary is derived from the first positional argument if it's
    a dict, otherwise from the function's kwargs.

    Args:
        tool_name: Name of the MCP tool or AI operation.
        prompt_template: Jinja2 template filename used (if any).
        model: Model name (e.g. "claude-sonnet-4-6").

    Example:
        @trace_ai_call(
            tool_name="vehicle_valuation", prompt_template="vehicle_valuation.j2"
        )
        def run_valuation(vehicle_context: dict) -> str:
            ...
    """

    def decorator(func: Callable) -> Callable:
        resolved_tool_name = tool_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build a lightweight context summary from args/kwargs
            context_summary = _extract_context_summary(args, kwargs)

            start_ms = time.monotonic()
            error_msg: str | None = None
            success = True

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = f"{type(e).__name__}: {e}"
                raise
            finally:
                duration_ms = int((time.monotonic() - start_ms) * 1000)
                trace = AITrace(
                    tool_name=resolved_tool_name,
                    context_summary=context_summary,
                    prompt_template=prompt_template,
                    model=model,
                    duration_ms=duration_ms,
                    success=success,
                    error=error_msg,
                )
                record_trace(trace)

        return wrapper

    return decorator


def _extract_context_summary(args: tuple, kwargs: dict) -> dict:
    """
    Build a lightweight context summary from function arguments.
    Extracts scalar values and key counts from dicts/lists.
    """
    summary: dict[str, Any] = {}

    # First positional arg is often the main context dict
    if args and isinstance(args[0], dict):
        for k, v in args[0].items():
            if isinstance(v, (str, int, float, bool)) and not isinstance(v, bool):
                summary[k] = v
            elif isinstance(v, (list, dict)):
                summary[f"{k}_count"] = len(v)
    elif args:
        summary["arg_count"] = len(args)

    # Include simple kwargs
    for k, v in kwargs.items():
        if isinstance(v, (str, int, float)):
            summary[k] = v

    return summary
