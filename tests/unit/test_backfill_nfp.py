"""
Unit tests for Story 1.2: backfill_nfp management command.

Covers:
  - Multi-item backfill sets net_financial_position correctly
  - Items with null current_market_value remain null after backfill
  - Empty database runs without error and reports zero processed
  - --dry-run does not write any values to the database
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

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
    return User.objects.create_user(username="backfill_test_user", password="pass")


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Backfill Test Collection",
        slug="backfill-test-collection",
    )


def _item(user, ct, *, purchase_price, market_value):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=ct,
        name="Backfill Item",
        purchase_price=purchase_price,
        current_market_value=market_value,
    )


def _service(item, cost):
    return GenericServiceRecord.objects.create(
        item=item,
        date=datetime.date.today(),
        vendor="Vendor",
        description="Service",
        category="MAINTENANCE",
        total_cost=cost,
    )


def _upgrade(item, cost, status="COMPLETED"):
    return GenericUpgrade.objects.create(
        item=item,
        name="Upgrade",
        status=status,
        cost=cost,
    )


# ---------------------------------------------------------------------------
# Multi-item backfill
# ---------------------------------------------------------------------------


class TestBackfillNfp:
    def test_sets_nfp_for_multiple_items(self, user, collection_type):
        item_a = _item(
            user,
            collection_type,
            purchase_price=Decimal("10000"),
            market_value=Decimal("15000"),
        )
        item_b = _item(
            user,
            collection_type,
            purchase_price=Decimal("5000"),
            market_value=Decimal("4000"),
        )
        _service(item_a, Decimal("500"))
        _upgrade(item_b, Decimal("200"), status="COMPLETED")

        # Wipe cached values that signals wrote so we can test the backfill
        DynamicCollectionItem.objects.update(net_financial_position=None)

        out = StringIO()
        call_command("backfill_nfp", stdout=out)

        item_a.refresh_from_db()
        item_b.refresh_from_db()

        assert item_a.net_financial_position == Decimal("4500")  # 15000-(10000+500)
        assert item_b.net_financial_position == Decimal("-1200")  # 4000-(5000+200)

    def test_null_market_value_stays_null(self, user, collection_type):
        item = _item(
            user,
            collection_type,
            purchase_price=Decimal("3000"),
            market_value=None,
        )
        DynamicCollectionItem.objects.update(net_financial_position=None)

        call_command("backfill_nfp", stdout=StringIO())

        item.refresh_from_db()
        assert item.net_financial_position is None

    def test_empty_database_exits_without_error(self, db):
        out = StringIO()
        call_command("backfill_nfp", stdout=out)
        assert "0" in out.getvalue()

    def test_output_reports_count(self, user, collection_type):
        _item(
            user,
            collection_type,
            purchase_price=Decimal("1000"),
            market_value=Decimal("1200"),
        )
        _item(
            user,
            collection_type,
            purchase_price=Decimal("2000"),
            market_value=Decimal("2500"),
        )
        DynamicCollectionItem.objects.update(net_financial_position=None)

        out = StringIO()
        call_command("backfill_nfp", stdout=out)

        assert "2" in out.getvalue()


# ---------------------------------------------------------------------------
# --dry-run
# ---------------------------------------------------------------------------


class TestBackfillNfpDryRun:
    def test_dry_run_does_not_write(self, user, collection_type):
        item = _item(
            user,
            collection_type,
            purchase_price=Decimal("1000"),
            market_value=Decimal("2000"),
        )
        DynamicCollectionItem.objects.update(net_financial_position=None)

        call_command("backfill_nfp", "--dry-run", stdout=StringIO())

        item.refresh_from_db()
        assert item.net_financial_position is None

    def test_dry_run_output_mentions_dry_run(self, user, collection_type):
        _item(
            user,
            collection_type,
            purchase_price=Decimal("1000"),
            market_value=Decimal("2000"),
        )
        DynamicCollectionItem.objects.update(net_financial_position=None)

        out = StringIO()
        call_command("backfill_nfp", "--dry-run", stdout=out)

        assert "dry" in out.getvalue().lower()
