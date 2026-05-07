"""
VehicleCollectionServices — provider for the Automobiles system collection.

Wraps the same external integrations as the legacy api/services.py but
operates on DynamicCollectionItem.custom_fields instead of the Vehicle ORM
model.  The old Vehicle-specific code in api/services.py is untouched (Phase 1
is non-breaking); this provider is the forward-looking replacement.

External dependencies (all via the FastAPI MCP relay):
  - NHTSA vPIC  → VIN decode  (lookup_vehicle_details)
  - Marketcheck  → Market valuation (search_market_listings)
  - Google Images → Stock photo (search_google_images)
  - Google Gemini → AI image generation (generate_vehicle_image)
"""

from __future__ import annotations

import base64
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


def _build_market_search_args(item: DynamicCollectionItem) -> dict[str, Any]:  # noqa: C901
    """
    Build the search argument dict expected by the search_market_listings MCP
    tool, reading all values from item.custom_fields.

    Mirrors _build_market_search_arguments(vehicle) in api/services.py.
    """
    args: dict[str, Any] = {
        "make": _cf(item, "make"),
        "model": _cf(item, "model"),
        "year": _cf(item, "year"),
        "trim": _cf(item, "trim"),
    }

    mileage = _cf(item, "mileage", 0)
    if mileage:
        args["mileage"] = mileage

    if _cf(item, "exterior_color"):
        args["exterior_color"] = _cf(item, "exterior_color")

    if _cf(item, "transmission"):
        args["transmission"] = _cf(item, "transmission")

    specs = _cf(item, "specs", {})
    if specs:
        spec_keys = [
            "engine",
            "drivetrain",
            "drive_type",
            "fuel_type",
            "body_style",
            "interior_color",
        ]
        for key in spec_keys:
            val = (
                specs.get(key)
                or specs.get(key.replace("_", " ").title())
                or specs.get(key.replace("_", " "))
            )
            if val:
                args[key] = val

    features = _cf(item, "features", {})
    if features:
        if isinstance(features, dict):
            keywords = [k for k, v in features.items() if v]
            if keywords:
                args["keywords"] = keywords
        elif isinstance(features, list):
            args["keywords"] = features

    return args


class VehicleCollectionServices(BaseCollectionServices):
    """
    Service provider for Automobiles collection items.

    Reads vehicle identity and spec data from item.custom_fields using the
    key names defined in docs/schemas/automobiles_field_schema.json.
    """

    def supports_valuation_refresh(self) -> bool:
        return True

    def supports_enrichment(self) -> bool:
        return True

    def supports_photo_fetch(self) -> bool:
        return True

    def get_enrichment_trigger_field(self) -> str:
        return "vin"

    # ------------------------------------------------------------------
    # Valuation
    # ------------------------------------------------------------------

    @transaction.atomic
    def run_valuation(self, item: DynamicCollectionItem) -> Decimal | None:
        """
        Fetch comparable market listings, calculate median price, persist a
        GenericValuationHistory record, and update item.current_market_value.
        """
        from my_garage.models import GenericValuationHistory

        search_args = _build_market_search_args(item)
        payload = {"tool_name": "search_market_listings", "arguments": search_args}

        try:
            logger.info(
                "Requesting vehicle valuation for item %s with args: %s",
                item,
                search_args,
            )
            response = requests.post(_MCP_EXECUTE_URL, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()

            listings = data.get("results", [])
            if not listings:
                logger.warning("No listings found for item %s (valuation)", item)
                return item.current_market_value

            prices = [
                Decimal(str(listing["price"]))
                for listing in listings
                if listing.get("price")
            ]
            if not prices:
                return item.current_market_value

            median_price = sorted(prices)[len(prices) // 2]

            item.current_market_value = median_price
            item.save(update_fields=["current_market_value"])

            GenericValuationHistory.objects.create(
                item=item,
                value=median_price,
                raw_data=data,
            )

            return median_price

        except requests.RequestException as exc:
            logger.error("Vehicle valuation request failed: %s", exc)
            raise

    # ------------------------------------------------------------------
    # VIN Enrichment
    # ------------------------------------------------------------------

    def run_enrichment(self, item: DynamicCollectionItem) -> dict[str, Any]:
        """
        Decode the VIN stored in custom_fields['vin'] via the NHTSA MCP tool.
        Updates custom_fields['specs'], and core identity fields (make/model/year)
        if the API returns them.  Triggers photo fetch if no photo exists.
        """
        vin = _cf(item, "vin")
        if not vin:
            logger.warning("run_enrichment called on item %s with no VIN", item)
            return {}

        payload = {
            "tool_name": "lookup_vehicle_details",
            "arguments": {"vin": vin, "model_year": _cf(item, "year")},
        }

        try:
            response = requests.post(_MCP_EXECUTE_URL, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                return {}

            # Merge specs and update identity fields
            item.custom_fields["specs"] = data
            if data.get("make"):
                item.custom_fields["make"] = data["make"]
            if data.get("model"):
                item.custom_fields["model"] = data["model"]
            if data.get("model_year"):
                item.custom_fields["year"] = data["model_year"]

            item.save(update_fields=["custom_fields"])

            if not item.photo:
                self.run_photo_fetch(item)

            return data

        except requests.RequestException as exc:
            logger.error("VIN enrichment request failed for item %s: %s", item, exc)
            return {}

    # ------------------------------------------------------------------
    # Photo fetch
    # ------------------------------------------------------------------

    def run_photo_fetch(
        self, item: DynamicCollectionItem, force_refresh: bool = False
    ) -> bool:
        """
        4-stage stock photo sourcing:
          1. Market listings (specific with trim/color)
          2. Market listings (relaxed — make/model/year only)
          3. HQ press sites via Google Images
          4. AI image generation (Gemini, last resort)
        """
        if item.photo and not force_refresh:
            return True

        base_args = _build_market_search_args(item)

        args_specific = base_args.copy()
        args_specific.pop("mileage", None)

        args_relaxed: dict[str, Any] = {
            "make": _cf(item, "make"),
            "model": _cf(item, "model"),
            "year": _cf(item, "year"),
        }
        if _cf(item, "trim"):
            args_relaxed["trim"] = _cf(item, "trim")

        strategies = [
            ("market_specific", args_specific, "search_market_listings"),
            ("market_relaxed", args_relaxed, "search_market_listings"),
        ]
        for label, args, tool in strategies:
            if self._search_and_save(item, args, label, tool):
                return True

        # HQ press sites
        hq_query = (
            f"{_cf(item, 'year')} {_cf(item, 'make')} {_cf(item, 'model')} "
            f"{_cf(item, 'trim')} site:netcarshow.com OR site:wsupercars.com"
        )
        if _cf(item, "exterior_color"):
            hq_query += f" {_cf(item, 'exterior_color')}"
        if self._search_and_save(
            item, {"query": hq_query}, "hq_press", "search_google_images"
        ):
            return True

        # Google broad fallback
        query = (
            f"{_cf(item, 'year')} {_cf(item, 'make')} {_cf(item, 'model')} "
            f"{_cf(item, 'trim')} stock photo 4k wallpaper imagesize:large"
        )
        if _cf(item, "exterior_color"):
            query += f" {_cf(item, 'exterior_color')}"
        if self._search_and_save(
            item, {"query": query}, "google", "search_google_images"
        ):
            return True

        # AI generation
        return self._generate_and_save(item)

    def _search_and_save(
        self, item: DynamicCollectionItem, args: dict, suffix: str, tool: str
    ) -> bool:
        payload = {"tool_name": tool, "arguments": args}
        try:
            response = requests.post(_MCP_EXECUTE_URL, json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()

            candidates: list[str] = []
            if tool == "search_market_listings":
                for listing in data.get("results", []):
                    url = (
                        listing.get("image_url")
                        or listing.get("photo")
                        or listing.get("primary_photo_url")
                    )
                    if url and isinstance(url, str) and url.startswith("http"):
                        candidates.append(url)
            elif tool == "search_google_images":
                candidates = data.get("images", [])

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"  # noqa: E501
            }
            for url in candidates[:10]:
                try:
                    img = requests.get(url, headers=headers, timeout=10)
                    img.raise_for_status()
                    if len(img.content) < 50 * 1024:
                        continue
                    make = _cf(item, "make", "vehicle")
                    model = _cf(item, "model", "model")
                    year = _cf(item, "year", "")
                    fname = f"{make}_{model}_{year}_{suffix}.jpg".lower().replace(
                        " ", "_"
                    )
                    item.photo.save(fname, ContentFile(img.content), save=True)
                    return True
                except Exception as exc:
                    logger.warning("Photo candidate %s failed: %s", url, exc)
        except Exception as exc:
            logger.warning("Photo search failed (%s): %s", tool, exc)
        return False

    def _generate_and_save(self, item: DynamicCollectionItem) -> bool:
        prompt = (
            f"A high quality photorealistic image of a {_cf(item, 'year')} "
            f"{_cf(item, 'make')} {_cf(item, 'model')}"
        )
        if _cf(item, "trim"):
            prompt += f" {_cf(item, 'trim')}"
        if _cf(item, "exterior_color"):
            prompt += f" in {_cf(item, 'exterior_color')} color"
        prompt += ", parked in a modern garage or showroom, 4k, highly detailed"

        payload = {
            "tool_name": "generate_vehicle_image",
            "arguments": {"prompt": prompt},
        }
        try:
            response = requests.post(_MCP_EXECUTE_URL, json=payload, timeout=70)
            response.raise_for_status()
            data = response.json()

            content = None
            if "image_base64" in data:
                content = base64.b64decode(data["image_base64"])
            elif "image_url" in data:
                r = requests.get(data["image_url"], timeout=20)
                r.raise_for_status()
                content = r.content

            if content:
                make = _cf(item, "make", "vehicle")
                model = _cf(item, "model", "model")
                year = _cf(item, "year", "")
                fname = f"{make}_{model}_{year}_ai_generated.jpg".lower().replace(
                    " ", "_"
                )
                item.photo.save(fname, ContentFile(content), save=True)
                return True
        except Exception as exc:
            logger.warning("AI image generation failed: %s", exc)
        return False

    # ------------------------------------------------------------------
    # Template context
    # ------------------------------------------------------------------

    def get_detail_context(self, item: DynamicCollectionItem) -> dict[str, Any]:
        return {
            "show_vin_enrich_button": bool(_cf(item, "vin")),
            "show_valuation_button": True,
            "show_photo_refresh_button": True,
            "valuation_history": item.valuation_history.all()[:5],
        }
