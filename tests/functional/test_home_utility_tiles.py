"""
Functional tests for the home page utility tile navigation.

Covers:
  - total_items_count and total_collection_types_count context variables
  - Utility tiles render for authenticated users
  - Utility tiles do not render for unauthenticated users
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import CollectionType, DynamicCollectionItem

User = get_user_model()

pytestmark = pytest.mark.django_db


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(username="tiles_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def automobiles_ct(user):
    return CollectionType.objects.create(
        owner=user,
        name="Automobiles",
        slug="automobiles",
        service_provider_key="vehicle",
        field_schema={"fields": []},
    )


@pytest.fixture
def horology_ct(user):
    return CollectionType.objects.create(
        owner=user,
        name="Horology Salon",
        slug="horology-salon",
        service_provider_key="timepiece",
        field_schema={"fields": []},
    )


@pytest.fixture
def custom_ct(user):
    return CollectionType.objects.create(
        owner=user,
        name="Sneakers",
        slug="sneakers",
        service_provider_key="default",
        field_schema={"fields": []},
    )


@pytest.fixture
def vehicle_item(user, automobiles_ct):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=automobiles_ct,
        name="Porsche 911",
        current_market_value=Decimal("80000.00"),
        custom_fields={},
    )


@pytest.fixture
def custom_item(user, custom_ct):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=custom_ct,
        name="Air Jordan 1",
        current_market_value=Decimal("400.00"),
        custom_fields={},
    )


# ── Context variable tests ────────────────────────────────────────────────────


class TestHomeContextTotals:
    def test_total_items_count_is_zero_with_no_items(self, auth_client):
        response = auth_client.get("/")
        assert response.context["total_items_count"] == 0

    def test_total_items_count_reflects_all_collection_items(
        self, auth_client, vehicle_item, custom_item
    ):
        response = auth_client.get("/")
        assert response.context["total_items_count"] == 2

    def test_total_collection_types_count_is_zero_with_no_types(self, auth_client):
        response = auth_client.get("/")
        assert response.context["total_collection_types_count"] == 0

    def test_total_collection_types_count_includes_all_types(
        self, auth_client, automobiles_ct, horology_ct, custom_ct
    ):
        response = auth_client.get("/")
        assert response.context["total_collection_types_count"] == 3

    def test_total_collection_types_count_excludes_inactive(self, auth_client, user):
        CollectionType.objects.create(
            owner=user,
            name="Archived",
            slug="archived",
            service_provider_key="default",
            field_schema={"fields": []},
            is_active=False,
        )
        response = auth_client.get("/")
        assert response.context["total_collection_types_count"] == 0

    def test_context_totals_absent_for_unauthenticated_user(self):
        response = Client().get("/")
        assert "total_items_count" not in response.context
        assert "total_collection_types_count" not in response.context


# ── Tile render tests ─────────────────────────────────────────────────────────


class TestHomeUtilityTilesRender:
    def test_collections_hub_tile_links_to_collection_type_list(
        self, auth_client, automobiles_ct
    ):
        response = auth_client.get("/")
        assert "/collections/" in response.content.decode()

    def test_estate_legacy_tile_renders_for_authenticated_user(self, auth_client):
        content = auth_client.get("/").content.decode()
        assert "Estate" in content
        assert "Legacy" in content

    def test_estate_legacy_tile_shows_coming_soon_badge(self, auth_client):
        content = auth_client.get("/").content.decode()
        assert "Coming Soon" in content

    def test_my_account_tile_links_to_profile(self, auth_client):
        content = auth_client.get("/").content.decode()
        assert "/accounts/profile/" in content

    def test_utility_tiles_not_rendered_for_unauthenticated_user(self):
        content = Client().get("/").content.decode()
        assert "Collections Hub" not in content
        assert "Plan Your Legacy" not in content
        assert "My Account" not in content
