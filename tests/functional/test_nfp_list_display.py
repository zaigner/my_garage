"""
Functional tests for Story 2.1: Collection List Mini NFP Breakdown.

Verifies that the collection list page renders the mini financial breakdown
(Cost Basis / Market Value / Net Position) for each item card.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    GenericServiceRecord,
    GenericUpgrade,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="nfp_list_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="NFP List Test",
        slug="nfp-list-test",
    )


@pytest.fixture
def item_with_records(user, collection_type):
    item = DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Test Item With Records",
        purchase_price=Decimal("10000.00"),
        current_market_value=Decimal("14000.00"),
    )
    GenericServiceRecord.objects.create(
        item=item,
        date=datetime.date.today(),
        vendor="Shop",
        description="Service",
        category="MAINTENANCE",
        total_cost=Decimal("500.00"),
    )
    GenericUpgrade.objects.create(
        item=item,
        name="Carbon Kit",
        status="COMPLETED",
        cost=Decimal("800.00"),
    )
    # Signals refresh NFP automatically on create
    item.refresh_from_db()
    return item


@pytest.fixture
def item_no_market_value(user, collection_type):
    item = DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="No Market Value Item",
        purchase_price=Decimal("3000.00"),
        current_market_value=None,
    )
    GenericServiceRecord.objects.create(
        item=item,
        date=datetime.date.today(),
        vendor="Shop",
        description="Storage fee",
        category="MAINTENANCE",
        total_cost=Decimal("25.00"),
    )
    item.refresh_from_db()
    return item


def _list_url(collection_type):
    return reverse(
        "collections:collection_list",
        kwargs={"collection_slug": collection_type.slug},
    )


# ---------------------------------------------------------------------------
# Mini breakdown present
# ---------------------------------------------------------------------------


class TestListMiniNfpBreakdown:
    def test_cost_basis_present_in_list(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_list_url(collection_type))
        assert response.status_code == 200
        content = response.content.decode()
        # cost_basis = 10000 + 500 + 800 = 11300; currency_display → "$11,300"
        assert "$11,300" in content

    def test_market_value_present_in_list(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_list_url(collection_type))
        content = response.content.decode()
        assert "$14,000" in content

    def test_positive_net_position_in_list(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_list_url(collection_type))
        content = response.content.decode()
        # net_position = 14000 - 11300 = +2700
        assert "+$2,700" in content

    def test_negative_net_position_in_list(self, auth_client, collection_type, user):
        item = DynamicCollectionItem.objects.create(
            owner=user,
            collection_type=collection_type,
            name="Underwater Item",
            purchase_price=Decimal("20000.00"),
            current_market_value=Decimal("15000.00"),
        )
        item.refresh_from_db()
        response = auth_client.get(_list_url(collection_type))
        content = response.content.decode()
        assert "−$5,000" in content

    def test_null_market_value_shows_dash_for_net_position(
        self, auth_client, collection_type, item_no_market_value
    ):
        response = auth_client.get(_list_url(collection_type))
        assert response.status_code == 200
        content = response.content.decode()
        assert "—" in content

    def test_cost_basis_shown_even_when_market_value_null(
        self, auth_client, collection_type, item_no_market_value
    ):
        response = auth_client.get(_list_url(collection_type))
        content = response.content.decode()
        # cost_basis = 3000 + 25 = 3025; currency_display → "$3,025"
        assert "$3,025" in content

    def test_aria_label_on_net_position(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_list_url(collection_type))
        content = response.content.decode()
        assert "Net Position" in content

    def test_not_available_aria_label_when_null(
        self, auth_client, collection_type, item_no_market_value
    ):
        response = auth_client.get(_list_url(collection_type))
        content = response.content.decode()
        assert "market value not set" in content.lower()
