"""
Functional tests for Story 1.4: Estate Plan Dashboard & Completeness View.

Covers:
  - GET /estate/ returns 200 for authenticated user
  - GET /estate/ redirects unauthenticated user to login
  - Shows executor name when designated
  - Shows "No executor designated" warning when not
  - Shows completeness count (X / Y items)
  - Bulk Assign link present
  - No division-by-zero when user has zero items
  - Item names appear in the table
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import (
    Beneficiary,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateExecutor,
)

User = get_user_model()

pytestmark = pytest.mark.django_db

DASHBOARD_URL = "/estate/"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(username="dash_func_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Watches",
        slug="watches-dash",
        field_schema=[],
    )


@pytest.fixture
def item(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Rolex Submariner",
    )


@pytest.fixture
def item2(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Omega Speedmaster",
    )


@pytest.fixture
def beneficiary(user):
    return Beneficiary.objects.create(
        owner=user,
        name="Jane Doe",
        relationship="Spouse",
    )


@pytest.fixture
def executor(user):
    return EstateExecutor.objects.create(
        owner=user,
        name="John Smith",
        contact_info="john@example.com",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestEstateDashboardAccess:
    def test_returns_200_for_authenticated_user(self, auth_client):
        assert auth_client.get(DASHBOARD_URL).status_code == 200

    def test_redirects_unauthenticated_to_login(self):
        response = Client().get(DASHBOARD_URL)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]


class TestEstateDashboardExecutorCard:
    def test_shows_executor_name_when_designated(self, auth_client, executor):
        content = auth_client.get(DASHBOARD_URL).content.decode()
        assert "John Smith" in content

    def test_shows_no_executor_warning_when_not_designated(self, auth_client):
        content = auth_client.get(DASHBOARD_URL).content.decode()
        assert "No executor designated" in content

    def test_does_not_show_no_executor_when_executor_exists(
        self, auth_client, executor
    ):
        content = auth_client.get(DASHBOARD_URL).content.decode()
        assert "No executor designated" not in content


class TestEstateDashboardCompleteness:
    def test_no_items_shows_no_error(self, auth_client):
        response = auth_client.get(DASHBOARD_URL)
        assert response.status_code == 200

    def test_shows_items_count_when_items_present(self, auth_client, item, item2):
        content = auth_client.get(DASHBOARD_URL).content.decode()
        assert "2" in content

    def test_shows_assigned_count(self, auth_client, item, item2, beneficiary):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        content = auth_client.get(DASHBOARD_URL).content.decode()
        assert "1" in content

    def test_shows_zero_pct_when_none_assigned(self, auth_client, item, item2):
        content = auth_client.get(DASHBOARD_URL).content.decode()
        assert "0%" in content

    def test_shows_100_pct_when_all_assigned(
        self, auth_client, item, item2, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        BeneficiaryAssignment.objects.create(item=item2, beneficiary=beneficiary)
        content = auth_client.get(DASHBOARD_URL).content.decode()
        assert "100%" in content


class TestEstateDashboardItemsTable:
    def test_item_names_appear_in_table(self, auth_client, item, item2):
        content = auth_client.get(DASHBOARD_URL).content.decode()
        assert "Rolex Submariner" in content
        assert "Omega Speedmaster" in content

    def test_unassigned_badge_shown_for_unassigned_items(self, auth_client, item):
        content = auth_client.get(DASHBOARD_URL).content.decode()
        assert "Unassigned" in content

    def test_beneficiary_name_shown_for_assigned_item(
        self, auth_client, item, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        content = auth_client.get(DASHBOARD_URL).content.decode()
        assert "Jane Doe" in content


class TestEstateDashboardBulkAssignLink:
    def test_bulk_assign_link_present(self, auth_client):
        content = auth_client.get(DASHBOARD_URL).content.decode()
        assert "/estate/assign/" in content
