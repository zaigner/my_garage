"""
MCP service configuration with startup validation.

Validates API keys at startup and exposes which tools are available
so the MCP server can surface accurate capability information.
"""
import logging
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Marketcheck — vehicle market data
    marketcheck_api_key: Optional[str] = None

    # Google Gemini — image generation + embedding
    google_api_key: Optional[str] = None

    # WatchCharts — timepiece valuations (future)
    watchcharts_api_key: Optional[str] = None

    # ------------------------------------------------------------------
    # Tool availability
    # ------------------------------------------------------------------

    @property
    def available_tools(self) -> set[str]:
        """
        Returns the set of tool names that have their required API keys
        configured. Claude should prefer calling only these tools.

        Tools that require no API key are always available.
        """
        always_available = {
            "lookup_vehicle_details",  # NHTSA — free, no key
            "search_google_images",  # Basic scraping — no key
            "get_watch_valuation",  # Mock — no key
        }

        conditional = {
            "search_market_listings": self.marketcheck_api_key,
            "get_sales_stats": self.marketcheck_api_key,
            "get_sales_history_by_vin": self.marketcheck_api_key,
            "generate_vehicle_image": self.google_api_key,
        }

        return always_available | {tool for tool, key in conditional.items() if key}

    @property
    def unavailable_tools(self) -> set[str]:
        """Tools that cannot function due to missing API keys."""
        all_tools = {
            "lookup_vehicle_details",
            "search_market_listings",
            "get_sales_stats",
            "get_sales_history_by_vin",
            "get_watch_valuation",
            "generate_vehicle_image",
            "search_google_images",
        }
        return all_tools - self.available_tools

    def log_startup_status(self) -> None:
        """
        Log a summary of which tools are available at service startup.
        Call this from the FastAPI lifespan event.
        """
        available = self.available_tools
        unavailable = self.unavailable_tools

        logger.info(
            f"MCP Tools available ({len(available)}): " + ", ".join(sorted(available))
        )

        if unavailable:
            logger.warning(
                f"MCP Tools unavailable ({len(unavailable)}) — missing API keys: "
                + ", ".join(sorted(unavailable))
            )

        # Specific key warnings
        if not self.marketcheck_api_key:
            logger.warning(
                "MARKETCHECK_API_KEY not set — "
                "search_market_listings, get_sales_stats, get_sales_history_by_vin disabled."
            )
        if not self.google_api_key:
            logger.warning(
                "GOOGLE_API_KEY not set — "
                "generate_vehicle_image disabled. RAG embeddings also disabled."
            )


settings = Settings()
