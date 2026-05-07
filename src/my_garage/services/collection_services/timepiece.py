"""
TimepieceCollectionServices — provider for the Horology Salon system collection.

Wraps the watch_valuation MCP tool and exposes the ChronoVault winder context.
Photo fetch is a simple Google Images search using brand + reference number.

External dependencies (all via the FastAPI MCP relay):
  - watch_valuation  → Watch market valuation (get_watch_valuation)
  - search_google_images → Stock photo sourcing
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from .base import BaseCollectionServices

if TYPE_CHECKING:
    from my_garage.models import DynamicCollectionItem

logger = logging.getLogger(__name__)

_MCP_EXECUTE_URL = f"{settings.FASTAPI_BASE_URL}/mcp/execute"


def _cf(item: DynamicCollectionItem, key: str, default: Any = "") -> Any:
    """Convenience accessor for custom_fields."""
    return item.custom_fields.get(key, default)


class TimepieceCollectionServices(BaseCollectionServices):
    """
    Service provider for Horology Salon collection items.

    Reads watch identity data from item.custom_fields using the key names
    defined in docs/schemas/horology_field_schema.json.

    Note: 'model' is stored as 'watch_model' in custom_fields to avoid
    collision with Python/ORM naming conventions.
    """

    def supports_valuation_refresh(self) -> bool:
        return True

    def supports_photo_fetch(self) -> bool:
        return True

    # Timepieces don't have an external enrichment source (WatchCharts API is
    # planned but not yet integrated).  Returns False until that lands.
    def supports_enrichment(self) -> bool:
        return False

    # ------------------------------------------------------------------
    # Valuation
    # ------------------------------------------------------------------

    @transaction.atomic
    def run_valuation(self, item: DynamicCollectionItem) -> Decimal | None:
        """
        Call the get_watch_valuation MCP tool using the watch's identity and
        condition data, persist a GenericValuationHistory record, and update
        item.current_market_value.
        """
        from my_garage.models import GenericValuationHistory

        arguments = {
            "brand": _cf(item, "brand"),
            "model": _cf(item, "watch_model"),
            "reference_number": _cf(item, "reference_number"),
            "condition_grade": _cf(item, "condition_grade"),
            "has_box": bool(_cf(item, "has_box", False)),
            "has_papers": bool(_cf(item, "has_papers", False)),
        }
        year = _cf(item, "year")
        if year:
            arguments["year"] = year

        payload = {"tool_name": "get_watch_valuation", "arguments": arguments}

        try:
            logger.info("Requesting watch valuation for item %s", item)
            response = requests.post(_MCP_EXECUTE_URL, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()

            estimated_value = data.get("estimated_value")
            if not estimated_value:
                logger.warning(
                    "Watch valuation returned no estimated_value for item %s", item
                )
                return item.current_market_value

            new_value = Decimal(str(estimated_value))

            item.current_market_value = new_value
            item.save(update_fields=["current_market_value"])

            GenericValuationHistory.objects.create(
                item=item,
                value=new_value,
                raw_data=data,
            )

            return new_value

        except requests.RequestException as exc:
            logger.error("Watch valuation request failed for item %s: %s", item, exc)
            raise

    # ------------------------------------------------------------------
    # Photo fetch
    # ------------------------------------------------------------------

    def run_photo_fetch(
        self, item: DynamicCollectionItem, force_refresh: bool = False
    ) -> bool:
        """
        Search Google Images using brand + reference number for a press/product
        photo of the watch.
        """
        if item.photo and not force_refresh:
            return True

        brand = _cf(item, "brand")
        reference = _cf(item, "reference_number")
        watch_model = _cf(item, "watch_model")

        query = f"{brand} {watch_model} {reference} official product photo"
        payload = {"tool_name": "search_google_images", "arguments": {"query": query}}

        try:
            response = requests.post(_MCP_EXECUTE_URL, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            candidates: list[str] = data.get("images", [])

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"  # noqa: E501
            }
            for url in candidates[:10]:
                try:
                    img = requests.get(url, headers=headers, timeout=10)
                    img.raise_for_status()
                    if len(img.content) < 30 * 1024:
                        continue
                    fname = (
                        f"{brand}_{reference}_photo.jpg".lower()
                        .replace(" ", "_")
                        .replace("/", "_")
                    )
                    item.photo.save(fname, ContentFile(img.content), save=True)
                    return True
                except Exception as exc:
                    logger.warning("Watch photo candidate %s failed: %s", url, exc)

        except Exception as exc:
            logger.warning("Watch photo search failed: %s", exc)

        return False

    # ------------------------------------------------------------------
    # Template context
    # ------------------------------------------------------------------

    def get_detail_context(self, item: DynamicCollectionItem) -> dict[str, Any]:
        """
        Expose the ChronoVault winder context.  The winder view renders up to
        8 timepieces in virtual winder slots; we expose all Horology Salon items
        owned by this user for the winder sidebar.
        """
        from my_garage.models import DynamicCollectionItem as DCItem

        winder_items = DCItem.objects.filter(
            collection_type=item.collection_type,
            owner=item.owner,
        ).order_by("name")[:8]

        return {
            "show_valuation_button": True,
            "show_winder_link": True,
            "show_photo_refresh_button": True,
            "winder_items": winder_items,
            "has_box": bool(_cf(item, "has_box", False)),
            "has_papers": bool(_cf(item, "has_papers", False)),
            "valuation_history": item.valuation_history.all()[:5],
        }
