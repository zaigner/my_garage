"""
ContextService — single entry point for all AI context retrieval.

Composes the existing DRF selector layer (my_garage.api.selectors) rather
than duplicating ORM queries. The RAG retrieval method (retrieve_relevant_docs)
is wired to the MongoDB vector store built by the build_knowledge_index command.

Usage:
    from my_garage.services import ContextService

    ctx = ContextService()
    vehicle_context = ctx.get_vehicle_context(vehicle_id=1, user=request.user)
    docs = ctx.retrieve_relevant_docs("service record oil change")
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from pymongo.errors import ServerSelectionTimeoutError

from my_garage.api import selectors
from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    Timepiece,
    Vehicle,
)
from my_garage.utils.mongo import get_collection

from .context_models import (
    CollectionItemContext,
    PortfolioSummary,
    ServiceRecordContext,
    TimepieceContext,
    UpgradeContext,
    VehicleContext,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Pure-Python cosine similarity. Returns 0.0 on zero-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class ContextServiceError(Exception):
    """Raised when context cannot be assembled due to a data or permission error."""


class ContextService:
    """
    Assembles structured, typed context for AI interactions.

    All methods return Pydantic models that can be serialized directly
    into prompt templates via ContextService.to_dict().
    """

    # ------------------------------------------------------------------
    # Vehicle
    # ------------------------------------------------------------------

    def get_vehicle_context(self, vehicle_id: int, user) -> VehicleContext:
        """
        Assemble full context for a single vehicle, including financials,
        service history, and upgrade list.

        Raises ContextServiceError if the vehicle doesn't exist or isn't
        owned by the given user.
        """
        try:
            vehicle = Vehicle.objects.select_related("owner").get(
                id=vehicle_id, owner=user
            )
        except Vehicle.DoesNotExist:
            raise ContextServiceError(f"Vehicle {vehicle_id} not found for user {user}")

        build_summary = selectors.vehicle_get_build_summary(vehicle)
        service_qs = selectors.vehicle_list_service_records(vehicle)
        upgrades = selectors.vehicle_list_upgrades(vehicle)

        service_records = [
            ServiceRecordContext(
                id=sr.id,
                date=sr.date,
                vendor=sr.vendor,
                description=sr.description,
                category=sr.category,
                total_cost=sr.total_cost,
                is_verified=sr.is_verified,
            )
            for sr in service_qs[:20]  # cap at 20 for context window budget
        ]

        upgrade_contexts = [
            UpgradeContext(
                id=u.id,
                name=getattr(u, "part_name", None) or getattr(u, "name", ""),
                brand=getattr(u, "brand", ""),
                status=u.status,
                cost=u.cost,
                notes=getattr(u, "notes", ""),
            )
            for u in upgrades[:20]
        ]

        return VehicleContext(
            id=vehicle.id,
            make=vehicle.make,
            model=vehicle.model,
            year=vehicle.year,
            trim=vehicle.trim,
            vin=vehicle.vin,
            exterior_color=vehicle.exterior_color,
            interior_color=vehicle.interior_color,
            transmission=vehicle.transmission,
            mileage=vehicle.mileage,
            purchase_price=vehicle.purchase_price,
            purchase_date=vehicle.purchase_date,
            current_market_value=vehicle.current_market_value,
            specs=vehicle.specs or {},
            features=vehicle.features or {},
            notes=vehicle.notes,
            total_maintenance_cost=build_summary["maintenance_total"],
            total_upgrade_cost=build_summary["upgrade_total"],
            total_investment=build_summary["total_investment"],
            equity=build_summary["equity"],
            is_profitable=build_summary["is_profitable"],
            latest_condition_grade=build_summary["latest_grade"],
            service_records=service_records,
            upgrades=upgrade_contexts,
        )

    # ------------------------------------------------------------------
    # Timepiece
    # ------------------------------------------------------------------

    def get_timepiece_context(self, timepiece_id: int, user) -> TimepieceContext:
        """
        Assemble context for a single timepiece.

        Raises ContextServiceError if the timepiece doesn't exist or isn't
        owned by the given user.
        """
        try:
            timepiece = Timepiece.objects.get(id=timepiece_id, owner=user)
        except Timepiece.DoesNotExist:
            raise ContextServiceError(
                f"Timepiece {timepiece_id} not found for user {user}"
            )

        return TimepieceContext(
            id=timepiece.id,
            brand=timepiece.brand,
            model=timepiece.model,
            reference_number=timepiece.reference_number,
            serial_number=timepiece.serial_number,
            year=timepiece.year,
            movement_type=timepiece.movement_type,
            case_material=timepiece.case_material,
            dial_color=timepiece.dial_color,
            complications=timepiece.complications or [],
            has_box=timepiece.has_box,
            has_papers=timepiece.has_papers,
            condition_grade=timepiece.condition_grade,
            purchase_price=timepiece.purchase_price,
            purchase_date=timepiece.purchase_date,
            current_market_value=timepiece.current_market_value,
            notes=timepiece.notes,
        )

    # ------------------------------------------------------------------
    # Collection item
    # ------------------------------------------------------------------

    def get_collection_item_context(self, item_id: int, user) -> CollectionItemContext:
        """
        Assemble context for a single dynamic collection item.

        Raises ContextServiceError if not found or not owned by user.
        """
        try:
            item = DynamicCollectionItem.objects.select_related("collection_type").get(
                id=item_id, owner=user
            )
        except DynamicCollectionItem.DoesNotExist:
            raise ContextServiceError(
                f"Collection item {item_id} not found for user {user}"
            )

        return CollectionItemContext(
            id=item.id,
            name=item.name,
            collection_type_name=item.collection_type.name,
            collection_type_slug=item.collection_type.slug,
            purchase_price=item.purchase_price,
            purchase_date=item.purchase_date,
            current_market_value=item.current_market_value,
            custom_fields=item.custom_fields or {},
            notes=item.notes,
            service_record_count=item.service_records.count(),
            upgrade_count=item.upgrades.count(),
        )

    # ------------------------------------------------------------------
    # Portfolio summary
    # ------------------------------------------------------------------

    def get_portfolio_summary(self, user) -> PortfolioSummary:
        """
        Aggregate portfolio-level context across all asset types for a user.
        Used for the home dashboard and portfolio-level prompts.
        """
        from django.db.models import Sum
        from django.db.models.functions import Coalesce

        vehicles = Vehicle.objects.filter(owner=user)
        timepieces = Timepiece.objects.filter(owner=user)
        collection_items = DynamicCollectionItem.objects.filter(owner=user)
        collection_types = list(
            CollectionType.objects.filter(owner=user, is_active=True).values_list(
                "name", flat=True
            )
        )

        def _sum_values(qs, field="current_market_value") -> Decimal:
            result = qs.aggregate(total=Coalesce(Sum(field), Decimal("0.00")))["total"]
            return result or Decimal("0.00")

        vehicles_value = _sum_values(vehicles)
        timepieces_value = _sum_values(timepieces)
        collections_value = _sum_values(collection_items)

        return PortfolioSummary(
            vehicle_count=vehicles.count(),
            timepiece_count=timepieces.count(),
            collection_item_count=collection_items.count(),
            total_vehicles_value=vehicles_value,
            total_timepieces_value=timepieces_value,
            total_collections_value=collections_value,
            total_portfolio_value=vehicles_value + timepieces_value + collections_value,
            collection_types=collection_types,
            generated_at=datetime.now(tz=timezone.utc),
        )

    # ------------------------------------------------------------------
    # RAG retrieval
    # ------------------------------------------------------------------

    def retrieve_relevant_docs(self, query: str, k: int = 5) -> list[str]:
        """
        Retrieve the top-k relevant document chunks from the MongoDB
        knowledge index for a given query.

        Uses Python cosine similarity (compatible with local MongoDB 6.x).
        Falls back to empty list on any infrastructure error so callers
        are never blocked.

        The knowledge index is built by:
            pixi run manage build_knowledge_index
        """
        if not query:
            return []

        try:
            embedding = self._embed_query(query)
            if embedding is None:
                return []

            collection = get_collection("knowledge_chunks")
            chunks = list(
                collection.find(
                    {"embedding": {"$exists": True}},
                    {"content": 1, "embedding": 1, "_id": 0},
                )
            )
            if not chunks:
                return []

            scored = [
                (_cosine_similarity(embedding, c["embedding"]), c["content"])
                for c in chunks
                if c.get("embedding")
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
            return [content for _, content in scored[:k]]

        except ServerSelectionTimeoutError:
            logger.warning("MongoDB unavailable — RAG retrieval skipped")
            return []
        except Exception as e:
            logger.warning(f"RAG retrieval failed: {e}")
            return []

    def _embed_query(self, text: str) -> list[float] | None:
        """
        Embed a query string using the Google text-embedding-004 model.
        Returns None if the API key is not configured or the call fails.
        """
        try:
            from django.conf import settings as django_settings
            from google import genai as google_genai

            api_key = getattr(django_settings, "GOOGLE_API_KEY", None)
            if not api_key:
                logger.warning("GOOGLE_API_KEY not set — RAG embedding skipped")
                return None

            client = google_genai.Client(api_key=api_key)
            response = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.warning(f"Embedding query failed: {e}")
            return None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def to_dict(context_model) -> dict:
        """Serialize any context Pydantic model to a plain dict for prompt rendering."""
        return context_model.model_dump(mode="json")
