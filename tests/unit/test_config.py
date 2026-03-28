"""
Tests for MCP config validation (Phase 1.3).
No network, no DB, no env file needed.
"""
from __future__ import annotations

from fastapi_services.mcp.config import Settings


def _settings(**kwargs) -> Settings:
    """Build a Settings instance with env file loading disabled."""
    return Settings.model_construct(**kwargs)


class TestAvailableTools:
    def test_nhtsa_always_available(self):
        s = _settings(marketcheck_api_key=None, google_api_key=None)
        assert "lookup_vehicle_details" in s.available_tools

    def test_google_search_always_available(self):
        s = _settings(marketcheck_api_key=None, google_api_key=None)
        assert "search_google_images" in s.available_tools

    def test_watch_valuation_always_available(self):
        s = _settings(marketcheck_api_key=None, google_api_key=None)
        assert "get_watch_valuation" in s.available_tools

    def test_marketcheck_tools_require_api_key(self):
        s_without = _settings(marketcheck_api_key=None)
        s_with = _settings(marketcheck_api_key="test-key")

        for tool in (
            "search_market_listings",
            "get_sales_stats",
            "get_sales_history_by_vin",
        ):
            assert tool not in s_without.available_tools
            assert tool in s_with.available_tools

    def test_image_generation_requires_google_key(self):
        s_without = _settings(google_api_key=None)
        s_with = _settings(google_api_key="test-google-key")

        assert "generate_vehicle_image" not in s_without.available_tools
        assert "generate_vehicle_image" in s_with.available_tools


class TestUnavailableTools:
    def test_unavailable_is_complement_of_available(self):
        s = _settings(marketcheck_api_key="key", google_api_key="key2")
        all_tools = s.available_tools | s.unavailable_tools
        # Union should cover all 7 tools
        assert len(all_tools) == 7

    def test_no_key_means_all_conditional_tools_unavailable(self):
        s = _settings(marketcheck_api_key=None, google_api_key=None)
        unavailable = s.unavailable_tools
        assert "search_market_listings" in unavailable
        assert "generate_vehicle_image" in unavailable

    def test_full_config_has_no_unavailable_tools(self):
        s = _settings(
            marketcheck_api_key="mc-key",
            google_api_key="g-key",
        )
        assert len(s.unavailable_tools) == 0


class TestLogStartupStatus:
    def test_logs_without_error(self, caplog):
        import logging

        s = _settings(marketcheck_api_key=None, google_api_key=None)
        with caplog.at_level(logging.WARNING, logger="fastapi_services.mcp.config"):
            s.log_startup_status()

        # Should have logged warnings about missing keys
        assert any("MARKETCHECK_API_KEY" in r.message for r in caplog.records)
        assert any("GOOGLE_API_KEY" in r.message for r in caplog.records)

    def test_no_warnings_when_fully_configured(self, caplog):
        import logging

        s = _settings(marketcheck_api_key="key", google_api_key="key2")
        with caplog.at_level(logging.WARNING, logger="fastapi_services.mcp.config"):
            s.log_startup_status()

        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) == 0
