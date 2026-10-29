"""Unit tests for Story 2.4: get_executor_item_detail_context."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from my_garage.api.estate_selectors import get_executor_item_detail_context
from my_garage.api.selectors import get_item_display_custom_fields
from my_garage.api.services import activate_estate_plan
from my_garage.models import (
    Beneficiary,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateAccessToken,
    GenericServiceRecord,
    GenericValuationHistory,
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


def _item(owner, ct, name="Car", value=None, **kw):
    return DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name, current_market_value=value, **kw
    )


def _token(owner):
    activate_estate_plan(owner)
    return EstateAccessToken.objects.get(owner=owner, is_active=True)


def test_other_owners_item_is_none(owner, cars):
    other = User.objects.create_user(username="other_o", password="pass")
    theirs = _item(other, CollectionType.objects.create(owner=other, name="X"))
    token = _token(owner)
    assert get_executor_item_detail_context(owner, token, theirs.pk) is None
    assert get_executor_item_detail_context(owner, token, 999999) is None


def test_snapshot_scoped_to_activation(owner, cars):
    item = _item(owner, cars, value=Decimal("100"))
    token = _token(owner)
    ctx = get_executor_item_detail_context(owner, token, item.pk)
    assert ctx["snapshot"].market_value == Decimal("100")
    assert ctx["row"]["in_snapshot"] is True

    # A manual snapshot is ignored, even on the same token
    ValuationSnapshot.objects.create(
        item=item,
        item_name=item.name,
        owner=owner,
        token=token,
        snapshot_date=datetime.date.today(),
        market_value=Decimal("999"),
        snapshot_trigger="MANUAL",
    )
    ctx = get_executor_item_detail_context(owner, token, item.pk)
    assert ctx["snapshot"].market_value == Decimal("100")

    # A later activation's snapshot belongs to its own token only
    item.current_market_value = Decimal("200")
    item.save()
    new_token = _token(owner)
    assert get_executor_item_detail_context(owner, token, item.pk)[
        "snapshot"
    ].market_value == Decimal("100")
    assert get_executor_item_detail_context(owner, new_token, item.pk)[
        "snapshot"
    ].market_value == Decimal("200")


def test_added_after_activation_has_no_snapshot(owner, cars):
    token = _token(owner)
    late = _item(owner, cars, "Late", Decimal("5"))
    ctx = get_executor_item_detail_context(owner, token, late.pk)
    assert ctx["snapshot"] is None
    assert ctx["row"]["in_snapshot"] is False


def test_designation_states(owner, cars):
    token = _token(owner)
    plain = _item(owner, cars, "Plain")
    ctx = get_executor_item_detail_context(owner, token, plain.pk)
    assert ctx["row"]["is_unassigned"] is True and ctx["conditional_note"] == ""

    priya = Beneficiary.objects.create(owner=owner, name="Priya", relationship="Child")
    a = BeneficiaryAssignment.objects.create(
        item=plain, beneficiary=priya, conditional_note="  If she is 25  "
    )
    ctx = get_executor_item_detail_context(owner, token, plain.pk)
    assert ctx["row"]["beneficiary_name"] == "Priya"
    assert ctx["row"]["is_unassigned"] is False
    assert ctx["conditional_note"] == "If she is 25"

    a.is_charitable = True
    a.charitable_org = "Red Cross"
    a.save()
    ctx = get_executor_item_detail_context(owner, token, plain.pk)
    assert ctx["row"]["is_charitable"] and ctx["row"]["charitable_org"] == "Red Cross"

    priya.delete()
    BeneficiaryAssignment.objects.filter(pk=a.pk).update(is_charitable=False)
    ctx = get_executor_item_detail_context(owner, token, plain.pk)
    assert ctx["row"]["is_unassigned"] is True


def test_custom_fields_match_owner_rules(owner):
    ct = CollectionType.objects.create(
        owner=owner,
        name="Wine",
        field_schema={
            "fields": [
                {"name": "hidden", "type": "text", "system": True},
                {"name": "blob", "type": "system_json"},
            ]
        },
    )
    item = _item(
        owner,
        ct,
        custom_fields={
            "vintage_year": 1990,
            "hidden": "x",
            "blob": {"a": 1},
            "specs": {"a": 1},
            "features": [1],
            "migrated": True,
            "empty": "",
            "none": None,
        },
    )
    assert get_item_display_custom_fields(item) == [("Vintage Year", 1990)]
    ctx = get_executor_item_detail_context(owner, _token(owner), item.pk)
    assert ctx["custom_fields"] == [("Vintage Year", 1990)]


def test_lists_newest_first_and_query_count(owner, cars, django_assert_num_queries):
    item = _item(owner, cars)
    token = _token(owner)
    for d in (1, 3, 2):
        GenericServiceRecord.objects.create(
            item=item,
            date=datetime.date(2024, 1, d),
            vendor="V",
            description="d",
            total_cost=Decimal("1"),
        )
    for v in (1, 2):
        GenericValuationHistory.objects.create(item=item, value=Decimal(v))
    with django_assert_num_queries(4):
        ctx = get_executor_item_detail_context(owner, token, item.pk)
    assert isinstance(ctx["service_records"], list)
    assert isinstance(ctx["valuation_history"], list)
    assert [r.date.day for r in ctx["service_records"]] == [3, 2, 1]
    assert [v.value for v in ctx["valuation_history"]] == [Decimal(2), Decimal(1)]
