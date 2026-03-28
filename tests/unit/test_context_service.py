"""
Tests for ContextService (Phase 1.1).

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
    ServiceRecord,
    Timepiece,
    Vehicle,
)
from my_garage.services import ContextService
from my_garage.services.context_models import (
    CollectionItemContext,
    PortfolioSummary,
    TimepieceContext,
    VehicleContext,
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
def vehicle(user):
    return Vehicle.objects.create(
        owner=user,
        make="Porsche",
        model="911",
        year=2019,
        trim="Carrera S",
        vin="WP0AB2A91KS123456",
        exterior_color="Guards Red",
        interior_color="Black",
        mileage=12000,
        purchase_price=Decimal("85000.00"),
        purchase_date=date(2019, 6, 1),
        current_market_value=Decimal("92000.00"),
    )


@pytest.fixture
def service_record(vehicle):
    return ServiceRecord.objects.create(
        vehicle=vehicle,
        date=date(2023, 1, 15),
        vendor="Porsche of Austin",
        description="Annual service",
        category="MAINTENANCE",
        total_cost=Decimal("1200.00"),
        is_verified=True,
    )


@pytest.fixture
def timepiece(user):
    return Timepiece.objects.create(
        owner=user,
        brand="Rolex",
        model="Submariner",
        reference_number="126610LN",
        serial_number="SN123456",
        year=2022,
        movement_type="AUTOMATIC",
        case_material="Oystersteel",
        dial_color="Black",
        complications=["Date"],
        has_box=True,
        has_papers=True,
        condition_grade="Mint",
        purchase_price=Decimal("13500.00"),
        current_market_value=Decimal("14800.00"),
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
# get_vehicle_context
# ---------------------------------------------------------------------------


class TestGetVehicleContext:
    def test_returns_vehicle_context_model(self, svc, vehicle, user, service_record):
        ctx = svc.get_vehicle_context(vehicle_id=vehicle.id, user=user)
        assert isinstance(ctx, VehicleContext)

    def test_basic_fields(self, svc, vehicle, user):
        ctx = svc.get_vehicle_context(vehicle_id=vehicle.id, user=user)
        assert ctx.make == "Porsche"
        assert ctx.model == "911"
        assert ctx.year == 2019
        assert ctx.vin == "WP0AB2A91KS123456"

    def test_includes_financial_aggregates(self, svc, vehicle, user, service_record):
        ctx = svc.get_vehicle_context(vehicle_id=vehicle.id, user=user)
        assert ctx.total_maintenance_cost == Decimal("1200.00")
        assert ctx.total_investment > Decimal("0")

    def test_includes_service_records(self, svc, vehicle, user, service_record):
        ctx = svc.get_vehicle_context(vehicle_id=vehicle.id, user=user)
        assert len(ctx.service_records) == 1
        assert ctx.service_records[0].vendor == "Porsche of Austin"

    def test_raises_for_nonexistent_vehicle(self, svc, user):
        with pytest.raises(ContextServiceError):
            svc.get_vehicle_context(vehicle_id=9999, user=user)

    def test_raises_for_wrong_owner(self, svc, vehicle, other_user):
        with pytest.raises(ContextServiceError):
            svc.get_vehicle_context(vehicle_id=vehicle.id, user=other_user)

    def test_serializable_to_dict(self, svc, vehicle, user):
        ctx = svc.get_vehicle_context(vehicle_id=vehicle.id, user=user)
        d = ContextService.to_dict(ctx)
        assert isinstance(d, dict)
        assert d["make"] == "Porsche"
        assert isinstance(
            d["total_maintenance_cost"], str
        )  # Decimal → str in JSON mode


# ---------------------------------------------------------------------------
# get_timepiece_context
# ---------------------------------------------------------------------------


class TestGetTimepieceContext:
    def test_returns_timepiece_context_model(self, svc, timepiece, user):
        ctx = svc.get_timepiece_context(timepiece_id=timepiece.id, user=user)
        assert isinstance(ctx, TimepieceContext)

    def test_basic_fields(self, svc, timepiece, user):
        ctx = svc.get_timepiece_context(timepiece_id=timepiece.id, user=user)
        assert ctx.brand == "Rolex"
        assert ctx.reference_number == "126610LN"
        assert ctx.has_box is True
        assert ctx.has_papers is True

    def test_raises_for_wrong_owner(self, svc, timepiece, other_user):
        with pytest.raises(ContextServiceError):
            svc.get_timepiece_context(timepiece_id=timepiece.id, user=other_user)


# ---------------------------------------------------------------------------
# get_collection_item_context
# ---------------------------------------------------------------------------


class TestGetCollectionItemContext:
    def test_returns_collection_item_context(self, svc, collection_item, user):
        ctx = svc.get_collection_item_context(item_id=collection_item.id, user=user)
        assert isinstance(ctx, CollectionItemContext)
        assert ctx.name == "2015 Opus One"
        assert ctx.custom_fields["vintage"] == 2015

    def test_raises_for_wrong_owner(self, svc, collection_item, other_user):
        with pytest.raises(ContextServiceError):
            svc.get_collection_item_context(item_id=collection_item.id, user=other_user)


# ---------------------------------------------------------------------------
# get_portfolio_summary
# ---------------------------------------------------------------------------


class TestGetPortfolioSummary:
    def test_returns_portfolio_summary(
        self, svc, vehicle, timepiece, collection_item, user
    ):
        summary = svc.get_portfolio_summary(user=user)
        assert isinstance(summary, PortfolioSummary)
        assert summary.vehicle_count == 1
        assert summary.timepiece_count == 1
        assert summary.collection_item_count == 1

    def test_total_value_is_sum_of_parts(
        self, svc, vehicle, timepiece, collection_item, user
    ):
        summary = svc.get_portfolio_summary(user=user)
        expected = (
            vehicle.current_market_value
            + timepiece.current_market_value
            + (collection_item.current_market_value or Decimal("0"))
        )
        assert summary.total_portfolio_value == expected

    def test_empty_portfolio(self, svc, user):
        summary = svc.get_portfolio_summary(user=user)
        assert summary.vehicle_count == 0
        assert summary.total_portfolio_value == Decimal("0.00")

    def test_collection_types_listed(self, svc, collection_type, user):
        summary = svc.get_portfolio_summary(user=user)
        assert "Wine Collection" in summary.collection_types


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
    def test_decimal_fields_serialize_to_string(self, svc, vehicle, user):
        ctx = svc.get_vehicle_context(vehicle_id=vehicle.id, user=user)
        d = ContextService.to_dict(ctx)
        # Pydantic JSON mode converts Decimal → str
        assert isinstance(d["purchase_price"], str)

    def test_nested_records_serialize(self, svc, vehicle, user, service_record):
        ctx = svc.get_vehicle_context(vehicle_id=vehicle.id, user=user)
        d = ContextService.to_dict(ctx)
        assert isinstance(d["service_records"], list)
        assert d["service_records"][0]["vendor"] == "Porsche of Austin"
