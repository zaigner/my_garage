"""
ContextService — single entry point for all AI context retrieval.

Composes the existing DRF selector layer (my_garage.api.selectors) rather
than duplicating ORM queries. The RAG retrieval method (retrieve_relevant_docs)
is wired to the MongoDB vector store built by the build_knowledge_index command.

Usage:
    from my_garage.services import ContextService

    ctx = ContextService()
    item_context = ctx.get_collection_item_context(item_id=1, user=request.user)
    docs = ctx.retrieve_relevant_docs("service record oil change")
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from pymongo.errors import ServerSelectionTimeoutError

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
)
from my_garage.utils.mongo import get_collection

from .context_models import (
    CollectionItemContext,
    PortfolioSummary,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Pure-Python cosine similarity. Returns 0.0 on zero-length vectors."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
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
        except DynamicCollectionItem.DoesNotExist as e:
            raise ContextServiceError(
                f"Collection item {item_id} not found for user {user}"
            ) from e

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
        Aggregate portfolio-level context across all collection items for a user.
        Used for the home dashboard and portfolio-level prompts.
        """
        from django.db.models import Sum
        from django.db.models.functions import Coalesce

        _system_slugs = {"automobiles", "horology-salon"}
        all_items = DynamicCollectionItem.objects.filter(owner=user)
        automobiles = all_items.filter(collection_type__slug="automobiles")
        horology = all_items.filter(collection_type__slug="horology-salon")
        other_items = all_items.exclude(collection_type__slug__in=_system_slugs)
        collection_types = list(
            CollectionType.objects.filter(owner=user, is_active=True).values_list(
                "name", flat=True
            )
        )

        def _sum_values(qs, field="current_market_value") -> Decimal:
            result = qs.aggregate(total=Coalesce(Sum(field), Decimal("0.00")))["total"]
            return result or Decimal("0.00")

        vehicles_value = _sum_values(automobiles)
        timepieces_value = _sum_values(horology)
        collections_value = _sum_values(other_items)

        return PortfolioSummary(
            vehicle_count=automobiles.count(),
            timepiece_count=horology.count(),
            collection_item_count=all_items.count(),
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
