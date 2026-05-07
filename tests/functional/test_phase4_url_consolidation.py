"""
Functional tests for Phase 4 — URL Consolidation.

Covers:
  - /garage/  redirects to /collections/automobiles/items/
  - /timepieces/  redirects to /collections/horology-salon/items/
  - Home view sources counts/values from DynamicCollectionItem
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(username="phase4_user", password="pass")


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
def vehicle_item(user, automobiles_ct):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=automobiles_ct,
        name="2021 Toyota Tacoma",
        current_market_value=Decimal("40000.00"),
        custom_fields={},
    )


@pytest.fixture
def timepiece_item(user, horology_ct):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=horology_ct,
        name="Rolex Submariner",
        current_market_value=Decimal("12000.00"),
        custom_fields={},
    )


# ── Redirect tests ────────────────────────────────────────────────────────────


class TestGarageListRedirect:
    def test_redirects_to_automobiles_collection(self, auth_client):
        response = auth_client.get("/garage/")
        assert response.status_code == 302
        assert response["Location"] == "/collections/automobiles/items/"

    def test_redirect_is_temporary(self, auth_client):
        response = auth_client.get("/garage/")
        assert response.status_code == 302  # 302 not 301

    def test_unauthenticated_garage_redirects(self):
        """Unauthenticated users also get redirected (RedirectView doesn't require
        auth)."""
        response = Client().get("/garage/")
        assert response.status_code == 302
        assert response["Location"] == "/collections/automobiles/items/"

    def test_legacy_vehicle_id_route_requires_login(self):
        """Legacy /garage/<id>/ requires authentication."""
        response = Client().get("/garage/1/")
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]


class TestTimepiecesListRedirect:
    def test_redirects_to_horology_collection(self, auth_client):
        response = auth_client.get("/timepieces/")
        assert response.status_code == 302
        assert response["Location"] == "/collections/horology-salon/items/"

    def test_redirect_is_temporary(self, auth_client):
        response = auth_client.get("/timepieces/")
        assert response.status_code == 302

    def test_unauthenticated_timepieces_redirects(self):
        response = Client().get("/timepieces/")
        assert response.status_code == 302
        assert response["Location"] == "/collections/horology-salon/items/"

    def test_legacy_timepiece_id_route_requires_login(self):
        """Legacy /timepieces/<id>/ requires authentication."""
        response = Client().get("/timepieces/1/")
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]


# ── Home view — DynamicCollectionItem data source ─────────────────────────────


class TestHomeViewCollectionData:
    def test_home_shows_automobiles_count_from_collection(
        self, auth_client, vehicle_item
    ):
        response = auth_client.get("/")
        assert response.status_code == 200
        assert response.context["automobiles_count"] == 1

    def test_home_shows_timepieces_count_from_collection(
        self, auth_client, timepiece_item
    ):
        response = auth_client.get("/")
        assert response.status_code == 200
        assert response.context["timepieces_count"] == 1

    def test_home_totals_automobiles_value(self, auth_client, vehicle_item):
        response = auth_client.get("/")
        assert response.context["total_automobiles_value"] == Decimal("40000.00")

    def test_home_totals_timepieces_value(self, auth_client, timepiece_item):
        response = auth_client.get("/")
        assert response.context["total_timepieces_value"] == Decimal("12000.00")

    def test_home_excludes_system_collections_from_custom_list(
        self, auth_client, vehicle_item, timepiece_item
    ):
        response = auth_client.get("/")
        custom = response.context["custom_collections"]
        slugs = [c.slug for c in custom]
        assert "automobiles" not in slugs
        assert "horology-salon" not in slugs

    def test_home_custom_collections_shows_non_system(self, auth_client, user):
        sneakers_ct = CollectionType.objects.create(
            owner=user,
            name="Sneakers",
            slug="sneakers",
            service_provider_key="default",
            field_schema={"fields": []},
        )
        DynamicCollectionItem.objects.create(
            owner=user,
            collection_type=sneakers_ct,
            name="Air Jordan 1",
            current_market_value=Decimal("300.00"),
            custom_fields={},
        )
        response = auth_client.get("/")
        slugs = [c.slug for c in response.context["custom_collections"]]
        assert "sneakers" in slugs

    def test_home_unauthenticated_has_no_context_counts(self):
        response = Client().get("/")
        assert response.status_code == 200
        assert "automobiles_count" not in response.context
