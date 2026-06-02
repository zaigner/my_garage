"""
Functional tests for Story 3.1: Home Dashboard Aggregate NFP Card.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext

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
    return User.objects.create_user(username="nfp_home_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Home NFP Test",
        slug="home-nfp-test",
    )


@pytest.fixture
def items_with_nfp(user, collection_type):
    item_a = DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Positive NFP Item",
        purchase_price=Decimal("10000"),
        current_market_value=Decimal("15000"),
    )
    item_b = DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Negative NFP Item",
        purchase_price=Decimal("20000"),
        current_market_value=Decimal("18000"),
    )
    GenericServiceRecord.objects.create(
        item=item_b,
        date=datetime.date.today(),
        vendor="Shop",
        description="Service",
        category="MAINTENANCE",
        total_cost=Decimal("500"),
    )
    # NFP: item_a = +5000, item_b = 18000 - 20500 = -2500 → aggregate = +2500
    item_a.refresh_from_db()
    item_b.refresh_from_db()
    return [item_a, item_b]


@pytest.fixture
def items_no_market_value(user, collection_type):
    item = DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="No Value Item",
        purchase_price=Decimal("5000"),
        current_market_value=None,
    )
    item.refresh_from_db()
    return [item]


# ---------------------------------------------------------------------------
# NFP card present
# ---------------------------------------------------------------------------


class TestHomeNfpCard:
    def test_nfp_section_label_present(self, auth_client, items_with_nfp):
        response = auth_client.get("/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Net Financial Position" in content

    def test_positive_aggregate_nfp_shown(self, auth_client, items_with_nfp):
        response = auth_client.get("/")
        content = response.content.decode()
        # aggregate = +5000 + (-2500) = +2500
        assert "+$2,500" in content

    def test_null_nfp_shows_dash(self, auth_client, items_no_market_value):
        response = auth_client.get("/")
        content = response.content.decode()
        assert "—" in content

    def test_no_error_when_no_items(self, auth_client):
        response = auth_client.get("/")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Query count
# ---------------------------------------------------------------------------


class TestHomeNfpQueryCount:
    def test_nfp_uses_aggregate_not_iteration(self, auth_client, items_with_nfp):
        with CaptureQueriesContext(connection) as ctx:
            auth_client.get("/")

        nfp_queries = [
            q["sql"]
            for q in ctx.captured_queries
            if "net_financial_position" in q["sql"].lower()
            and "sum" in q["sql"].lower()
        ]
        assert len(nfp_queries) == 1, (
            f"Expected 1 NFP aggregate query, got {len(nfp_queries)}: {nfp_queries}"
        )
