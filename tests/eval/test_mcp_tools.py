"""
Eval tests: MCP tool correctness (Phase 3.2).
Tests tool output shape against the golden dataset.
External APIs are always mocked.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi_services.mcp.config import Settings


class TestMcpToolsGoldenDataset:
    def test_vehicle_lookup_structure(self, golden_dataset):
        """VIN lookup output has expected keys and excludes metadata."""
        case = next(
            c for c in golden_dataset if c["id"] == "mcp_vehicle_lookup_structure"
        )

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"Results": case["mock_response"]["Results"]}
        mock_resp.raise_for_status = MagicMock()

        with patch(
            "fastapi_services.mcp.tools.vehicle_lookup.requests.get",
            return_value=mock_resp,
        ):
            from fastapi_services.mcp.tools.vehicle_lookup import lookup_vehicle_details

            result = lookup_vehicle_details("WP0AB2A91KS123456", model_year=2019)

        for key in case["expected_keys"]:
            assert key in result, f"Missing key: {key}"
        for key in case["must_not_contain"]:
            assert key not in result, f"Should not contain: {key}"

    def test_watch_valuation_structure(self, golden_dataset):
        """Watch valuation output has expected keys and correct currency."""
        case = next(
            c for c in golden_dataset if c["id"] == "mcp_watch_valuation_structure"
        )

        from fastapi_services.mcp.tools.watch_valuation import get_watch_valuation

        result = get_watch_valuation(**case["inputs"])

        for key in case["expected_keys"]:
            assert key in result, f"Missing key: {key}"
        assert result["currency"] == case["expected_currency"]

    def test_watch_valuation_estimated_value_is_positive(self):
        from fastapi_services.mcp.tools.watch_valuation import get_watch_valuation

        result = get_watch_valuation(brand="Rolex", model="Submariner")
        assert result["estimated_value"] > 0

    def test_market_listings_error_on_missing_key(self):
        from fastapi_services.mcp.tools.market_valuation import search_market_listings

        with patch("fastapi_services.mcp.tools.market_valuation.settings") as ms:
            ms.marketcheck_api_key = None
            result = search_market_listings(make="Porsche", model="911", year=2019)
        assert "error" in result

    def test_sales_stats_error_on_missing_key(self):
        from fastapi_services.mcp.tools.sales_stats import get_sales_stats

        with patch("fastapi_services.mcp.tools.sales_stats.settings") as ms:
            ms.marketcheck_api_key = None
            result = get_sales_stats(year=2019, make="Porsche", model="911")
        assert "error" in result


class TestConfigAvailableToolsGoldenDataset:
    def test_no_keys_scenario(self, golden_dataset):
        case = next(
            c for c in golden_dataset if c["id"] == "config_available_tools_no_keys"
        )
        s = Settings.model_construct(marketcheck_api_key=None, google_api_key=None)

        for tool in case["expected_available"]:
            assert tool in s.available_tools, f"Expected available: {tool}"
        for tool in case["expected_unavailable"]:
            assert tool not in s.available_tools, f"Should not be available: {tool}"
            assert tool in s.unavailable_tools, f"Expected unavailable: {tool}"
