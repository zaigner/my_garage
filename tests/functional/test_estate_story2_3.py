"""Functional tests for Story 2.3: executor portfolio view."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.api.services import activate_estate_plan
from my_garage.models import (
    Beneficiary,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateAccessLog,
    EstateAccessToken,
)

User = get_user_model()
pytestmark = pytest.mark.django_db

PORTAL = "/estate/portal/"
DASH = "/estate/portal/dashboard/"


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="estate_2_3", password="pass", first_name="Marcus", last_name="Hale"
    )


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


def _executor_client(owner):
    client = Client()
    assert client.post(PORTAL, {"code": activate_estate_plan(owner)}).status_code == 302
    return client


class TestPortfolioPage:
    def test_header_rows_and_summary(self, owner, cars):
        porsche = _item(owner, cars, "1972 Porsche 911", Decimal("150000"))
        priya = Beneficiary.objects.create(
            owner=owner, name="Priya", relationship="Child"
        )
        BeneficiaryAssignment.objects.create(item=porsche, beneficiary=priya)
        client = _executor_client(owner)

        r = client.get(DASH)
        body = r.content.decode()
        assert r.status_code == 200
        assert "Marcus Hale" in body
        issued = EstateAccessToken.objects.get(is_active=True).issued_at
        assert f"Estate access activated {issued:%B} {issued.day}, {issued:%Y}" in body
        assert "1972 Porsche 911" in body and "Cars" in body and "Priya" in body
        assert "$150,000" in body
        assert ">Items<" in body and ">1<" in body

    def test_username_when_no_full_name(self, cars):
        plain = User.objects.create_user(username="plain_owner", password="pass")
        r = _executor_client(plain).get(DASH)
        assert "plain_owner" in r.content.decode()

    def test_nulls_render_as_em_dash_not_zero(self, owner, cars):
        _item(owner, cars, "Unvalued Car")
        body = _executor_client(owner).get(DASH).content.decode()
        assert "—" in body and "$0" not in body

    def test_unassigned_badge_and_probate_notice(self, owner, cars):
        _item(owner, cars, "BMW M3")
        body = _executor_client(owner).get(DASH).content.decode()
        assert "Unassigned" in body
        assert "1 asset has no beneficiary designation." in body
        assert "probate process" in body

    def test_no_probate_notice_when_all_assigned(self, owner, cars):
        item = _item(owner, cars, "Assigned Car")
        BeneficiaryAssignment.objects.create(
            item=item, is_charitable=True, charitable_org="Red Cross"
        )
        body = _executor_client(owner).get(DASH).content.decode()
        assert "Red Cross" in body and "(charitable)" in body
        assert "probate process" not in body

    def test_item_added_after_activation_is_listed(self, owner, cars):
        client = _executor_client(owner)
        _item(owner, cars, "Late Addition", Decimal("5000"))
        body = client.get(DASH).content.decode()
        assert "Late Addition" in body and "$5,000" in body

    def test_partial_delta_footnote(self, owner, cars):
        _item(owner, cars, "Valued", Decimal("100"))
        _item(owner, cars, "Unvalued")
        body = _executor_client(owner).get(DASH).content.decode()
        assert "Across 1 of 2 items valued at both dates" in body

    def test_other_owners_items_hidden(self, owner, cars):
        other = User.objects.create_user(username="other_2_3", password="pass")
        _item(
            other, CollectionType.objects.create(owner=other, name="Art"), "Not Yours"
        )
        body = _executor_client(owner).get(DASH).content.decode()
        assert "Not Yours" not in body

    def test_empty_portfolio(self, owner):
        body = _executor_client(owner).get(DASH).content.decode()
        assert "No assets are recorded in this estate." in body


class TestPortalViewLog:
    def test_get_logs_one_portal_view(self, owner, cars):
        client = _executor_client(owner)
        client.get(DASH)
        log = EstateAccessLog.objects.get(event="PORTAL_VIEW")
        assert log.owner == owner
        assert log.token == EstateAccessToken.objects.get(is_active=True)

    def test_head_does_not_log(self, owner):
        client = _executor_client(owner)
        assert client.head(DASH).status_code == 200
        assert not EstateAccessLog.objects.filter(event="PORTAL_VIEW").exists()


class TestSessionEnd:
    def test_ended_session_redirects_without_error(self, owner, cars):
        client = _executor_client(owner)
        session = client.session
        session.flush()
        r = client.get(DASH)
        assert r.status_code == 302 and r["Location"] == PORTAL


class TestRenderedEdgeCases:
    def test_zero_delta_and_zero_value_show_dollar_zero(self, owner, cars):
        _item(owner, cars, "Worthless", Decimal("0"))
        body = _executor_client(owner).get(DASH).content.decode()
        assert body.count("$0") >= 3  # value at activation, current value, change

    def test_negative_delta(self, owner, cars):
        item = _item(owner, cars, "Depreciating", Decimal("1000"))
        client = _executor_client(owner)
        item.current_market_value = Decimal("400")
        item.save()
        assert "−$600" in client.get(DASH).content.decode()

    def test_charitable_without_org_name(self, owner, cars):
        item = _item(owner, cars, "Gift")
        BeneficiaryAssignment.objects.create(item=item, is_charitable=True)
        assert (
            "Charitable bequest" in _executor_client(owner).get(DASH).content.decode()
        )

    def test_deleted_beneficiary_shows_unassigned(self, owner, cars):
        gone = Beneficiary.objects.create(
            owner=owner, name="Gone", relationship="Friend"
        )
        item = _item(owner, cars, "Orphaned")
        BeneficiaryAssignment.objects.create(item=item, beneficiary=gone)
        gone.delete()
        body = _executor_client(owner).get(DASH).content.decode()
        assert "Unassigned" in body and ">Gone<" not in body

    def test_plural_probate_notice(self, owner, cars):
        _item(owner, cars, "One")
        _item(owner, cars, "Two")
        body = _executor_client(owner).get(DASH).content.decode()
        assert "2 assets have no beneficiary designation." in body
        assert "They will need to be handled" in body

    def test_added_after_activation_label_and_counts(self, owner, cars):
        _item(owner, cars, "Original", Decimal("100"))
        client = _executor_client(owner)
        _item(owner, cars, "Newcomer", Decimal("50"))
        body = client.get(DASH).content.decode()
        assert "Added after activation" in body
        assert "1 of 2 items valued" in body
