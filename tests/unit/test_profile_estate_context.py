"""
Unit tests for profile view estate context (Story 1.5).

Verifies that the profile view passes correct estate summary fields.
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

PROFILE_URL = "/accounts/profile/"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="profile_ctx_user", password="pass")


@pytest.fixture
def auth_client(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user, name="Watches", slug="watches-profile", field_schema=[]
    )


@pytest.fixture
def item(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user, collection_type=collection_type, name="Watch A"
    )


@pytest.fixture
def item2(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user, collection_type=collection_type, name="Watch B"
    )


@pytest.fixture
def beneficiary(user):
    return Beneficiary.objects.create(owner=user, name="Jane", relationship="Spouse")


@pytest.fixture
def executor(user):
    return EstateExecutor.objects.create(owner=user, name="Bob", contact_info="")


class TestProfileEstateContext:
    def test_executor_designated_false_when_no_executor(self, auth_client):
        response = auth_client.get(PROFILE_URL)
        assert response.context["executor_designated"] is False

    def test_executor_designated_true_when_executor_set(self, auth_client, executor):
        response = auth_client.get(PROFILE_URL)
        assert response.context["executor_designated"] is True

    def test_estate_items_total_zero_when_no_items(self, auth_client):
        response = auth_client.get(PROFILE_URL)
        assert response.context["estate_items_total"] == 0

    def test_estate_items_total_matches_item_count(self, auth_client, item, item2):
        response = auth_client.get(PROFILE_URL)
        assert response.context["estate_items_total"] == 2

    def test_estate_items_assigned_zero_when_none_assigned(
        self, auth_client, item, item2
    ):
        response = auth_client.get(PROFILE_URL)
        assert response.context["estate_items_assigned"] == 0

    def test_estate_items_assigned_correct_count(
        self, auth_client, item, item2, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        response = auth_client.get(PROFILE_URL)
        assert response.context["estate_items_assigned"] == 1

    def test_estate_completeness_pct_zero_no_items(self, auth_client):
        response = auth_client.get(PROFILE_URL)
        assert response.context["estate_completeness_pct"] == 0

    def test_estate_completeness_pct_100_all_assigned(
        self, auth_client, item, item2, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        BeneficiaryAssignment.objects.create(item=item2, beneficiary=beneficiary)
        response = auth_client.get(PROFILE_URL)
        assert response.context["estate_completeness_pct"] == 100
