"""
Functional tests for the home view year-over-year % change display.

Verifies that the correct context variables reach the template and that
the rendered HTML reflects the right state (positive, negative, no-data).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from my_garage.models import DynamicCollectionItem, PortfolioSnapshot

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

HOME_URL = "/"


def _make_item(
    user, collection_type, *, market_value=None, purchase_price=None, purchase_date=None
):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Test Asset",
        current_market_value=market_value,
        purchase_price=purchase_price,
        purchase_date=purchase_date,
    )


# ---------------------------------------------------------------------------
# Context variable tests
# ---------------------------------------------------------------------------


class TestHomeYoYContext:
    def test_yoy_positive_in_context(self, auth_client, user, automobiles_type):
        today = date.today()
        one_year_ago = today - timedelta(days=365)

        _make_item(user, automobiles_type, market_value=Decimal("11000"))
        PortfolioSnapshot.objects.create(
            user=user, date=one_year_ago, total_value=Decimal("10000")
        )

        response = auth_client.get(HOME_URL)

        assert response.status_code == 200
        assert response.context["yoy_pct_change"] == Decimal("10.0")
        assert response.context["yoy_source"] == "snapshot"

    def test_yoy_negative_in_context(self, auth_client, user, automobiles_type):
        today = date.today()
        one_year_ago = today - timedelta(days=365)

        _make_item(user, automobiles_type, market_value=Decimal("8000"))
        PortfolioSnapshot.objects.create(
            user=user, date=one_year_ago, total_value=Decimal("10000")
        )

        response = auth_client.get(HOME_URL)

        assert response.status_code == 200
        assert response.context["yoy_pct_change"] == Decimal("-20.0")
        assert response.context["yoy_source"] == "snapshot"

    def test_yoy_purchase_price_fallback_in_context(
        self, auth_client, user, automobiles_type
    ):
        today = date.today()
        old_date = today - timedelta(days=400)

        _make_item(
            user,
            automobiles_type,
            market_value=Decimal("12000"),
            purchase_price=Decimal("10000"),
            purchase_date=old_date,
        )

        response = auth_client.get(HOME_URL)

        assert response.status_code == 200
        assert response.context["yoy_pct_change"] == Decimal("20.0")
        assert response.context["yoy_source"] == "purchase_price"

    def test_yoy_none_in_context_when_no_history(
        self, auth_client, user, automobiles_type
    ):
        today = date.today()
        recent_date = today - timedelta(days=30)

        _make_item(
            user,
            automobiles_type,
            market_value=Decimal("12000"),
            purchase_price=Decimal("10000"),
            purchase_date=recent_date,
        )

        response = auth_client.get(HOME_URL)

        assert response.status_code == 200
        assert response.context["yoy_pct_change"] is None
        assert response.context["yoy_source"] == "none"

    def test_yoy_not_in_context_for_anonymous(self):
        from django.test import Client

        response = Client().get(HOME_URL)
        assert response.status_code == 200
        assert "yoy_pct_change" not in response.context


# ---------------------------------------------------------------------------
# Rendered HTML tests
# ---------------------------------------------------------------------------


class TestHomeYoYRendered:
    def test_positive_renders_green_badge(self, auth_client, user, automobiles_type):
        today = date.today()
        PortfolioSnapshot.objects.create(
            user=user, date=today - timedelta(days=365), total_value=Decimal("10000")
        )
        _make_item(user, automobiles_type, market_value=Decimal("11000"))

        response = auth_client.get(HOME_URL)
        content = response.content.decode()

        assert "text-green-400" in content
        assert "+10.0%" in content
        assert "vs last year" in content

    def test_negative_renders_red_badge(self, auth_client, user, automobiles_type):
        today = date.today()
        PortfolioSnapshot.objects.create(
            user=user, date=today - timedelta(days=365), total_value=Decimal("10000")
        )
        _make_item(user, automobiles_type, market_value=Decimal("9000"))

        response = auth_client.get(HOME_URL)
        content = response.content.decode()

        assert "text-red-400" in content
        assert "-10.0%" in content

    def test_purchase_price_fallback_renders_est_label(
        self, auth_client, user, automobiles_type
    ):
        today = date.today()
        _make_item(
            user,
            automobiles_type,
            market_value=Decimal("12000"),
            purchase_price=Decimal("10000"),
            purchase_date=today - timedelta(days=400),
        )

        response = auth_client.get(HOME_URL)
        content = response.content.decode()

        assert "est. vs cost basis" in content

    def test_no_data_renders_tracking_started(self, auth_client, user):
        response = auth_client.get(HOME_URL)
        content = response.content.decode()

        assert "tracking started" in content

    def test_unauthenticated_shows_no_badge(self):
        from django.test import Client

        response = Client().get(HOME_URL)
        content = response.content.decode()

        assert "tracking started" not in content
        assert "vs last year" not in content
        assert "est. vs cost basis" not in content
