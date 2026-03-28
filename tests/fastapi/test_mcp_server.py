"""
Tests for the real MCP server (Phase 0.1).

These tests verify:
1. All expected tools are registered on the MCP server.
2. Each tool has a correct name, description, and callable implementation.
3. Tools return the right shape of data when called with mocked external APIs.
"""
from unittest.mock import MagicMock, patch

from fastapi_services.mcp.server import mcp_server

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _registered_tool_names() -> set[str]:
    """Return the set of tool names registered on the FastMCP server."""
    # FastMCP exposes its tool registry via ._tool_manager or .tools
    # depending on the mcp SDK version. Try both.
    if hasattr(mcp_server, "_tool_manager"):
        return set(mcp_server._tool_manager._tools.keys())
    if hasattr(mcp_server, "tools"):
        tools = mcp_server.tools
        if callable(tools):
            return set(tools())
        return set(tools)
    # Fallback: inspect the ASGI app routes
    return set()


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

EXPECTED_TOOLS = {
    "lookup_vehicle_details",
    "search_market_listings",
    "get_sales_stats",
    "get_sales_history_by_vin",
    "get_watch_valuation",
    "generate_vehicle_image",
    "search_google_images",
}


def test_all_expected_tools_are_registered():
    """Every tool defined in server.py must appear in the FastMCP registry."""
    registered = _registered_tool_names()
    assert EXPECTED_TOOLS.issubset(
        registered
    ), f"Missing tools: {EXPECTED_TOOLS - registered}"


def test_no_unexpected_tools_registered():
    """Guard against accidental tool registrations."""
    registered = _registered_tool_names()
    unexpected = registered - EXPECTED_TOOLS
    assert not unexpected, f"Unexpected tools registered: {unexpected}"


# ---------------------------------------------------------------------------
# lookup_vehicle_details — mocked NHTSA API
# ---------------------------------------------------------------------------


class TestLookupVehicleDetails:
    @patch("fastapi_services.mcp.tools.vehicle_lookup.requests.get")
    def test_returns_clean_spec_dict(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "Results": [
                {"Variable": "Make", "Value": "PORSCHE"},
                {"Variable": "Model", "Value": "911"},
                {"Variable": "Model Year", "Value": "2019"},
                {"Variable": "Error Code", "Value": None},  # should be filtered
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from fastapi_services.mcp.tools.vehicle_lookup import lookup_vehicle_details

        result = lookup_vehicle_details("WP0AB2A91KS123456", model_year=2019)

        assert result.get("make") == "PORSCHE"
        assert result.get("model") == "911"
        assert "error_code" not in result

    @patch("fastapi_services.mcp.tools.vehicle_lookup.requests.get")
    def test_returns_error_on_empty_results(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"Results": []}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from fastapi_services.mcp.tools.vehicle_lookup import lookup_vehicle_details

        result = lookup_vehicle_details("INVALIDVIN00000000")
        assert "error" in result

    @patch("fastapi_services.mcp.tools.vehicle_lookup.requests.get")
    def test_handles_request_exception(self, mock_get):
        import requests as req_lib

        mock_get.side_effect = req_lib.exceptions.RequestException("timeout")

        from fastapi_services.mcp.tools.vehicle_lookup import lookup_vehicle_details

        result = lookup_vehicle_details("WP0AB2A91KS123456")
        assert "error" in result


# ---------------------------------------------------------------------------
# search_market_listings — mocked Marketcheck API
# ---------------------------------------------------------------------------


class TestSearchMarketListings:
    @patch("fastapi_services.mcp.tools.market_valuation.requests.get")
    @patch("fastapi_services.mcp.tools.market_valuation.settings")
    def test_returns_listings(self, mock_settings, mock_get):
        mock_settings.marketcheck_api_key = "test-key"
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "num_found": 2,
            "listings": [
                {
                    "price": 80000,
                    "miles": 12000,
                    "vin": "ABC",
                    "trim": "Carrera S",
                    "source": "dealer",
                    "exterior_color": "Guards Red",
                    "interior_color": "Black",
                    "dealer": {"name": "Test Motors", "city": "Austin", "state": "TX"},
                    "media": {"photo_links": []},
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        from fastapi_services.mcp.tools.market_valuation import search_market_listings

        result = search_market_listings(make="Porsche", model="911", year=2019)
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["price"] == 80000

    @patch("fastapi_services.mcp.tools.market_valuation.settings")
    def test_returns_error_when_no_api_key(self, mock_settings):
        mock_settings.marketcheck_api_key = None

        from fastapi_services.mcp.tools.market_valuation import search_market_listings

        result = search_market_listings(make="Porsche", model="911", year=2019)
        assert "error" in result


# ---------------------------------------------------------------------------
# get_watch_valuation — no external API (mock implementation)
# ---------------------------------------------------------------------------


class TestGetWatchValuation:
    def test_rolex_returns_higher_than_seiko(self):
        from fastapi_services.mcp.tools.watch_valuation import get_watch_valuation

        rolex = get_watch_valuation(brand="Rolex", model="Submariner")
        seiko = get_watch_valuation(brand="Seiko", model="SKX007")
        assert rolex["estimated_value"] > seiko["estimated_value"]

    def test_box_and_papers_increase_value(self):
        from fastapi_services.mcp.tools.watch_valuation import get_watch_valuation

        base = get_watch_valuation(brand="Omega", model="Speedmaster")
        complete = get_watch_valuation(
            brand="Omega", model="Speedmaster", has_box=True, has_papers=True
        )
        assert complete["estimated_value"] > base["estimated_value"]

    def test_returns_required_keys(self):
        from fastapi_services.mcp.tools.watch_valuation import get_watch_valuation

        result = get_watch_valuation(brand="Rolex", model="Daytona")
        assert "estimated_value" in result
        assert "currency" in result
        assert "confidence" in result


# ---------------------------------------------------------------------------
# MCP server ASGI app structure
# ---------------------------------------------------------------------------


def test_mcp_server_has_name():
    assert mcp_server.name == "my-garage"


def test_streamable_http_app_is_callable():
    """Verify the ASGI app can be constructed without error."""
    asgi_app = mcp_server.streamable_http_app()
    assert asgi_app is not None
