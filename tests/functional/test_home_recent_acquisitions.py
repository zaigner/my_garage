"""
Functional tests for the home page Recent Acquisitions section.

Verifies the three rendering states:
  1. Authenticated user WITH items  → real item cards, no fake names
  2. Authenticated user with NO items → empty-vault prompt, no fake names
  3. Unauthenticated visitor         → generic marketing placeholders only
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import CollectionType, DynamicCollectionItem

User = get_user_model()

HOME_URL = "/"

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="acq_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def automobiles_type(user):
    ct, _ = CollectionType.objects.get_or_create(
        owner=user,
        slug="automobiles",
        defaults={
            "name": "Automobiles",
            "service_provider_key": "vehicle",
            "is_system": True,
        },
    )
    return ct


@pytest.fixture
def collection_item(user, automobiles_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=automobiles_type,
        name="2019 Porsche 911",
        purchase_price=Decimal("120000.00"),
        current_market_value=Decimal("135000.00"),
    )


# ---------------------------------------------------------------------------
# State 1: authenticated user WITH items
# ---------------------------------------------------------------------------


class TestAuthenticatedWithItems:
    def test_shows_real_item_name(self, auth_client, collection_item):
        response = auth_client.get(HOME_URL)
        content = response.content.decode()

        assert "2019 Porsche 911" in content

    def test_does_not_show_fake_names(self, auth_client, collection_item):
        response = auth_client.get(HOME_URL)
        content = response.content.decode()

        assert "Patek Philippe Nautilus" not in content
        assert "Porsche 911 GT3" not in content
        assert "First Edition: The Great Gatsby" not in content

    def test_does_not_show_empty_vault_prompt(self, auth_client, collection_item):
        response = auth_client.get(HOME_URL)
        content = response.content.decode()

        assert "Your vault awaits" not in content

    def test_item_links_to_detail_page(self, auth_client, collection_item):
        response = auth_client.get(HOME_URL)
        content = response.content.decode()

        expected_url = f"/collections/{collection_item.collection_type.slug}/items/{collection_item.id}/"  # noqa: E501
        assert expected_url in content


# ---------------------------------------------------------------------------
# State 2: authenticated user with NO items
# ---------------------------------------------------------------------------


class TestAuthenticatedNoItems:
    def test_shows_empty_vault_prompt(self, auth_client):
        response = auth_client.get(HOME_URL)
        content = response.content.decode()

        assert "Your vault awaits" in content

    def test_does_not_show_fake_names(self, auth_client):
        response = auth_client.get(HOME_URL)
        content = response.content.decode()

        assert "Patek Philippe Nautilus" not in content
        assert "Porsche 911 GT3" not in content
        assert "First Edition: The Great Gatsby" not in content

    def test_shows_start_collection_link(self, auth_client):
        response = auth_client.get(HOME_URL)
        content = response.content.decode()

        assert "Start Your Collection" in content


# ---------------------------------------------------------------------------
# State 3: unauthenticated visitor sees marketing placeholders only
# ---------------------------------------------------------------------------


class TestUnauthenticated:
    def test_shows_generic_marketing_labels(self):
        response = Client().get(HOME_URL)
        content = response.content.decode()

        assert "Fine Timepieces" in content
        assert "Luxury Automobiles" in content
        assert "Curated Assets" in content

    def test_does_not_show_fake_owner_names(self):
        """Old fake specific items should not appear as if the visitor owns them."""
        response = Client().get(HOME_URL)
        content = response.content.decode()

        assert "Patek Philippe Nautilus" not in content
        assert "First Edition: The Great Gatsby" not in content

    def test_does_not_show_empty_vault_prompt(self):
        response = Client().get(HOME_URL)
        content = response.content.decode()

        assert "Your vault awaits" not in content
