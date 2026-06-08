"""
Functional tests for Story 1.5: Profile Page Estate Status Card & Account Deletion.

Covers:
  - Profile page estate card visibility and content
  - "No executor designated" warning
  - Executor name display
  - Completeness count display
  - Manage Estate Plan link
  - Danger Zone card present
  - POST /accounts/delete/ deletes user and redirects to home
  - DELETE cascades beneficiary/executor/assignment/changelog
  - GET /accounts/delete/ is rejected (405)
  - Unauthenticated POST redirects to login
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
    EstateChangeLog,
    EstateExecutor,
)

User = get_user_model()

pytestmark = pytest.mark.django_db

PROFILE_URL = "/accounts/profile/"
DELETE_URL = "/accounts/delete/"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(username="profile15_user", password="pass")


@pytest.fixture
def auth_client(user):
    c = Client()
    c.force_login(user)
    return c


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user, name="Watches", slug="watches-p15", field_schema=[]
    )


@pytest.fixture
def item(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user, collection_type=collection_type, name="Submariner"
    )


@pytest.fixture
def item2(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user, collection_type=collection_type, name="Speedmaster"
    )


@pytest.fixture
def beneficiary(user):
    return Beneficiary.objects.create(
        owner=user, name="Jane Doe", relationship="Spouse"
    )


@pytest.fixture
def executor(user):
    return EstateExecutor.objects.create(
        owner=user, name="John Smith", contact_info="john@example.com"
    )


# ── Profile page ──────────────────────────────────────────────────────────────


class TestProfileEstatePage:
    def test_profile_returns_200(self, auth_client):
        assert auth_client.get(PROFILE_URL).status_code == 200

    def test_estate_card_heading_present(self, auth_client):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "Estate" in content

    def test_shows_no_executor_warning(self, auth_client):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "No executor designated" in content

    def test_shows_executor_name_when_designated(self, auth_client, executor):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "John Smith" in content

    def test_hides_no_executor_warning_when_executor_set(self, auth_client, executor):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "No executor designated" not in content

    def test_completeness_count_present(self, auth_client, item, item2, beneficiary):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "1" in content
        assert "2" in content

    def test_manage_estate_link_present(self, auth_client):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "/estate/" in content

    def test_danger_zone_section_present(self, auth_client):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "Danger Zone" in content

    def test_delete_account_button_present(self, auth_client):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "Delete Account" in content


# ── Account deletion ──────────────────────────────────────────────────────────


class TestAccountDeletion:
    def test_post_deletes_user_and_redirects_to_home(self, auth_client, user):
        user_pk = user.pk
        response = auth_client.post(DELETE_URL)
        assert response.status_code == 302
        assert response["Location"] == "/"
        assert not User.objects.filter(pk=user_pk).exists()

    def test_post_cascades_beneficiary_records(self, auth_client, user, beneficiary):
        ben_pk = beneficiary.pk
        auth_client.post(DELETE_URL)
        assert not Beneficiary.objects.filter(pk=ben_pk).exists()

    def test_post_cascades_executor_record(self, auth_client, user, executor):
        exec_pk = executor.pk
        auth_client.post(DELETE_URL)
        assert not EstateExecutor.objects.filter(pk=exec_pk).exists()

    def test_post_cascades_assignment_record(
        self, auth_client, user, item, beneficiary
    ):
        assignment = BeneficiaryAssignment.objects.create(
            item=item, beneficiary=beneficiary
        )
        assign_pk = assignment.pk
        auth_client.post(DELETE_URL)
        assert not BeneficiaryAssignment.objects.filter(pk=assign_pk).exists()

    def test_post_cascades_changelog_record(self, auth_client, user):
        log = EstateChangeLog.objects.create(
            owner=user, action="ASSIGNED", item_name="Test Item"
        )
        log_pk = log.pk
        auth_client.post(DELETE_URL)
        assert not EstateChangeLog.objects.filter(pk=log_pk).exists()

    def test_get_returns_405(self, auth_client):
        response = auth_client.get(DELETE_URL)
        assert response.status_code == 405

    def test_unauthenticated_post_redirects_to_login(self):
        response = Client().post(DELETE_URL)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]
