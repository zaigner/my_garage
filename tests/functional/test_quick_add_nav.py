"""
Functional tests for the global Quick Add nav button (P2a).

Verifies:
  - Quick Add button is present in the nav for authenticated users
  - Quick Add dropdown contains links to each of the user's active collections
  - "New Collection Type" link is always present for authenticated users
  - Empty state text appears when user has no collections
  - Quick Add button is NOT rendered for anonymous users
  - quick_add_collections context is injected on inner pages (not just home)
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from my_garage.models import CollectionType, DynamicCollectionItem

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(db):
    return User.objects.create_user(username="quick_add_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def anon_client():
    return Client()


@pytest.fixture
def sneaker_collection(user):
    return CollectionType.objects.create(
        owner=user, name="Sneakers", slug="sneakers-qa", is_active=True
    )


@pytest.fixture
def wine_collection(user):
    return CollectionType.objects.create(
        owner=user, name="Wine Cellar", slug="wine-cellar-qa", is_active=True
    )


@pytest.fixture
def inactive_collection(user):
    return CollectionType.objects.create(
        owner=user, name="Old Archive", slug="old-archive-qa", is_active=False
    )


class TestQuickAddButton:
    def test_quick_add_button_present_for_authenticated_user(self, auth_client, user):
        response = auth_client.get(reverse("home"))
        content = response.content.decode()
        assert "Quick add item" in content  # aria-label

    def test_quick_add_button_not_present_for_anonymous_user(self, anon_client):
        response = anon_client.get(reverse("home"))
        content = response.content.decode()
        assert "Quick add item" not in content

    def test_new_collection_type_link_always_present(self, auth_client):
        response = auth_client.get(reverse("home"))
        content = response.content.decode()
        assert "New Collection Type" in content

    def test_add_to_collection_heading_present(self, auth_client):
        response = auth_client.get(reverse("home"))
        content = response.content.decode()
        assert "Add to Collection" in content


class TestQuickAddCollectionLinks:
    def test_user_active_collections_appear_in_dropdown(
        self, auth_client, sneaker_collection, wine_collection
    ):
        response = auth_client.get(reverse("home"))
        content = response.content.decode()
        assert "Sneakers" in content
        assert "Wine Cellar" in content

    def test_inactive_collections_excluded_from_dropdown(
        self, auth_client, inactive_collection
    ):
        response = auth_client.get(reverse("home"))
        content = response.content.decode()
        assert "Old Archive" not in content

    def test_collection_add_url_in_dropdown(self, auth_client, sneaker_collection):
        response = auth_client.get(reverse("home"))
        content = response.content.decode()
        expected_url = reverse(
            "collections:collection_item_add",
            kwargs={"collection_slug": sneaker_collection.slug},
        )
        assert expected_url in content

    def test_empty_state_shown_when_no_collections(self, auth_client, user):
        response = auth_client.get(reverse("home"))
        content = response.content.decode()
        assert "No collections yet" in content


class TestQuickAddOnInnerPages:
    def test_quick_add_available_on_collection_item_detail(
        self, auth_client, sneaker_collection, user
    ):
        item = DynamicCollectionItem.objects.create(
            owner=user,
            collection_type=sneaker_collection,
            name="Air Max 90",
        )
        url = reverse(
            "collections:collection_item_detail",
            kwargs={"collection_slug": sneaker_collection.slug, "item_id": item.id},
        )
        response = auth_client.get(url)
        content = response.content.decode()
        assert "Quick add item" in content
        assert "Sneakers" in content

    def test_quick_add_available_on_collection_list(
        self, auth_client, sneaker_collection
    ):
        url = reverse(
            "collections:collection_list",
            kwargs={"collection_slug": sneaker_collection.slug},
        )
        response = auth_client.get(url)
        content = response.content.decode()
        assert "Quick add item" in content
