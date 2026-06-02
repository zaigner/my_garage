"""
Unit tests for Story 1.1: NFP Calculation, Cached Field, and Signal Handlers.

Covers:
  - get_item_nfp_breakdown: nominal, null market value, zero records,
    zero upgrades, non-COMPLETED upgrade excluded from cost basis
  - refresh_item_nfp: field saved, null market value stores null
  - post_delete signal on GenericServiceRecord refreshes NFP
  - post_delete signal on GenericUpgrade (COMPLETED) reduces NFP
  - GenericUpgrade via content_type/object_id path triggers NFP refresh
  - nfp_display template filter: positive, negative, null, zero
  - nfp_color_class template filter: correct Tailwind class returned
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from my_garage.api.selectors import get_item_nfp_breakdown
from my_garage.api.services import refresh_item_nfp
from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    GenericServiceRecord,
    GenericUpgrade,
)
from my_garage.templatetags.my_garage_extras import nfp_color_class, nfp_display

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="nfp_test_user", password="pass")


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="NFP Test Collection",
        slug="nfp-test-collection",
    )


@pytest.fixture
def item(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Test Item",
        purchase_price=Decimal("10000.00"),
        current_market_value=Decimal("14000.00"),
    )


@pytest.fixture
def item_no_market_value(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="No Market Value Item",
        purchase_price=Decimal("5000.00"),
        current_market_value=None,
    )


def _service_record(item, cost):
    from datetime import date

    return GenericServiceRecord.objects.create(
        item=item,
        date=date.today(),
        vendor="Test Vendor",
        description="Test service",
        category="MAINTENANCE",
        total_cost=cost,
    )


def _upgrade(item, cost, status="COMPLETED"):
    return GenericUpgrade.objects.create(
        item=item,
        name="Test Upgrade",
        status=status,
        cost=cost,
    )


# ---------------------------------------------------------------------------
# get_item_nfp_breakdown — selector
# ---------------------------------------------------------------------------


class TestGetItemNfpBreakdown:
    def test_nominal_case(self, item):
        _service_record(item, Decimal("1000.00"))
        _service_record(item, Decimal("500.00"))
        _upgrade(item, Decimal("800.00"), status="COMPLETED")

        breakdown = get_item_nfp_breakdown(item)

        assert breakdown["purchase_price"] == Decimal("10000.00")
        assert breakdown["service_total"] == Decimal("1500.00")
        assert breakdown["upgrade_total"] == Decimal("800.00")
        assert breakdown["cost_basis"] == Decimal("12300.00")
        assert breakdown["market_value"] == Decimal("14000.00")
        assert breakdown["net_position"] == Decimal("1700.00")

    def test_null_market_value_returns_null_net_position(self, item_no_market_value):
        breakdown = get_item_nfp_breakdown(item_no_market_value)

        assert breakdown["market_value"] is None
        assert breakdown["net_position"] is None

    def test_zero_service_records(self, item):
        breakdown = get_item_nfp_breakdown(item)

        assert breakdown["service_total"] == Decimal("0.00")
        assert breakdown["net_position"] == Decimal("4000.00")  # 14000 - 10000

    def test_zero_upgrades(self, item):
        _service_record(item, Decimal("500.00"))

        breakdown = get_item_nfp_breakdown(item)

        assert breakdown["upgrade_total"] == Decimal("0.00")
        assert breakdown["cost_basis"] == Decimal("10500.00")

    def test_non_completed_upgrade_excluded(self, item):
        _upgrade(item, Decimal("2000.00"), status="WISHLIST")
        _upgrade(item, Decimal("1500.00"), status="ORDERED")
        _upgrade(item, Decimal("1000.00"), status="IN_PROGRESS")
        _upgrade(item, Decimal("500.00"), status="CANCELLED")
        _upgrade(item, Decimal("300.00"), status="COMPLETED")

        breakdown = get_item_nfp_breakdown(item)

        assert breakdown["upgrade_total"] == Decimal("300.00")
        assert breakdown["cost_basis"] == Decimal("10300.00")

    def test_null_purchase_price_treats_as_zero(self, user, collection_type):
        item = DynamicCollectionItem.objects.create(
            owner=user,
            collection_type=collection_type,
            name="No Purchase Price",
            purchase_price=None,
            current_market_value=Decimal("5000.00"),
        )
        breakdown = get_item_nfp_breakdown(item)

        assert breakdown["purchase_price"] is None
        assert breakdown["cost_basis"] == Decimal("0.00")
        assert breakdown["net_position"] == Decimal("5000.00")


# ---------------------------------------------------------------------------
# refresh_item_nfp — service
# ---------------------------------------------------------------------------


class TestRefreshItemNfp:
    def test_saves_net_financial_position(self, item):
        _service_record(item, Decimal("500.00"))

        refresh_item_nfp(item)
        item.refresh_from_db()

        assert item.net_financial_position == Decimal("3500.00")  # 14000 - 10000 - 500

    def test_saves_total_cost_basis(self, item):
        _service_record(item, Decimal("500.00"))
        _upgrade(item, Decimal("200.00"), status="COMPLETED")

        refresh_item_nfp(item)
        item.refresh_from_db()

        assert item.total_cost_basis == Decimal("10700.00")  # 10000 + 500 + 200

    def test_null_market_value_stores_null_nfp_but_cost_basis(
        self, item_no_market_value
    ):
        _service_record(item_no_market_value, Decimal("200.00"))

        refresh_item_nfp(item_no_market_value)
        item_no_market_value.refresh_from_db()

        assert item_no_market_value.net_financial_position is None
        assert item_no_market_value.total_cost_basis == Decimal("5200.00")  # 5000 + 200

    def test_only_updates_nfp_fields(self, item):
        original_name = item.name

        refresh_item_nfp(item)
        item.refresh_from_db()

        assert item.name == original_name


# ---------------------------------------------------------------------------
# Signal: GenericServiceRecord post_save / post_delete
# ---------------------------------------------------------------------------


class TestItemSaveSignal:
    def test_item_create_sets_nfp(self, user, collection_type):
        item = DynamicCollectionItem.objects.create(
            owner=user,
            collection_type=collection_type,
            name="New Item",
            purchase_price=Decimal("5000.00"),
            current_market_value=Decimal("7000.00"),
        )
        item.refresh_from_db()
        assert item.net_financial_position == Decimal("2000.00")
        assert item.total_cost_basis == Decimal("5000.00")

    def test_item_update_market_value_refreshes_nfp(self, item):
        item.current_market_value = Decimal("20000.00")
        item.save(update_fields=["current_market_value"])
        item.refresh_from_db()
        assert item.net_financial_position == Decimal("10000.00")  # 20000 - 10000

    def test_nfp_save_does_not_recurse(self, item):
        # Loop guard in handle_item_change skips when update_fields == NFP fields.
        # Without it, refresh_item_nfp → save → signal → refresh → infinite loop.
        from my_garage.api.services import refresh_item_nfp

        refresh_item_nfp(item)  # Should not raise RecursionError


class TestServiceRecordSignal:
    def test_post_save_refreshes_nfp(self, item):
        item.net_financial_position = None
        item.save(update_fields=["net_financial_position"])

        _service_record(item, Decimal("1000.00"))
        item.refresh_from_db()

        assert item.net_financial_position == Decimal("3000.00")  # 14000 - 10000 - 1000

    def test_post_delete_refreshes_nfp(self, item):
        record = _service_record(item, Decimal("2000.00"))
        item.refresh_from_db()
        assert item.net_financial_position == Decimal("2000.00")  # 14000 - 10000 - 2000

        record.delete()
        item.refresh_from_db()

        assert item.net_financial_position == Decimal("4000.00")  # 14000 - 10000

    def test_stale_value_not_present_after_delete(self, item):
        record = _service_record(item, Decimal("1000.00"))
        item.refresh_from_db()
        stale = item.net_financial_position

        record.delete()
        item.refresh_from_db()

        assert item.net_financial_position != stale


# ---------------------------------------------------------------------------
# Signal: GenericUpgrade post_save / post_delete
# ---------------------------------------------------------------------------


class TestUpgradeSignal:
    def test_completed_upgrade_post_save_refreshes_nfp(self, item):
        _upgrade(item, Decimal("1000.00"), status="COMPLETED")
        item.refresh_from_db()

        assert item.net_financial_position == Decimal("3000.00")  # 14000 - 10000 - 1000

    def test_wishlist_upgrade_does_not_affect_nfp(self, item):
        initial_nfp = Decimal("4000.00")  # 14000 - 10000
        refresh_item_nfp(item)

        _upgrade(item, Decimal("5000.00"), status="WISHLIST")
        item.refresh_from_db()

        assert item.net_financial_position == initial_nfp

    def test_post_delete_completed_upgrade_reduces_nfp(self, item):
        upgrade = _upgrade(item, Decimal("2000.00"), status="COMPLETED")
        item.refresh_from_db()
        assert item.net_financial_position == Decimal("2000.00")

        upgrade.delete()
        item.refresh_from_db()

        assert item.net_financial_position == Decimal("4000.00")

    def test_status_change_to_completed_triggers_nfp_recalc(self, item):
        upgrade = _upgrade(item, Decimal("1000.00"), status="WISHLIST")
        refresh_item_nfp(item)
        item.refresh_from_db()
        nfp_before = item.net_financial_position

        upgrade.status = "COMPLETED"
        upgrade.save()
        item.refresh_from_db()

        assert item.net_financial_position == nfp_before - Decimal("1000.00")


# ---------------------------------------------------------------------------
# Signal: GenericUpgrade via content_type / object_id path (AC: 7)
# ---------------------------------------------------------------------------


class TestUpgradeGenericFKSignal:
    def test_generic_fk_upgrade_refreshes_nfp(self, item):
        ct = ContentType.objects.get_for_model(DynamicCollectionItem)
        upgrade = GenericUpgrade.objects.create(
            item=None,
            content_type=ct,
            object_id=item.pk,
            name="GFK Upgrade",
            status="COMPLETED",
            cost=Decimal("500.00"),
        )
        item.refresh_from_db()

        assert item.net_financial_position == Decimal("3500.00")  # 14000 - 10000 - 500

        upgrade.delete()
        item.refresh_from_db()

        assert item.net_financial_position == Decimal("4000.00")


# ---------------------------------------------------------------------------
# nfp_display template filter
# ---------------------------------------------------------------------------


class TestNfpDisplayFilter:
    def test_positive_value(self):
        result = nfp_display(Decimal("4450.00"))
        assert result == "+$4,450"

    def test_negative_value(self):
        result = nfp_display(Decimal("-4400.00"))
        assert result == "−$4,400"

    def test_null_returns_dash(self):
        result = nfp_display(None)
        assert result == "—"

    def test_zero_returns_dash(self):
        result = nfp_display(Decimal("0.00"))
        assert result == "—"

    def test_large_value_formatted_with_commas(self):
        result = nfp_display(Decimal("12345.67"))
        assert result == "+$12,346"

    def test_negative_large_value(self):
        result = nfp_display(Decimal("-12345.67"))
        assert result == "−$12,346"


# ---------------------------------------------------------------------------
# nfp_color_class template filter
# ---------------------------------------------------------------------------


class TestNfpColorClassFilter:
    def test_positive_returns_green(self):
        assert nfp_color_class(Decimal("100.00")) == "text-green-400"

    def test_negative_returns_red(self):
        assert nfp_color_class(Decimal("-100.00")) == "text-red-400"

    def test_null_returns_gray(self):
        assert nfp_color_class(None) == "text-gray-400"

    def test_zero_returns_gray(self):
        assert nfp_color_class(Decimal("0.00")) == "text-gray-400"
