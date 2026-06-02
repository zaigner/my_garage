"""
Functional tests for Story 2.2: Item Detail Full Financial Breakdown.

Verifies that the collection item detail page renders the full financial
position card: Purchase Price / Service Costs / Upgrade Costs / Cost Basis /
Market Value / Net Position.
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
    return User.objects.create_user(username="nfp_detail_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="NFP Detail Test",
        slug="nfp-detail-test",
    )


@pytest.fixture
def item_with_records(user, collection_type):
    item = DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Detail Test Item",
        purchase_price=Decimal("44000.00"),
        current_market_value=Decimal("48000.00"),
    )
    # 4 service records totalling $5,200
    for cost in [Decimal("1200"), Decimal("1500"), Decimal("1000"), Decimal("1500")]:
        GenericServiceRecord.objects.create(
            item=item,
            date=datetime.date.today(),
            vendor="Shop",
            description="Service",
            category="MAINTENANCE",
            total_cost=cost,
        )
    # INSTALLED upgrades totalling $3,200
    GenericUpgrade.objects.create(
        item=item, name="Carbon Spoiler", status="COMPLETED", cost=Decimal("1800")
    )
    GenericUpgrade.objects.create(
        item=item, name="Air Filter", status="COMPLETED", cost=Decimal("1400")
    )
    # WISHLIST upgrade that should NOT count
    GenericUpgrade.objects.create(
        item=item, name="Wheels", status="WISHLIST", cost=Decimal("5000")
    )
    item.refresh_from_db()
    return item


@pytest.fixture
def item_no_market_value(user, collection_type):
    item = DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Pending Valuation Item",
        purchase_price=Decimal("5000.00"),
        current_market_value=None,
    )
    item.refresh_from_db()
    return item


def _detail_url(collection_type, item):
    return reverse(
        "collections:collection_item_detail",
        kwargs={"collection_slug": collection_type.slug, "item_id": item.id},
    )


# ---------------------------------------------------------------------------
# Full breakdown present
# ---------------------------------------------------------------------------


class TestDetailFullNfpBreakdown:
    def test_detail_page_returns_200(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_detail_url(collection_type, item_with_records))
        assert response.status_code == 200

    def test_purchase_price_in_breakdown(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_detail_url(collection_type, item_with_records))
        content = response.content.decode()
        assert "$44,000" in content

    def test_service_costs_total_in_breakdown(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_detail_url(collection_type, item_with_records))
        content = response.content.decode()
        # service total = 1200 + 1500 + 1000 + 1500 = $5,200
        assert "$5,200" in content

    def test_completed_upgrade_costs_in_breakdown(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_detail_url(collection_type, item_with_records))
        content = response.content.decode()
        # completed upgrade total = 1800 + 1400 = $3,200
        assert "$3,200" in content

    def test_wishlist_upgrade_not_in_cost_basis(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_detail_url(collection_type, item_with_records))
        content = response.content.decode()
        # cost_basis = 44000 + 5200 + 3200 = 52400; wishlist $5000 not in basis
        assert "$52,400" in content

    def test_net_position_in_breakdown(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_detail_url(collection_type, item_with_records))
        content = response.content.decode()
        # net_position = 48000 - 52400 = -4400
        assert "−$4,400" in content

    def test_financial_position_section_present(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_detail_url(collection_type, item_with_records))
        content = response.content.decode()
        assert "Financial Position" in content

    def test_section_labels_present(
        self, auth_client, collection_type, item_with_records
    ):
        response = auth_client.get(_detail_url(collection_type, item_with_records))
        content = response.content.decode()
        assert "Service Costs" in content
        assert "Upgrades" in content
        assert "Cost Basis" in content
        assert "Net Position" in content


# ---------------------------------------------------------------------------
# Null market value — tooltip shown
# ---------------------------------------------------------------------------


class TestDetailNullMarketValue:
    def test_dash_shown_for_net_position(
        self, auth_client, collection_type, item_no_market_value
    ):
        response = auth_client.get(_detail_url(collection_type, item_no_market_value))
        content = response.content.decode()
        assert "—" in content

    def test_tooltip_text_present(
        self, auth_client, collection_type, item_no_market_value
    ):
        response = auth_client.get(_detail_url(collection_type, item_no_market_value))
        content = response.content.decode()
        assert "valuation" in content.lower()
