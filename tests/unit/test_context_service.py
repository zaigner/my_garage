"""
Tests for ContextService (Phase 5 — unified DynamicCollectionItem).

Uses pytest-django with in-memory SQLite (test settings).
All external I/O (MongoDB, Google API) is mocked.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    GenericServiceRecord,
)
from my_garage.services import ContextService
from my_garage.services.context_models import (
    CollectionItemContext,
    PortfolioSummary,
)
from my_garage.services.context_service import ContextServiceError

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="pass")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="other", password="pass")


@pytest.fixture
def automobiles_type(user):
    ct, _ = CollectionType.objects.get_or_create(
        owner=user,
        slug="automobiles",
        defaults={
            "name": "Automobiles",
            "service_provider_key": "vehicle",
            "is_system": True,
        },
    )
    return ct


@pytest.fixture
def horology_type(user):
    ct, _ = CollectionType.objects.get_or_create(
        owner=user,
        slug="horology-salon",
        defaults={
            "name": "Horology Salon",
            "service_provider_key": "timepiece",
            "is_system": True,
        },
    )
    return ct


@pytest.fixture
def vehicle_item(user, automobiles_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=automobiles_type,
        name="2019 Porsche 911 Carrera S",
        purchase_price=Decimal("85000.00"),
        purchase_date=date(2019, 6, 1),
        current_market_value=Decimal("92000.00"),
        custom_fields={
            "make": "Porsche",
            "model": "911",
            "year": 2019,
            "vin": "WP0AB2A91KS123456",
        },
    )


@pytest.fixture
def service_record(vehicle_item):
    return GenericServiceRecord.objects.create(
        item=vehicle_item,
        date=date(2023, 1, 15),
        vendor="Porsche of Austin",
        description="Annual service",
        category="MAINTENANCE",
        total_cost=Decimal("1200.00"),
        is_verified=True,
    )


@pytest.fixture
def timepiece_item(user, horology_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=horology_type,
        name="Rolex Submariner 126610LN",
        purchase_price=Decimal("13500.00"),
        current_market_value=Decimal("14800.00"),
        custom_fields={
            "brand": "Rolex",
            "watch_model": "Submariner",
            "reference_number": "126610LN",
            "has_box": True,
            "has_papers": True,
        },
    )


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Wine Collection",
        slug="wine-collection",
        field_schema={
            "fields": [{"name": "vintage", "type": "number", "label": "Vintage Year"}]
        },
    )


@pytest.fixture
def collection_item(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="2015 Opus One",
        purchase_price=Decimal("350.00"),
        current_market_value=Decimal("420.00"),
        custom_fields={"vintage": 2015},
    )


@pytest.fixture
def svc():
    return ContextService()


# ---------------------------------------------------------------------------
# get_collection_item_context
# ---------------------------------------------------------------------------


class TestGetCollectionItemContext:
    def test_returns_collection_item_context(self, svc, collection_item, user):
        ctx = svc.get_collection_item_context(item_id=collection_item.id, user=user)
        assert isinstance(ctx, CollectionItemContext)
        assert ctx.name == "2015 Opus One"
        assert ctx.custom_fields["vintage"] == 2015

    def test_collection_type_fields_present(self, svc, collection_item, user):
        ctx = svc.get_collection_item_context(item_id=collection_item.id, user=user)
        assert ctx.collection_type_name == "Wine Collection"
        assert ctx.collection_type_slug == "wine-collection"

    def test_financial_fields(self, svc, collection_item, user):
        ctx = svc.get_collection_item_context(item_id=collection_item.id, user=user)
        assert ctx.purchase_price == Decimal("350.00")
        assert ctx.current_market_value == Decimal("420.00")

    def test_service_record_count(self, svc, vehicle_item, service_record, user):
        ctx = svc.get_collection_item_context(item_id=vehicle_item.id, user=user)
        assert ctx.service_record_count == 1

    def test_raises_for_nonexistent_item(self, svc, user):
        with pytest.raises(ContextServiceError):
            svc.get_collection_item_context(item_id=9999, user=user)

    def test_raises_for_wrong_owner(self, svc, collection_item, other_user):
        with pytest.raises(ContextServiceError):
            svc.get_collection_item_context(item_id=collection_item.id, user=other_user)

    def test_serializable_to_dict(self, svc, collection_item, user):
        ctx = svc.get_collection_item_context(item_id=collection_item.id, user=user)
        d = ContextService.to_dict(ctx)
        assert isinstance(d, dict)
        assert d["name"] == "2015 Opus One"


# ---------------------------------------------------------------------------
# get_portfolio_summary
# ---------------------------------------------------------------------------


class TestGetPortfolioSummary:
    def test_returns_portfolio_summary(
        self, svc, vehicle_item, timepiece_item, collection_item, user
    ):
        summary = svc.get_portfolio_summary(user=user)
        assert isinstance(summary, PortfolioSummary)
        assert summary.vehicle_count == 1
        assert summary.timepiece_count == 1

    def test_total_value_covers_all_items(
        self, svc, vehicle_item, timepiece_item, collection_item, user
    ):
        summary = svc.get_portfolio_summary(user=user)
        expected = (
            vehicle_item.current_market_value
            + timepiece_item.current_market_value
            + collection_item.current_market_value
        )
        assert summary.total_portfolio_value == expected

    def test_empty_portfolio(self, svc, user):
        summary = svc.get_portfolio_summary(user=user)
        assert summary.vehicle_count == 0
        assert summary.total_portfolio_value == Decimal("0.00")

    def test_collection_types_listed(self, svc, collection_type, user):
        summary = svc.get_portfolio_summary(user=user)
        assert "Wine Collection" in summary.collection_types

    def test_total_items_count(
        self, svc, vehicle_item, timepiece_item, collection_item, user
    ):
        summary = svc.get_portfolio_summary(user=user)
        assert summary.collection_item_count == 3


# ---------------------------------------------------------------------------
# retrieve_relevant_docs (RAG)
# ---------------------------------------------------------------------------


class TestRetrieveRelevantDocs:
    def test_returns_empty_list_on_mongodb_timeout(self, svc):
        with patch("my_garage.services.context_service.get_collection") as mock_col:
            from pymongo.errors import ServerSelectionTimeoutError

            mock_col.side_effect = ServerSelectionTimeoutError("timeout")
            result = svc.retrieve_relevant_docs("oil change service")
            assert result == []

    def test_returns_empty_list_on_empty_query(self, svc):
        result = svc.retrieve_relevant_docs("")
        assert result == []

    def test_returns_empty_list_when_embed_returns_none(self, svc):
        with patch.object(svc, "_embed_query", return_value=None):
            result = svc.retrieve_relevant_docs("some query")
            assert result == []

    def test_returns_content_from_mongo_results(self, svc):
        mock_embedding = [1.0] + [0.0] * 767

        with patch.object(svc, "_embed_query", return_value=mock_embedding):
            mock_coll = MagicMock()
            mock_coll.find.return_value = [
                {
                    "content": "Service records track maintenance history.",
                    "embedding": [1.0] + [0.0] * 767,
                },
                {
                    "content": "Oil changes should be done every 10,000 miles.",
                    "embedding": [0.0, 1.0] + [0.0] * 766,
                },
            ]
            with patch(
                "my_garage.services.context_service.get_collection",
                return_value=mock_coll,
            ):
                result = svc.retrieve_relevant_docs("oil change service", k=2)

        assert len(result) == 2
        assert "Service records" in result[0]


# ---------------------------------------------------------------------------
# to_dict utility
# ---------------------------------------------------------------------------


class TestToDict:
    def test_decimal_fields_serialize_to_string(self, svc, collection_item, user):
        ctx = svc.get_collection_item_context(item_id=collection_item.id, user=user)
        d = ContextService.to_dict(ctx)
        # Pydantic JSON mode converts Decimal → str
        assert isinstance(d["purchase_price"], str)

    def test_dict_has_expected_keys(self, svc, collection_item, user):
        ctx = svc.get_collection_item_context(item_id=collection_item.id, user=user)
        d = ContextService.to_dict(ctx)
        assert "name" in d
        assert "collection_type_name" in d
        assert "custom_fields" in d
