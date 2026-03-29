"""
BaseCollectionServices — the interface every service provider must satisfy.

Capability guards (supports_*) are plain methods that return False by default
so providers only need to override what they actually implement.  Views and
Celery tasks MUST check supports_*() before calling the corresponding run_*()
method.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from my_garage.models import DynamicCollectionItem


class BaseCollectionServices:
    """
    Abstract-style base class for collection service providers.

    Each provider wraps one or more external API integrations (MCP tools,
    third-party APIs, AI generators) and exposes them through a uniform
    interface so that views, tasks, and templates never branch on collection
    type directly.

    Subclass and override only the methods your provider supports.
    """

    # ------------------------------------------------------------------
    # Capability guards
    # ------------------------------------------------------------------

    def supports_valuation_refresh(self) -> bool:
        """True if this provider can fetch a live market valuation."""
        return False

    def supports_enrichment(self) -> bool:
        """True if this provider can auto-populate fields from an external ID
        (e.g. VIN decode for vehicles, reference-number lookup for watches)."""
        return False

    def supports_photo_fetch(self) -> bool:
        """True if this provider can source a stock/press photo automatically."""
        return False

    def get_enrichment_trigger_field(self) -> str | None:
        """
        Name of the custom_fields key whose presence enables the enrichment
        button in the UI.  Returns None if enrichment is not supported.

        Example: 'vin' for vehicles, None for default.
        """
        return None

    # ------------------------------------------------------------------
    # Service operations
    # ------------------------------------------------------------------

    def run_valuation(self, item: DynamicCollectionItem) -> Decimal | None:
        """
        Fetch an up-to-date market valuation for *item*, persist it to
        GenericValuationHistory, update item.current_market_value, and return
        the new value.

        Raises NotImplementedError if supports_valuation_refresh() is False.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support valuation refresh."
        )

    def run_enrichment(self, item: DynamicCollectionItem) -> dict[str, Any]:
        """
        Enrich *item* by querying an external data source using the trigger
        field value (e.g. VIN).  Updates item.custom_fields in-place and saves.

        Returns the raw data dict from the external source.
        Raises NotImplementedError if supports_enrichment() is False.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support enrichment."
        )

    def run_photo_fetch(
        self, item: DynamicCollectionItem, force_refresh: bool = False
    ) -> bool:
        """
        Attempt to source and save a photo for *item*.

        Returns True on success, False if all strategies are exhausted.
        Raises NotImplementedError if supports_photo_fetch() is False.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support photo fetch."
        )

    # ------------------------------------------------------------------
    # Template context helpers
    # ------------------------------------------------------------------

    def get_detail_context(self, item: DynamicCollectionItem) -> dict[str, Any]:
        """
        Return extra context dict merged into the collection_item_detail view
        context.  Used to toggle provider-specific UI sections (buttons,
        panels, winder views) without branching on collection type in templates.

        Override in subclasses to expose provider-specific context keys.
        """
        return {}
