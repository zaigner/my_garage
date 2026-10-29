"""Unit tests for the shared estate helpers (Epic 3 retro item 11)."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from my_garage.api.estate_selectors import (
    activation_snapshots,
    designated_assignment_q,
    get_activation_snapshot,
    get_beneficiary_assignments,
    get_executor_beneficiary,
    get_executor_beneficiary_links,
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
    ValuationSnapshot,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_user(username="shared_owner", password="pass")


@pytest.fixture
def other():
    return User.objects.create_user(username="shared_other", password="pass")


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


@pytest.fixture
def other_cars(other):
    return CollectionType.objects.create(owner=other, name="Other cars")


@pytest.fixture
def ann(owner):
    return Beneficiary.objects.create(owner=owner, name="Ann", relationship="Child")


def _item(owner, ct, name, value=None):
    return DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name, current_market_value=value
    )


def _assign(item, beneficiary, charitable=False):
    return BeneficiaryAssignment.objects.create(
        item=item,
        beneficiary=beneficiary,
        is_charitable=charitable,
        charitable_org="Org" if charitable else "",
    )


def _activate(owner):
    activate_estate_plan(owner)
    return EstateAccessToken.objects.get(owner=owner, is_active=True)


class TestDesignatedAssignmentQ:
    def test_keeps_only_own_non_charitable_active_items(
        self, owner, other, cars, other_cars, ann
    ):
        kept = _assign(_item(owner, cars, "Kept"), ann)
        _assign(_item(owner, cars, "Charity"), ann, charitable=True)
        hidden = CollectionType.objects.create(owner=owner, name="Hidden")
        _assign(_item(owner, hidden, "Soft-deleted"), ann)
        hidden.is_active = False
        hidden.save()
        # Only reachable through the ORM: owner's beneficiary, other's item
        _assign(_item(other, other_cars, "Cross-owner"), ann)

        rows = BeneficiaryAssignment.objects.filter(designated_assignment_q(owner))
        assert list(rows) == [kept]

    def test_prefix_reaches_through_a_relation(
        self, owner, other, cars, other_cars, ann
    ):
        bob = Beneficiary.objects.create(owner=owner, name="Bob", relationship="Son")
        _assign(_item(owner, cars, "Ann car"), ann)
        _assign(_item(other, other_cars, "Bob cross-owner"), bob)

        found = Beneficiary.objects.filter(
            designated_assignment_q(owner, "assignments__")
        )
        assert list(found) == [ann]


class TestCrossOwnerAssignment:
    """A cross-owner assignment is not counted or shown anywhere."""

    @pytest.fixture
    def setup(self, owner, other, cars, other_cars, ann):
        own = _item(owner, cars, "Ann own car")
        _assign(own, ann)
        cross = _item(other, other_cars, "Other owner's car")
        _assign(cross, ann)
        bob = Beneficiary.objects.create(owner=owner, name="Bob", relationship="Son")
        _assign(_item(other, other_cars, "Bob cross-owner"), bob)
        return {"own": own, "cross": cross, "bob": bob}

    def test_executor_list(self, owner, ann, setup):
        token = _activate(owner)
        rows = get_executor_beneficiary_links(owner, token)
        assert [r["beneficiary"] for r in rows] == [ann]
        assert rows[0]["item_count"] == 1

    def test_get_executor_beneficiary(self, owner, ann, setup):
        assert get_executor_beneficiary(owner, setup["bob"].pk) is None
        found = get_executor_beneficiary(owner, ann.pk)
        assert found == ann
        assert found.item_count == 1

    def test_beneficiary_portal(self, owner, ann, setup):
        token = _activate(owner)
        link = claim_beneficiary_link(issue_beneficiary_link(ann, token))
        assert [a.item for a in get_beneficiary_assignments(link)] == [setup["own"]]


class TestActivationSnapshot:
    def test_newest_row_of_the_given_token(self, owner, cars):
        item = _item(owner, cars, "911", Decimal("100"))
        first = _activate(owner)
        second_row = ValuationSnapshot.objects.create(
            item=item,
            item_name=item.name,
            owner=owner,
            token=first,
            snapshot_date=datetime.date.today(),
            market_value=Decimal("150"),
            snapshot_trigger="ESTATE_ACTIVATION",
        )
        assert get_activation_snapshot(owner, first, item) == second_row

    def test_newer_snapshot_under_another_token_is_not_picked(self, owner, cars):
        item = _item(owner, cars, "911", Decimal("100"))
        first = _activate(owner)
        item.current_market_value = Decimal("200")
        item.save()
        second = _activate(owner)

        assert get_activation_snapshot(owner, first, item).market_value == Decimal(
            "100"
        )
        assert get_activation_snapshot(owner, second, item).market_value == Decimal(
            "200"
        )

    def test_ignores_manual_and_other_owner_rows(self, owner, other, cars):
        item = _item(owner, cars, "911", Decimal("100"))
        token = _activate(owner)
        for row_owner, trigger in ((owner, "MANUAL"), (other, "ESTATE_ACTIVATION")):
            ValuationSnapshot.objects.create(
                item=item,
                item_name=item.name,
                owner=row_owner,
                token=token,
                snapshot_date=datetime.date.today(),
                market_value=Decimal("999"),
                snapshot_trigger=trigger,
            )
        assert get_activation_snapshot(owner, token, item).market_value == Decimal(
            "100"
        )
        assert [s.market_value for s in activation_snapshots(owner, token)] == [
            Decimal("100")
        ]

    def test_none_for_an_item_added_after_activation(self, owner, cars):
        token = _activate(owner)
        late = _item(owner, cars, "Late", Decimal("5"))
        assert get_activation_snapshot(owner, token, late) is None
