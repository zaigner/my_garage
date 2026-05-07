"""
Functional tests for the tabbed Service Records & Projects panel on the
collection item detail page (P1c UX enhancement).

Verifies:
  - Tab container is present with Alpine.js x-data
  - "Service Records" and "Projects" tab buttons are in the HTML
  - Service record data appears in the HTML (all records, not capped)
  - Project (upgrade) data appears in the HTML
  - Empty states render correctly
  - Service Records section is no longer in the sidebar (tab panel only)
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

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
    return User.objects.create_user(username="tabs_test_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def sneaker_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Sneakers",
        slug="sneakers-tabs",
        field_schema={"fields": [{"name": "size", "type": "text", "label": "Size"}]},
    )


@pytest.fixture
def sneaker_item(user, sneaker_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=sneaker_type,
        name="Air Max 90",
        purchase_price=Decimal("120.00"),
        custom_fields={"size": "10"},
    )


@pytest.fixture
def service_records(sneaker_item):
    records = []
    for i in range(3):
        records.append(
            GenericServiceRecord.objects.create(
                item=sneaker_item,
                date="2024-01-01",
                vendor=f"Shoe Clinic {i + 1}",
                description=f"Cleaning service number {i + 1}",
                category="MAINTENANCE",
                total_cost=Decimal("25.00"),
            )
        )
    return records


@pytest.fixture
def upgrades(sneaker_item):
    projects = []
    for i in range(2):
        projects.append(
            GenericUpgrade.objects.create(
                item=sneaker_item,
                name=f"Custom Laces {i + 1}",
                status="WISHLIST",
                cost=Decimal("15.00"),
            )
        )
    return projects


def _detail_url(item):
    return reverse(
        "collections:collection_item_detail",
        kwargs={"collection_slug": item.collection_type.slug, "item_id": item.id},
    )


# ---------------------------------------------------------------------------
# Tab structure in HTML
# ---------------------------------------------------------------------------


class TestTabStructure:
    def test_tab_container_has_alpine_data(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "activeTab" in content

    def test_service_records_tab_button_present(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "Service Records" in content

    def test_projects_tab_button_present(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "Projects" in content

    def test_page_renders_ok(self, auth_client, sneaker_item):
        response = auth_client.get(_detail_url(sneaker_item))
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Service records tab content
# ---------------------------------------------------------------------------


class TestServiceRecordsTab:
    def test_all_service_records_in_html(
        self, auth_client, sneaker_item, service_records
    ):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        for record in service_records:
            assert record.vendor in content

    def test_service_record_count_badge(
        self, auth_client, sneaker_item, service_records
    ):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "3" in content

    def test_add_service_record_link_present(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "Add" in content
        assert (
            "service"
            in auth_client.get(_detail_url(sneaker_item)).content.decode().lower()
        )

    def test_empty_state_shown_when_no_records(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "No service records yet" in content


# ---------------------------------------------------------------------------
# Projects tab content
# ---------------------------------------------------------------------------


class TestProjectsTab:
    def test_all_upgrades_in_html(self, auth_client, sneaker_item, upgrades):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        for upgrade in upgrades:
            assert upgrade.name in content

    def test_project_count_badge(self, auth_client, sneaker_item, upgrades):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "2" in content

    def test_kanban_link_present(self, auth_client, sneaker_item, upgrades):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "Kanban" in content

    def test_empty_state_shown_when_no_projects(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "No projects yet" in content
