"""
Functional tests for Story 3.2: Insights Page NFP Breakdown.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    GenericServiceRecord,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="nfp_insights_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def collection_a(user):
    return CollectionType.objects.create(
        owner=user, name="Watches", slug="watches-insights"
    )


@pytest.fixture
def collection_b(user):
    return CollectionType.objects.create(owner=user, name="Cars", slug="cars-insights")


@pytest.fixture
def items_positive_nfp(user, collection_a):
    item = DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_a,
        name="Rolex",
        purchase_price=Decimal("8000"),
        current_market_value=Decimal("12000"),
    )
    item.refresh_from_db()
    return item


@pytest.fixture
def items_negative_nfp(user, collection_b):
    item = DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_b,
        name="BMW",
        purchase_price=Decimal("40000"),
        current_market_value=Decimal("35000"),
    )
    GenericServiceRecord.objects.create(
        item=item,
        date=datetime.date.today(),
        vendor="Shop",
        description="Oil change",
        category="MAINTENANCE",
        total_cost=Decimal("200"),
    )
    item.refresh_from_db()
    return item


@pytest.fixture
def items_null_market_value(user, collection_a):
    item = DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_a,
        name="Patek Philippe",
        purchase_price=Decimal("25000"),
        current_market_value=None,
    )
    item.refresh_from_db()
    return item


# ---------------------------------------------------------------------------
# NFP KPI card
# ---------------------------------------------------------------------------


class TestInsightsNfpKpiCard:
    def test_nfp_kpi_label_present(self, auth_client, items_positive_nfp):
        response = auth_client.get("/insights/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Net Financial Position" in content

    def test_positive_aggregate_nfp_shown(self, auth_client, items_positive_nfp):
        response = auth_client.get("/insights/")
        content = response.content.decode()
        # NFP = 12000 - 8000 = +4000
        assert "+$4,000" in content

    def test_negative_aggregate_nfp_shown(self, auth_client, items_negative_nfp):
        response = auth_client.get("/insights/")
        content = response.content.decode()
        # NFP = 35000 - (40000 + 200) = -5200
        assert "−$5,200" in content

    def test_no_error_when_no_items(self, auth_client):
        response = auth_client.get("/insights/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Per-category NFP
# ---------------------------------------------------------------------------


class TestInsightsCategoryNfp:
    def test_per_category_nfp_value_shown(
        self, auth_client, items_positive_nfp, items_negative_nfp
    ):
        response = auth_client.get("/insights/")
        content = response.content.decode()
        # Watches: +4000, Cars: -5200
        assert "+$4,000" in content
        assert "−$5,200" in content

    def test_null_market_value_shows_dash(self, auth_client, items_null_market_value):
        response = auth_client.get("/insights/")
        content = response.content.decode()
        assert "—" in content
