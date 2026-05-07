"""
Eval tests: Collection item context assembly (Phase 5 — unified DynamicCollectionItem).
Validates against the golden dataset to catch regressions in context structure.
"""

from __future__ import annotations

import pytest

from my_garage.services import ContextService
from my_garage.services.context_service import ContextServiceError

pytestmark = pytest.mark.django_db


class TestVehicleContextGoldenDataset:
    def test_all_expected_keys_present(
        self, golden_dataset, context_service, eval_vehicle, eval_user
    ):
        case = next(c for c in golden_dataset if c["id"] == "vehicle_context_basic")
        ctx = context_service.get_collection_item_context(eval_vehicle.id, eval_user)
        d = ContextService.to_dict(ctx)

        for key in case["expected_keys"]:
            assert key in d, f"Missing key: {key}"

    def test_expected_values_match(
        self, golden_dataset, context_service, eval_vehicle, eval_user
    ):
        case = next(c for c in golden_dataset if c["id"] == "vehicle_context_basic")
        ctx = context_service.get_collection_item_context(eval_vehicle.id, eval_user)
        d = ContextService.to_dict(ctx)

        for key, expected in case["expected_values"].items():
            assert d[key] == expected, f"Key {key}: expected {expected}, got {d[key]}"

    def test_service_records_populated(
        self, golden_dataset, context_service, eval_vehicle, eval_user
    ):
        case = next(
            c for c in golden_dataset if c["id"] == "vehicle_service_records_populated"
        )
        ctx = context_service.get_collection_item_context(eval_vehicle.id, eval_user)
        assert ctx.service_record_count >= case["expected_service_record_count_min"]

    def test_financial_aggregates(
        self, golden_dataset, context_service, eval_vehicle, eval_user
    ):
        case = next(
            c for c in golden_dataset if c["id"] == "vehicle_financial_aggregates"
        )
        ctx = context_service.get_collection_item_context(eval_vehicle.id, eval_user)
        financials = case["expected_financials"]
        assert str(ctx.purchase_price) == financials["purchase_price"]
        assert str(ctx.current_market_value) == financials["current_market_value"]

    def test_context_serializes_to_dict(self, context_service, eval_vehicle, eval_user):
        ctx = context_service.get_collection_item_context(eval_vehicle.id, eval_user)
        d = ContextService.to_dict(ctx)
        assert isinstance(d, dict)
        assert isinstance(d["purchase_price"], str)
        assert isinstance(d["current_market_value"], str)

    def test_wrong_owner_raises(self, context_service, eval_vehicle, eval_user):
        from django.contrib.auth import get_user_model

        other = get_user_model().objects.create_user(username="intruder", password="x")
        with pytest.raises(ContextServiceError):
            context_service.get_collection_item_context(eval_vehicle.id, other)


class TestTimepieceContextGoldenDataset:
    def test_all_expected_keys_present(
        self, golden_dataset, context_service, eval_timepiece, eval_user
    ):
        case = next(c for c in golden_dataset if c["id"] == "timepiece_context_basic")
        ctx = context_service.get_collection_item_context(eval_timepiece.id, eval_user)
        d = ContextService.to_dict(ctx)

        for key in case["expected_keys"]:
            assert key in d, f"Missing key: {key}"

    def test_expected_values_match(
        self, golden_dataset, context_service, eval_timepiece, eval_user
    ):
        case = next(c for c in golden_dataset if c["id"] == "timepiece_context_basic")
        ctx = context_service.get_collection_item_context(eval_timepiece.id, eval_user)
        d = ContextService.to_dict(ctx)

        for key, expected in case["expected_values"].items():
            assert d[key] == expected, f"Key {key}: expected {expected}, got {d[key]}"

    def test_horology_custom_fields_present(
        self, golden_dataset, context_service, eval_timepiece, eval_user
    ):
        case = next(c for c in golden_dataset if c["id"] == "timepiece_context_basic")
        ctx = context_service.get_collection_item_context(eval_timepiece.id, eval_user)
        for field_key in case["expected_custom_field_keys"]:
            assert field_key in ctx.custom_fields, f"Missing custom field: {field_key}"


class TestCollectionItemContextGoldenDataset:
    def test_all_expected_keys_present(
        self, golden_dataset, context_service, eval_collection_item, eval_user
    ):
        case = next(
            c for c in golden_dataset if c["id"] == "collection_item_context_basic"
        )
        ctx = context_service.get_collection_item_context(
            eval_collection_item.id, eval_user
        )
        d = ContextService.to_dict(ctx)

        for key in case["expected_keys"]:
            assert key in d, f"Missing key: {key}"

    def test_custom_fields_present(
        self, golden_dataset, context_service, eval_collection_item, eval_user
    ):
        case = next(
            c for c in golden_dataset if c["id"] == "collection_item_context_basic"
        )
        ctx = context_service.get_collection_item_context(
            eval_collection_item.id, eval_user
        )
        for field_key in case["expected_custom_field_keys"]:
            assert field_key in ctx.custom_fields, f"Missing custom field: {field_key}"


class TestPortfolioSummaryGoldenDataset:
    def test_all_expected_keys_present(
        self,
        golden_dataset,
        context_service,
        eval_vehicle,
        eval_timepiece,
        eval_collection_item,
        eval_user,
    ):
        case = next(c for c in golden_dataset if c["id"] == "portfolio_summary_counts")
        summary = context_service.get_portfolio_summary(eval_user)
        d = ContextService.to_dict(summary)

        for key in case["expected_keys"]:
            assert key in d, f"Missing key: {key}"

    def test_counts_match(
        self,
        golden_dataset,
        context_service,
        eval_vehicle,
        eval_timepiece,
        eval_collection_item,
        eval_user,
    ):
        case = next(c for c in golden_dataset if c["id"] == "portfolio_summary_counts")
        summary = context_service.get_portfolio_summary(eval_user)

        for key, expected in case["expected_counts"].items():
            actual = getattr(summary, key)
            assert actual == expected, f"{key}: expected {expected}, got {actual}"

    def test_total_value_is_sum_of_parts(
        self,
        context_service,
        eval_vehicle,
        eval_timepiece,
        eval_collection_item,
        eval_user,
    ):
        summary = context_service.get_portfolio_summary(eval_user)
        expected = (
            summary.total_vehicles_value
            + summary.total_timepieces_value
            + summary.total_collections_value
        )
        assert summary.total_portfolio_value == expected
