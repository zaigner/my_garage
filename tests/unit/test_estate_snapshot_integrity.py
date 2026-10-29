"""Unit tests for Story 3.1: activation snapshots bound to their token."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from my_garage.api.estate_selectors import (
    get_executor_item_detail_context,
    get_executor_portfolio_context,
)
from my_garage.api.services import activate_estate_plan
from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    EstateAccessToken,
    ValuationSnapshot,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_user(username="integrity_owner", password="pass")


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


def _item(owner, ct, name, value=None):
    return DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name, current_market_value=value
    )


def _activate(owner):
    activate_estate_plan(owner)
    return EstateAccessToken.objects.get(owner=owner, is_active=True)


class TestActivation:
    def test_snapshots_carry_token_and_item_name(self, owner, cars):
        _item(owner, cars, "911", Decimal("100"))
        _item(owner, cars, "M3", Decimal("50"))
        token = _activate(owner)
        snaps = ValuationSnapshot.objects.filter(owner=owner)
        assert snaps.count() == 2
        assert {(s.token_id, s.item_name) for s in snaps} == {
            (token.pk, "911"),
            (token.pk, "M3"),
        }

    def test_str_does_not_touch_item(self, owner, cars):
        item = _item(owner, cars, "911")
        _activate(owner)
        item.delete()
        snap = ValuationSnapshot.objects.get(owner=owner)
        assert "911" in str(snap)


class TestItemDeletion:
    def test_row_remains_with_null_item(self, owner, cars):
        item = _item(owner, cars, "911", Decimal("100"))
        token = _activate(owner)
        item.delete()
        snap = ValuationSnapshot.objects.get(owner=owner)
        assert snap.item_id is None
        assert snap.item_name == "911"
        assert snap.token_id == token.pk
        assert snap.market_value == Decimal("100")

    def test_owner_deletion_still_removes_snapshots(self, owner, cars):
        _item(owner, cars, "911", Decimal("100"))
        _activate(owner)
        owner.delete()
        assert ValuationSnapshot.objects.count() == 0

    def test_removed_row_and_totals(self, owner, cars):
        _item(owner, cars, "Kept", Decimal("100"))
        gone = _item(owner, cars, "Gone", Decimal("40"))
        token = _activate(owner)
        before = get_executor_portfolio_context(owner, token)
        gone.delete()
        _item(owner, cars, "Added later", Decimal("7"))

        ctx = get_executor_portfolio_context(owner, token)
        assert ctx["snapshot_total"] == before["snapshot_total"] == Decimal("140")
        assert ctx["snapshot_count"] == 2
        assert ctx["removed_count"] == 1
        assert ctx["removed_rows"] == [
            {
                "item": None,
                "item_name": "Gone",
                "snapshot_value": Decimal("40"),
                "removed": True,
            }
        ]
        assert [r["item"].name for r in ctx["rows"]] == ["Added later", "Kept"]
        assert ctx["items_total"] == 2
        assert ctx["unassigned_count"] == 2
        assert ctx["current_total"] == Decimal("107")
        assert ctx["delta"] == Decimal("0") and ctx["compared_count"] == 1

    def test_unvalued_removed_item_not_counted_as_valued(self, owner, cars):
        gone = _item(owner, cars, "Gone")
        token = _activate(owner)
        gone.delete()
        ctx = get_executor_portfolio_context(owner, token)
        assert ctx["removed_count"] == 1
        assert ctx["snapshot_total"] is None and ctx["snapshot_count"] == 0

    def test_detail_of_deleted_item_is_none(self, owner, cars):
        gone = _item(owner, cars, "Gone", Decimal("40"))
        token = _activate(owner)
        pk = gone.pk
        gone.delete()
        assert get_executor_item_detail_context(owner, token, pk) is None


class TestTokenScope:
    def test_both_selectors_read_only_their_token(self, owner, cars):
        item = _item(owner, cars, "911", Decimal("100"))
        gone = _item(owner, cars, "Gone", Decimal("5"))
        first = _activate(owner)
        gone.delete()
        item.current_market_value = Decimal("200")
        item.save()
        second = _activate(owner)

        # The first session still sees its own values, incl. the removed item
        ctx1 = get_executor_portfolio_context(owner, first)
        assert ctx1["rows"][0]["snapshot_value"] == Decimal("100")
        assert ctx1["removed_count"] == 1
        detail1 = get_executor_item_detail_context(owner, first, item.pk)
        assert detail1["snapshot"].market_value == Decimal("100")

        # The new session reads only the rows of the new token
        ctx2 = get_executor_portfolio_context(owner, second)
        assert ctx2["rows"][0]["snapshot_value"] == Decimal("200")
        assert ctx2["removed_count"] == 0
        assert ctx2["snapshot_total"] == Decimal("200")
        detail2 = get_executor_item_detail_context(owner, second, item.pk)
        assert detail2["snapshot"].market_value == Decimal("200")

    def test_other_token_row_created_later_is_ignored(self, owner, cars):
        # Timestamp matching would have picked this row up; token matching does not
        item = _item(owner, cars, "911", Decimal("100"))
        earlier = _activate(owner)
        current = _activate(owner)
        ValuationSnapshot.objects.create(
            item=item,
            item_name=item.name,
            owner=owner,
            token=earlier,
            snapshot_date=datetime.date.today(),
            market_value=Decimal("999"),
            snapshot_trigger="ESTATE_ACTIVATION",
        )
        ctx = get_executor_portfolio_context(owner, current)
        assert ctx["snapshot_total"] == Decimal("100")
        detail = get_executor_item_detail_context(owner, current, item.pk)
        assert detail["snapshot"].market_value == Decimal("100")

    def test_dashboard_and_detail_agree(self, owner, cars):
        item = _item(owner, cars, "911", Decimal("100"))
        token = _activate(owner)
        row = get_executor_portfolio_context(owner, token)["rows"][0]
        detail = get_executor_item_detail_context(owner, token, item.pk)
        assert row["snapshot_value"] == detail["row"]["snapshot_value"]


class TestQueryCounts:
    def test_portfolio_two_queries_with_removed_rows(
        self, owner, cars, django_assert_num_queries
    ):
        items = [_item(owner, cars, f"Car {i}", Decimal("10")) for i in range(4)]
        token = _activate(owner)
        items[0].delete()
        items[1].delete()
        with django_assert_num_queries(2):
            ctx = get_executor_portfolio_context(owner, token)
            for row in ctx["rows"]:
                str(row["item"].collection_type.name)
                str(row["beneficiary_name"])
            for row in ctx["removed_rows"]:
                str(row["item_name"])
        assert ctx["removed_count"] == 2

    def test_detail_four_queries(self, owner, cars, django_assert_num_queries):
        item = _item(owner, cars, "911", Decimal("10"))
        token = _activate(owner)
        with django_assert_num_queries(4):
            get_executor_item_detail_context(owner, token, item.pk)
