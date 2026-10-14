"""
Functional tests for the hamburger menu's collection links.

Garage and Horology Salon used to be hardcoded for every visitor. The menu
now lists only the collections the signed-in user actually owns, on every
page that includes the nav, under each collection's own name.
"""

from __future__ import annotations

import re

import pytest
from django.test import Client
from django.urls import reverse

pytestmark = pytest.mark.django_db

HOME_URL = "/"

NAV_LINK_RE = re.compile(
    r'<a href="(?P<href>[^"]+)" data-testid="nav-collection-link"'
    r".*?<span>(?P<name>[^<]*)</span>",
    re.DOTALL,
)


def nav_collection_links(response) -> dict[str, str]:
    """Map of collection name → href for the menu's "Your Collections" links."""
    content = response.content.decode()
    return {m["name"]: m["href"] for m in NAV_LINK_RE.finditer(content)}


def collection_url(slug: str) -> str:
    return reverse("collections:collection_list", args=[slug])


class TestUnauthenticated:
    def test_menu_lists_no_collections(self):
        response = Client().get(HOME_URL)

        assert response.status_code == 200
        assert nav_collection_links(response) == {}

    def test_menu_does_not_link_to_system_collections(self):
        content = Client().get(HOME_URL).content.decode()

        assert collection_url("automobiles") not in content
        assert collection_url("horology-salon") not in content


class TestAuthenticatedWithoutSystemCollections:
    def test_menu_lists_no_collections(self, auth_client):
        response = auth_client.get(HOME_URL)

        assert nav_collection_links(response) == {}

    def test_menu_lists_only_owned_collection(self, auth_client, collection_type):
        response = auth_client.get(HOME_URL)

        assert nav_collection_links(response) == {
            collection_type.name: collection_url(collection_type.slug)
        }


class TestAuthenticatedWithSystemCollections:
    def test_menu_lists_system_collections_by_own_name(
        self, auth_client, automobiles_type, horology_type
    ):
        response = auth_client.get(HOME_URL)

        assert nav_collection_links(response) == {
            "Automobiles": collection_url("automobiles"),
            "Horology Salon": collection_url("horology-salon"),
        }

    def test_menu_lists_collections_beyond_home_page(
        self, auth_client, automobiles_type
    ):
        """Only the home view used to supply the list, so other pages had none."""
        response = auth_client.get(reverse("collections:collection_type_list"))

        assert response.status_code == 200
        assert nav_collection_links(response) == {
            "Automobiles": collection_url("automobiles")
        }

    def test_inactive_collection_is_not_listed(self, auth_client, automobiles_type):
        automobiles_type.is_active = False
        automobiles_type.save()

        response = auth_client.get(HOME_URL)

        assert nav_collection_links(response) == {}
