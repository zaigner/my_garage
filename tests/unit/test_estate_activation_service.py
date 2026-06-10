"""
Unit tests for Story 2.1: activate_estate_plan service.

Covers:
  - Token generation returns a non-empty string
  - Stored hash is SHA-256 of the raw token (not the raw token itself)
  - ValuationSnapshot records created for all items (bulk_create count)
  - Reactivation deactivates old token and creates a new one
  - Items with null market_value / purchase_price produce null snapshot fields
  - equity = None when either value is None
  - equity = market_value - cost_basis when both present
"""

from __future__ import annotations

import hashlib
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from my_garage.api.services import activate_estate_plan
from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    EstateAccessToken,
    ValuationSnapshot,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(username="estate_user_2_1", password="pass")


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Watches",
        slug="watches",
        field_schema=[],
        list_display_fields=[],
    )


@pytest.fixture
def item_with_values(user, collection_type):
    # Signal recomputes total_cost_basis from purchase_price (no services/upgrades)
    # so purchase_price IS the cost_basis after save
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Rolex Submariner",
        purchase_price=Decimal("8500.00"),
        current_market_value=Decimal("11000.00"),
    )


@pytest.fixture
def item_no_values(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Unvalued Watch",
        purchase_price=None,
        current_market_value=None,
        total_cost_basis=None,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestActivateEstatePlanTokenGeneration:
    def test_returns_non_empty_string(self, user):
        raw = activate_estate_plan(user)
        assert isinstance(raw, str)
        assert len(raw) > 0

    def test_token_hash_is_sha256_of_raw(self, user):
        raw = activate_estate_plan(user)
        token = EstateAccessToken.objects.get(owner=user, is_active=True)
        expected_hash = hashlib.sha256(raw.encode()).hexdigest()
        assert token.token_hash == expected_hash

    def test_raw_token_not_stored_as_hash(self, user):
        raw = activate_estate_plan(user)
        token = EstateAccessToken.objects.get(owner=user, is_active=True)
        assert token.token_hash != raw

    def test_token_is_active(self, user):
        activate_estate_plan(user)
        token = EstateAccessToken.objects.get(owner=user, is_active=True)
        assert token.is_active is True

    def test_token_hash_length_is_64(self, user):
        activate_estate_plan(user)
        token = EstateAccessToken.objects.get(owner=user, is_active=True)
        assert len(token.token_hash) == 64  # SHA-256 hex = 64 chars


class TestActivateEstatePlanSnapshots:
    def test_snapshot_created_for_each_item(
        self, user, item_with_values, item_no_values
    ):
        activate_estate_plan(user)
        count = ValuationSnapshot.objects.filter(owner=user).count()
        assert count == 2

    def test_snapshot_values_stored_for_valued_item(self, user, item_with_values):
        activate_estate_plan(user)
        snap = ValuationSnapshot.objects.get(owner=user, item=item_with_values)
        assert snap.market_value == Decimal("11000.00")
        assert snap.cost_basis == Decimal("8500.00")  # signal sets from purchase_price

    def test_snapshot_equity_computed_when_both_values_present(
        self, user, item_with_values
    ):
        activate_estate_plan(user)
        snap = ValuationSnapshot.objects.get(owner=user, item=item_with_values)
        assert snap.equity == Decimal("11000.00") - Decimal("8500.00")  # 2500.00

    def test_snapshot_nulls_for_unvalued_item(self, user, item_no_values):
        activate_estate_plan(user)
        snap = ValuationSnapshot.objects.get(owner=user, item=item_no_values)
        assert snap.market_value is None
        assert snap.cost_basis is None
        assert snap.equity is None

    def test_snapshot_trigger_is_estate_activation(self, user, item_with_values):
        activate_estate_plan(user)
        snap = ValuationSnapshot.objects.get(owner=user, item=item_with_values)
        assert snap.snapshot_trigger == "ESTATE_ACTIVATION"

    def test_no_exception_when_portfolio_is_empty(self, user):
        raw = activate_estate_plan(user)
        assert isinstance(raw, str)
        assert ValuationSnapshot.objects.filter(owner=user).count() == 0

    def test_snapshot_equity_none_when_market_value_missing(
        self, user, collection_type
    ):
        # market_value=None → equity=None even when cost_basis is set
        item = DynamicCollectionItem.objects.create(
            owner=user,
            collection_type=collection_type,
            name="No Market Value",
            current_market_value=None,
            purchase_price=Decimal("500.00"),
        )
        activate_estate_plan(user)
        snap = ValuationSnapshot.objects.get(owner=user, item=item)
        assert snap.equity is None

    def test_snapshot_equity_none_when_cost_basis_missing(self, user, collection_type):
        # purchase_price=None → cost_basis=None in snapshot → equity=None
        item = DynamicCollectionItem.objects.create(
            owner=user,
            collection_type=collection_type,
            name="No Cost Basis",
            current_market_value=Decimal("1000.00"),
            purchase_price=None,
        )
        activate_estate_plan(user)
        snap = ValuationSnapshot.objects.get(owner=user, item=item)
        assert snap.equity is None


class TestActivateEstatePlanReactivation:
    def test_reactivation_deactivates_old_token(self, user):
        first_raw = activate_estate_plan(user)
        first_hash = hashlib.sha256(first_raw.encode()).hexdigest()

        activate_estate_plan(user)

        old_token = EstateAccessToken.objects.filter(token_hash=first_hash).first()
        assert old_token is not None
        assert old_token.is_active is False

    def test_reactivation_creates_new_active_token(self, user):
        activate_estate_plan(user)
        second_raw = activate_estate_plan(user)
        second_hash = hashlib.sha256(second_raw.encode()).hexdigest()

        new_token = EstateAccessToken.objects.filter(token_hash=second_hash).first()
        assert new_token is not None
        assert new_token.is_active is True

    def test_reactivation_creates_new_snapshots(self, user, item_with_values):
        activate_estate_plan(user)
        activate_estate_plan(user)
        # Two activations → two snapshot records for the same item
        count = ValuationSnapshot.objects.filter(
            owner=user, item=item_with_values
        ).count()
        assert count == 2
