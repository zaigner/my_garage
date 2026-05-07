"""
Unit tests for portfolio_get_yoy_change selector.

Covers:
  - Returns (pct, "snapshot") when a PortfolioSnapshot exists within the ±30-day window
  - Picks the snapshot closest to the target date (latest in the window)
  - Falls back to "purchase_price" when no snapshot but old items exist
  - Returns (None, "none") when no snapshot and no items older than 365 days
  - Returns (None, "none") when old items exist but all have null purchase_price
  - Correct sign: negative pct when current < past
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from my_garage.api.selectors import portfolio_get_yoy_change
from my_garage.models import CollectionType, DynamicCollectionItem, PortfolioSnapshot

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="yoy_user", password="pass")


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Test Collection",
        slug="test-collection-yoy",
    )


def _item(
    user, collection_type, *, market_value=None, purchase_price=None, purchase_date=None
):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Test Item",
        current_market_value=market_value,
        purchase_price=purchase_price,
        purchase_date=purchase_date,
    )


# ---------------------------------------------------------------------------
# Snapshot path
# ---------------------------------------------------------------------------


class TestYoYWithSnapshot:
    def test_positive_growth(self, user, collection_type):
        today = date(2026, 5, 4)
        one_year_ago = today - timedelta(days=365)

        _item(user, collection_type, market_value=Decimal("11000"))
        PortfolioSnapshot.objects.create(
            user=user, date=one_year_ago, total_value=Decimal("10000")
        )

        pct, source = portfolio_get_yoy_change(user, today=today)

        assert source == "snapshot"
        assert pct == Decimal("10.0")

    def test_negative_growth(self, user, collection_type):
        today = date(2026, 5, 4)
        one_year_ago = today - timedelta(days=365)

        _item(user, collection_type, market_value=Decimal("9000"))
        PortfolioSnapshot.objects.create(
            user=user, date=one_year_ago, total_value=Decimal("10000")
        )

        pct, source = portfolio_get_yoy_change(user, today=today)

        assert source == "snapshot"
        assert pct == Decimal("-10.0")

    def test_snapshot_within_30_day_window_is_used(self, user, collection_type):
        today = date(2026, 5, 4)
        snapshot_date = today - timedelta(
            days=365 + 20
        )  # 20 days before exact year ago

        _item(user, collection_type, market_value=Decimal("12000"))
        PortfolioSnapshot.objects.create(
            user=user, date=snapshot_date, total_value=Decimal("10000")
        )

        pct, source = portfolio_get_yoy_change(user, today=today)

        assert source == "snapshot"
        assert pct is not None

    def test_snapshot_outside_30_day_window_is_ignored(self, user, collection_type):
        today = date(2026, 5, 4)
        snapshot_date = today - timedelta(days=365 + 45)  # outside ±30-day window

        _item(user, collection_type, market_value=Decimal("12000"))
        PortfolioSnapshot.objects.create(
            user=user, date=snapshot_date, total_value=Decimal("10000")
        )

        _pct, source = portfolio_get_yoy_change(user, today=today)

        # No snapshot in window — falls back to purchase_price or none
        assert source != "snapshot"

    def test_picks_latest_snapshot_in_window(self, user, collection_type):
        today = date(2026, 5, 4)
        one_year_ago = today - timedelta(days=365)

        _item(user, collection_type, market_value=Decimal("10500"))
        # Two snapshots in window — should use the later one (10000, not 8000)
        PortfolioSnapshot.objects.create(
            user=user,
            date=one_year_ago - timedelta(days=10),
            total_value=Decimal("8000"),
        )
        PortfolioSnapshot.objects.create(
            user=user, date=one_year_ago, total_value=Decimal("10000")
        )

        pct, source = portfolio_get_yoy_change(user, today=today)

        assert source == "snapshot"
        # 10500 vs 10000 = +5%
        assert pct == Decimal("5.0")


# ---------------------------------------------------------------------------
# Purchase-price fallback path
# ---------------------------------------------------------------------------


class TestYoYWithPurchasePriceFallback:
    def test_uses_purchase_price_for_old_items(self, user, collection_type):
        today = date(2026, 5, 4)
        old_purchase_date = today - timedelta(days=400)

        _item(
            user,
            collection_type,
            market_value=Decimal("12000"),
            purchase_price=Decimal("10000"),
            purchase_date=old_purchase_date,
        )

        pct, source = portfolio_get_yoy_change(user, today=today)

        assert source == "purchase_price"
        assert pct == Decimal("20.0")

    def test_ignores_items_bought_within_last_year(self, user, collection_type):
        today = date(2026, 5, 4)
        recent_purchase_date = today - timedelta(days=100)

        _item(
            user,
            collection_type,
            market_value=Decimal("12000"),
            purchase_price=Decimal("10000"),
            purchase_date=recent_purchase_date,
        )

        pct, source = portfolio_get_yoy_change(user, today=today)

        # Item is too new — no old baseline
        assert source == "none"
        assert pct is None


# ---------------------------------------------------------------------------
# No-data path
# ---------------------------------------------------------------------------


class TestYoYNoData:
    def test_no_items_returns_none(self, user):
        pct, source = portfolio_get_yoy_change(user, today=date(2026, 5, 4))
        assert pct is None
        assert source == "none"

    def test_old_items_without_purchase_price_returns_none(self, user, collection_type):
        today = date(2026, 5, 4)
        old_purchase_date = today - timedelta(days=400)

        _item(
            user,
            collection_type,
            market_value=Decimal("12000"),
            purchase_price=None,
            purchase_date=old_purchase_date,
        )

        pct, source = portfolio_get_yoy_change(user, today=today)

        assert source == "none"
        assert pct is None
