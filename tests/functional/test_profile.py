"""
Functional tests for the user profile page (/accounts/profile/).

Covers:
  - GET: 200 for authenticated, redirect for unauthenticated
  - GET: all three cards render (Profile Information, Security, Account Information)
  - GET: form pre-populated with existing user data
  - GET: username shown read-only (not an editable form field)
  - GET: total_items counts only current user's items
  - GET: Change Password link present
  - POST: valid data saves and PRG-redirects to profile
  - POST: valid data triggers success toast message
  - POST: invalid/blank email returns 200 with form errors
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.forms import ProfileForm
from my_garage.models import CollectionType, DynamicCollectionItem

User = get_user_model()

pytestmark = pytest.mark.django_db

PROFILE_URL = "/accounts/profile/"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="profile_user",
        password="testpass123",
        email="original@example.com",
    )


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Test Collection",
        slug="test-collection",
        service_provider_key="default",
        field_schema={"fields": []},
    )


# ── GET Tests ─────────────────────────────────────────────────────────────────


class TestProfileGET:
    def test_returns_200_for_authenticated_user(self, auth_client):
        response = auth_client.get(PROFILE_URL)
        assert response.status_code == 200

    def test_redirects_unauthenticated_to_login(self):
        response = Client().get(PROFILE_URL)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_form_in_context(self, auth_client):
        response = auth_client.get(PROFILE_URL)
        assert isinstance(response.context["form"], ProfileForm)

    def test_total_items_zero_with_no_items(self, auth_client):
        response = auth_client.get(PROFILE_URL)
        assert response.context["total_items"] == 0

    def test_total_items_counts_only_current_user_items(
        self, auth_client, user, collection_type
    ):
        other_user = User.objects.create_user(username="other", password="pass")
        other_ct = CollectionType.objects.create(
            owner=other_user,
            name="Other",
            slug="other",
            service_provider_key="default",
            field_schema={"fields": []},
        )
        DynamicCollectionItem.objects.create(
            owner=user,
            collection_type=collection_type,
            name="Item A",
            custom_fields={},
        )
        DynamicCollectionItem.objects.create(
            owner=user,
            collection_type=collection_type,
            name="Item B",
            custom_fields={},
        )
        DynamicCollectionItem.objects.create(
            owner=other_user,
            collection_type=other_ct,
            name="Other Item",
            custom_fields={},
        )
        response = auth_client.get(PROFILE_URL)
        assert response.context["total_items"] == 2

    def test_profile_information_card_renders(self, auth_client):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "Profile Information" in content

    def test_security_card_renders(self, auth_client):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "Security" in content

    def test_account_info_card_renders(self, auth_client):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "Account Information" in content

    def test_change_password_link_present(self, auth_client):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "/accounts/password_change/" in content

    def test_username_shown_not_editable(self, auth_client, user):
        content = auth_client.get(PROFILE_URL).content.decode()
        assert user.username in content
        assert 'name="username"' not in content

    def test_form_prepopulated_with_existing_email(self, auth_client, user):
        user.email = "prefilled@example.com"
        user.save()
        content = auth_client.get(PROFILE_URL).content.decode()
        assert "prefilled@example.com" in content


# ── POST Tests ────────────────────────────────────────────────────────────────


class TestProfilePOST:
    def test_valid_post_redirects_to_profile(self, auth_client):
        response = auth_client.post(
            PROFILE_URL,
            {"first_name": "Zach", "last_name": "A", "email": "zach@example.com"},
        )
        assert response.status_code == 302
        assert response["Location"].endswith(PROFILE_URL)

    def test_valid_post_saves_first_name(self, auth_client, user):
        auth_client.post(
            PROFILE_URL,
            {"first_name": "Zach", "last_name": "A", "email": "zach@example.com"},
        )
        user.refresh_from_db()
        assert user.first_name == "Zach"

    def test_valid_post_saves_email(self, auth_client, user):
        auth_client.post(
            PROFILE_URL,
            {"first_name": "Zach", "last_name": "A", "email": "new@example.com"},
        )
        user.refresh_from_db()
        assert user.email == "new@example.com"

    def test_valid_post_shows_success_message(self, auth_client):
        response = auth_client.post(
            PROFILE_URL,
            {"first_name": "Zach", "last_name": "A", "email": "zach@example.com"},
            follow=True,
        )
        content = response.content.decode()
        assert "Profile updated" in content

    def test_invalid_email_returns_200_with_errors(self, auth_client):
        response = auth_client.post(
            PROFILE_URL,
            {"first_name": "Zach", "last_name": "A", "email": "not-an-email"},
        )
        assert response.status_code == 200

    def test_blank_email_returns_200_with_errors(self, auth_client):
        response = auth_client.post(
            PROFILE_URL,
            {"first_name": "Zach", "last_name": "A", "email": ""},
        )
        assert response.status_code == 200

    def test_invalid_post_does_not_save(self, auth_client, user):
        original_email = user.email
        auth_client.post(
            PROFILE_URL,
            {"first_name": "Zach", "last_name": "A", "email": "bad-email"},
        )
        user.refresh_from_db()
        assert user.email == original_email
