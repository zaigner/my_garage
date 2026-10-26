"""Unit tests for Story 2.3: get_executor_portfolio_context."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from my_garage.api.selectors import get_executor_portfolio_context
from my_garage.api.services import activate_estate_plan
from my_garage.models import (
    Beneficiary,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateAccessToken,
    ValuationSnapshot,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_user(username="portfolio_owner", password="pass")


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


def _item(owner, collection_type, name, value=None):
    return DynamicCollectionItem.objects.create(
        owner=owner,
        collection_type=collection_type,
        name=name,
        current_market_value=value,
    )


def _ctx(owner):
    """Context for the owner's active token (one is created if never activated)."""
    token = EstateAccessToken.objects.filter(owner=owner, is_active=True).first()
    if token is None:
        token = EstateAccessToken.objects.create(owner=owner, token_hash="0" * 64)
    return get_executor_portfolio_context(owner, token)


def _row(ctx, name):
    return next(r for r in ctx["rows"] if r["item"].name == name)


class TestRows:
    def test_empty_portfolio(self, owner):
        ctx = _ctx(owner)
        assert ctx["rows"] == [] and ctx["items_total"] == 0
        assert ctx["snapshot_total"] is None and ctx["current_total"] is None
        assert ctx["delta"] is None and ctx["unassigned_count"] == 0

    def test_latest_snapshot_wins(self, owner, cars):
        item = _item(owner, cars, "911", Decimal("100000"))
        activate_estate_plan(owner)
        item.current_market_value = Decimal("120000")
        item.save()
        activate_estate_plan(owner)
        assert _row(_ctx(owner), "911")["snapshot_value"] == Decimal("120000")

    def test_item_added_after_activation_is_listed_without_snapshot(self, owner, cars):
        activate_estate_plan(owner)
        _item(owner, cars, "M3", Decimal("50000"))
        row = _row(_ctx(owner), "M3")
        assert row["snapshot_value"] is None and not row["in_snapshot"]
        assert row["current_value"] == Decimal("50000")

    def test_unvalued_item_at_activation_is_in_snapshot(self, owner, cars):
        _item(owner, cars, "Unvalued")
        activate_estate_plan(owner)
        row = _row(_ctx(owner), "Unvalued")
        assert row["in_snapshot"] and row["snapshot_value"] is None

    def test_ignores_manual_and_earlier_activation_snapshots(self, owner, cars):
        item = _item(owner, cars, "911", Decimal("100"))
        activate_estate_plan(owner)  # earlier activation: 100
        item.current_market_value = Decimal("200")
        item.save()
        activate_estate_plan(owner)  # current activation: 200
        ValuationSnapshot.objects.create(
            item=item,
            owner=owner,
            snapshot_date=item.created_at.date(),
            market_value=Decimal("999"),
            snapshot_trigger="MANUAL",
        )
        assert _row(_ctx(owner), "911")["snapshot_value"] == Decimal("200")

    def test_other_owners_items_excluded(self, owner, cars):
        other = User.objects.create_user(username="someone_else", password="pass")
        _item(other, CollectionType.objects.create(owner=other, name="Art"), "Theirs")
        _item(owner, cars, "Mine")
        names = [r["item"].name for r in _ctx(owner)["rows"]]
        assert names == ["Mine"]

    def test_ordered_by_collection_then_name(self, owner, cars):
        watches = CollectionType.objects.create(owner=owner, name="Watches")
        _item(owner, watches, "Rolex")
        _item(owner, cars, "Zonda")
        _item(owner, cars, "Alpine")
        names = [r["item"].name for r in _ctx(owner)["rows"]]
        assert names == ["Alpine", "Zonda", "Rolex"]

    def test_query_count(self, owner, cars, django_assert_num_queries):
        for i in range(5):
            _item(owner, cars, f"Car {i}", Decimal("1000"))
        activate_estate_plan(owner)
        token = EstateAccessToken.objects.get(owner=owner, is_active=True)
        with django_assert_num_queries(2):
            ctx = get_executor_portfolio_context(owner, token)
            for row in ctx["rows"]:
                str(row["item"].collection_type.name)
                str(row["beneficiary_name"])


class TestDesignation:
    def test_states(self, owner, cars):
        kid = Beneficiary.objects.create(
            owner=owner, name="Priya", relationship="Child"
        )
        gone = Beneficiary.objects.create(
            owner=owner, name="Gone", relationship="Friend"
        )
        assigned = _item(owner, cars, "Assigned")
        charity = _item(owner, cars, "Charity")
        orphaned = _item(owner, cars, "Orphaned")
        _item(owner, cars, "Nothing")
        BeneficiaryAssignment.objects.create(item=assigned, beneficiary=kid)
        BeneficiaryAssignment.objects.create(
            item=charity, is_charitable=True, charitable_org="Red Cross"
        )
        BeneficiaryAssignment.objects.create(item=orphaned, beneficiary=gone)
        gone.delete()  # SET_NULL leaves the assignment behind

        ctx = _ctx(owner)
        assert _row(ctx, "Assigned")["beneficiary_name"] == "Priya"
        assert not _row(ctx, "Assigned")["is_unassigned"]
        assert _row(ctx, "Charity")["is_charitable"]
        assert _row(ctx, "Charity")["charitable_org"] == "Red Cross"
        assert not _row(ctx, "Charity")["is_unassigned"]
        assert _row(ctx, "Orphaned")["is_unassigned"]
        assert _row(ctx, "Nothing")["is_unassigned"]
        assert ctx["unassigned_count"] == 2


class TestTotals:
    def test_totals_skip_nulls_and_delta_uses_items_valued_at_both(self, owner, cars):
        both = _item(owner, cars, "Both", Decimal("100"))
        _item(owner, cars, "Snapshot only", Decimal("40"))
        _item(owner, cars, "Never valued")
        activate_estate_plan(owner)
        both.current_market_value = Decimal("150")
        both.save()
        snapshot_only = DynamicCollectionItem.objects.get(name="Snapshot only")
        snapshot_only.current_market_value = None
        snapshot_only.save()
        _item(owner, cars, "Added later", Decimal("10"))

        ctx = _ctx(owner)
        assert ctx["items_total"] == 4
        assert ctx["snapshot_total"] == Decimal("140")
        assert ctx["current_total"] == Decimal("160")
        assert ctx["delta"] == Decimal("50")
        assert ctx["compared_count"] == 1
        assert ctx["snapshot_count"] == 2 and ctx["current_count"] == 2

    def test_no_values_anywhere(self, owner, cars):
        _item(owner, cars, "Unvalued")
        activate_estate_plan(owner)
        ctx = _ctx(owner)
        assert ctx["snapshot_total"] is None
        assert ctx["current_total"] is None
        assert ctx["delta"] is None and ctx["compared_count"] == 0
