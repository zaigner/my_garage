"""Unit tests for Story 3.5: the beneficiary item detail selector."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from my_garage.api.selectors import (
    get_beneficiary_assignment,
    get_beneficiary_item_detail_context,
)
from my_garage.api.services import (
    activate_estate_plan,
    claim_beneficiary_link,
    issue_beneficiary_link,
)
from my_garage.models import (
    Beneficiary,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateAccessToken,
    GenericServiceRecord,
    ValuationSnapshot,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_user(username="detail_owner", password="pass")


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


def _beneficiary(owner, name):
    return Beneficiary.objects.create(owner=owner, name=name, relationship="Child")


def _assign(owner, ct, beneficiary, name, charitable=False, note="", **fields):
    item = DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name, **fields
    )
    BeneficiaryAssignment.objects.create(
        item=item,
        beneficiary=beneficiary,
        is_charitable=charitable,
        charitable_org="Org" if charitable else "",
        conditional_note=note,
    )
    return item


@pytest.fixture
def ann(owner):
    return _beneficiary(owner, "Ann")


@pytest.fixture
def car(owner, cars, ann):
    return _assign(
        owner,
        cars,
        ann,
        "Ann car",
        note="  Keep it garaged.  ",
        purchase_price=Decimal("10000"),
        purchase_date=date(2020, 5, 1),
        current_market_value=Decimal("15000"),
        custom_fields={"colour": "Red", "specs": {"hp": 300}, "blank": ""},
    )


def _link(owner, beneficiary):
    """Activate (snapshotting every item that exists now) and claim a link."""
    activate_estate_plan(owner)
    token = EstateAccessToken.objects.get(owner=owner, is_active=True)
    return claim_beneficiary_link(issue_beneficiary_link(beneficiary, token))


class TestContext:
    def test_fields(self, owner, car, ann):
        GenericServiceRecord.objects.create(
            item=car, date=date(2021, 1, 1), vendor="Old", description="a", total_cost=1
        )
        GenericServiceRecord.objects.create(
            item=car, date=date(2022, 1, 1), vendor="New", description="b", total_cost=2
        )
        link = _link(owner, ann)
        # Values move after activation; the snapshot keeps the old ones
        car.current_market_value = Decimal("16000")
        car.save()
        ctx = get_beneficiary_item_detail_context(link, car.pk)
        assert ctx["item"] == car
        assert ctx["item"].current_market_value == Decimal("16000")
        assert ctx["conditional_note"] == "Keep it garaged."
        assert ctx["custom_fields"] == [("Colour", "Red")]
        assert [r.vendor for r in ctx["service_records"]] == ["New", "Old"]
        assert ctx["snapshot"].token == link.issued_by_token
        assert ctx["snapshot"].market_value == Decimal("15000")

    def test_added_after_activation(self, owner, cars, ann, car):
        link = _link(owner, ann)
        later = _assign(owner, cars, ann, "Later car")
        ctx = get_beneficiary_item_detail_context(link, later.pk)
        assert ctx["snapshot"] is None

    def test_older_tokens_snapshot_ignored(self, owner, cars, ann, car):
        link = _link(owner, ann)
        later = _assign(owner, cars, ann, "Later car")
        old = EstateAccessToken.objects.create(
            owner=owner, token_hash="0" * 64, is_active=False
        )
        ValuationSnapshot.objects.create(
            item=later,
            item_name=later.name,
            owner=owner,
            token=old,
            snapshot_trigger="ESTATE_ACTIVATION",
            snapshot_date=date(2020, 1, 1),
            market_value=Decimal("1"),
        )
        assert get_beneficiary_item_detail_context(link, later.pk)["snapshot"] is None
        assert get_beneficiary_item_detail_context(link, car.pk)["snapshot"]

    def test_blank_note(self, owner, cars, ann):
        item = _assign(owner, cars, ann, "Plain car")
        link = _link(owner, ann)
        assert get_beneficiary_item_detail_context(link, item.pk)[
            "conditional_note"
        ] == ("")


class TestIsolation:
    @pytest.mark.parametrize(
        "case",
        [
            "other",
            "unassigned",
            "charitable",
            "soft_deleted",
            "other_owner",
            "none",
            "huge_id",
        ],
    )
    def test_excluded(self, owner, cars, ann, car, case):
        if case == "other":
            item = _assign(owner, cars, _beneficiary(owner, "Bob"), "Bob car")
        elif case == "unassigned":
            item = DynamicCollectionItem.objects.create(
                owner=owner, collection_type=cars, name="Spare"
            )
        elif case == "charitable":
            item = _assign(owner, cars, ann, "Gift", charitable=True)
        elif case == "soft_deleted":
            gone = CollectionType.objects.create(owner=owner, name="Gone")
            item = _assign(owner, gone, ann, "Hidden")
            gone.is_active = False
            gone.save()
        elif case == "other_owner":
            stranger = User.objects.create_user(username="stranger", password="x")
            ct = CollectionType.objects.create(owner=stranger, name="Theirs")
            item = _assign(stranger, ct, _beneficiary(stranger, "Ann"), "Their car")
        else:
            item = None
        link = _link(owner, ann)
        # 2**70 overflows a 64-bit id: it must read as no match, not raise
        item_id = item.pk if item else (2**70 if case == "huge_id" else 999999)
        assert get_beneficiary_item_detail_context(link, item_id) is None
        assert get_beneficiary_assignment(link, item_id) is None
        assert get_beneficiary_item_detail_context(link, car.pk) is not None


class TestQueryCount:
    @pytest.mark.parametrize("records", [1, 3])
    def test_fixed(self, owner, car, ann, records, django_assert_num_queries):
        for i in range(records):
            GenericServiceRecord.objects.create(
                item=car,
                date=date(2022, 1, 1 + i),
                vendor=f"V{i}",
                description="x",
                total_cost=1,
            )
        link = _link(owner, ann)
        with django_assert_num_queries(3):
            ctx = get_beneficiary_item_detail_context(link, car.pk)
            assert ctx["item"].collection_type.name == "Cars"
        assert len(ctx["service_records"]) == records
