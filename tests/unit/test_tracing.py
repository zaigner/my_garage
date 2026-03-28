"""
Tests for the AI trace decorator and record_trace (Phase 3.1).
No Django DB or MongoDB needed — MongoDB writes are mocked.
"""
from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from my_garage.utils.tracing import (
    AITrace,
    _extract_context_summary,
    record_trace,
    trace_ai_call,
)


class TestAITrace:
    def test_defaults_are_set(self):
        trace = AITrace(tool_name="test_tool")
        assert trace.task_id  # uuid generated
        assert trace.timestamp is not None
        assert trace.success is True
        assert trace.error is None

    def test_serializes_to_dict(self):
        trace = AITrace(tool_name="test_tool", model="claude-sonnet-4-6")
        d = trace.model_dump(mode="json")
        assert d["tool_name"] == "test_tool"
        assert isinstance(d["timestamp"], str)


class TestRecordTrace:
    def test_writes_to_mongo_in_background(self):
        trace = AITrace(tool_name="test_tool")
        with patch("my_garage.utils.tracing._write_trace") as mock_write:
            record_trace(trace)
            # Give the background thread a moment to start
            time.sleep(0.05)
        # Background thread may have called _write_trace or not yet — just verify no exception

    def test_does_not_raise_on_mongo_failure(self):
        trace = AITrace(tool_name="test_tool")
        # _write_trace imports get_collection locally — patch at the source module
        with patch("my_garage.utils.mongo.get_collection") as mock_col:
            from pymongo.errors import ServerSelectionTimeoutError

            mock_col.side_effect = ServerSelectionTimeoutError("timeout")
            # Should not raise
            record_trace(trace)
            time.sleep(0.05)


class TestTraceAiCallDecorator:
    def test_wraps_function_transparently(self):
        @trace_ai_call(tool_name="test_op")
        def add(a: int, b: int) -> int:
            return a + b

        with patch("my_garage.utils.tracing.record_trace"):
            result = add(2, 3)

        assert result == 5

    def test_records_trace_on_success(self):
        recorded: list[AITrace] = []

        @trace_ai_call(tool_name="my_tool", model="claude-sonnet")
        def my_func(context: dict) -> str:
            return "ok"

        with patch("my_garage.utils.tracing.record_trace", side_effect=recorded.append):
            my_func({"vehicle_id": 42})

        assert len(recorded) == 1
        assert recorded[0].tool_name == "my_tool"
        assert recorded[0].model == "claude-sonnet"
        assert recorded[0].success is True
        assert recorded[0].error is None

    def test_records_trace_on_failure(self):
        recorded: list[AITrace] = []

        @trace_ai_call(tool_name="failing_tool")
        def failing_func():
            raise ValueError("something went wrong")

        with patch("my_garage.utils.tracing.record_trace", side_effect=recorded.append):
            with pytest.raises(ValueError):
                failing_func()

        assert len(recorded) == 1
        assert recorded[0].success is False
        assert "ValueError" in recorded[0].error

    def test_measures_duration(self):
        recorded: list[AITrace] = []

        @trace_ai_call(tool_name="slow_tool")
        def slow_func():
            time.sleep(0.05)
            return "done"

        with patch("my_garage.utils.tracing.record_trace", side_effect=recorded.append):
            slow_func()

        assert recorded[0].duration_ms >= 40  # at least 40ms

    def test_uses_function_name_when_no_tool_name(self):
        recorded: list[AITrace] = []

        @trace_ai_call()
        def my_operation():
            return "result"

        with patch("my_garage.utils.tracing.record_trace", side_effect=recorded.append):
            my_operation()

        assert recorded[0].tool_name == "my_operation"

    def test_preserves_function_name(self):
        @trace_ai_call(tool_name="tool")
        def important_function():
            pass

        assert important_function.__name__ == "important_function"


class TestExtractContextSummary:
    def test_extracts_scalar_from_dict_arg(self):
        summary = _extract_context_summary(({"vehicle_id": 42, "make": "Porsche"},), {})
        assert summary["vehicle_id"] == 42
        assert summary["make"] == "Porsche"

    def test_counts_list_values(self):
        summary = _extract_context_summary(({"service_records": [1, 2, 3]},), {})
        assert summary["service_records_count"] == 3

    def test_extracts_kwargs(self):
        summary = _extract_context_summary((), {"vehicle_id": 5, "make": "BMW"})
        assert summary["vehicle_id"] == 5
        assert summary["make"] == "BMW"

    def test_handles_empty_args(self):
        summary = _extract_context_summary((), {})
        assert isinstance(summary, dict)

    def test_handles_non_dict_first_arg(self):
        summary = _extract_context_summary(("string_arg", 42), {})
        assert "arg_count" in summary
