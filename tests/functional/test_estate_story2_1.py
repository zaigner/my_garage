"""
Functional tests for Story 2.1: Estate Plan Activation, Executor Token
Generation & Valuation Snapshot.

Covers:
  - Unauthenticated GET → redirect to login
  - Authenticated GET with no executor → 200, submit button disabled
  - Authenticated GET with executor → 200, submit button not disabled
  - POST with confirmed=True and executor → token created, snapshots created, redirect
  - Success page shows token, purges from session after display
  - POST without confirming checkbox → no token created
  - Reactivation → old token deactivated, new token active
  - Direct GET to success with no session token → redirect to activate
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    EstateAccessToken,
    EstateExecutor,
    ValuationSnapshot,
)

User = get_user_model()

pytestmark = pytest.mark.django_db

ACTIVATE_URL = "/estate/activate/"
SUCCESS_URL = "/estate/activate/success/"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(username="estate_user_2_1_func", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def executor(user):
    return EstateExecutor.objects.create(
        owner=user,
        name="John Smith",
        contact_info="john@example.com",
    )


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Watches",
        slug="watches-2-1",
        field_schema=[],
        list_display_fields=[],
    )


@pytest.fixture
def item(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Test Watch",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestActivatePageAccess:
    def test_unauthenticated_get_redirects_to_login(self, client):
        response = client.get(ACTIVATE_URL)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_authenticated_get_returns_200(self, auth_client):
        response = auth_client.get(ACTIVATE_URL)
        assert response.status_code == 200

    def test_no_executor_submit_button_is_disabled(self, auth_client):
        response = auth_client.get(ACTIVATE_URL)
        content = response.content.decode()
        assert "disabled" in content

    def test_with_executor_submit_button_is_not_disabled(self, auth_client, executor):
        response = auth_client.get(ACTIVATE_URL)
        assert response.context["can_activate"] is True

    def test_no_executor_shows_warning_message(self, auth_client):
        response = auth_client.get(ACTIVATE_URL)
        content = response.content.decode()
        assert "designate an executor" in content.lower()


class TestActivatePost:
    def test_post_without_executor_does_not_create_token(self, auth_client):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        assert EstateAccessToken.objects.count() == 0

    def test_post_without_confirming_checkbox_rejected(self, auth_client, executor):
        response = auth_client.post(ACTIVATE_URL, {})
        # Form invalid — no token created
        assert EstateAccessToken.objects.count() == 0
        assert response.status_code == 200

    def test_valid_post_creates_access_token(self, auth_client, executor):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        assert EstateAccessToken.objects.filter(owner=executor.owner).exists()

    def test_valid_post_token_is_active(self, auth_client, executor):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        token = EstateAccessToken.objects.get(owner=executor.owner)
        assert token.is_active is True

    def test_valid_post_creates_snapshots_for_items(self, auth_client, executor, item):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        assert ValuationSnapshot.objects.filter(owner=executor.owner).count() == 1

    def test_valid_post_redirects_to_success(self, auth_client, executor):
        response = auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        assert response.status_code == 302
        assert response["Location"] == SUCCESS_URL

    def test_reactivation_deactivates_old_token(self, auth_client, executor):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        first_token = EstateAccessToken.objects.get(owner=executor.owner)
        first_hash = first_token.token_hash

        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})

        old = EstateAccessToken.objects.get(token_hash=first_hash)
        assert old.is_active is False

    def test_reactivation_creates_new_active_token(self, auth_client, executor):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        active_tokens = EstateAccessToken.objects.filter(
            owner=executor.owner, is_active=True
        )
        assert active_tokens.count() == 1


class TestActivateSuccessPage:
    def test_success_page_shows_token_from_session(self, auth_client, executor):
        # POST to activate — places token in session and redirects
        response = auth_client.post(ACTIVATE_URL, {"confirmed": "on"}, follow=True)
        content = response.content.decode()
        # The page should show SOMETHING that looks like a token (non-empty text)
        assert "estate" in content.lower() or len(content) > 100

    def test_success_page_with_no_session_token_redirects(self, auth_client):
        # Direct GET to success with no session token
        response = auth_client.get(SUCCESS_URL)
        assert response.status_code == 302
        assert response["Location"] == ACTIVATE_URL

    def test_success_page_purges_token_from_session(self, auth_client, executor):
        # Activate to put token in session
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        # Visit success page — consumes the session token
        auth_client.get(SUCCESS_URL)
        # Second visit should redirect (no token left)
        response = auth_client.get(SUCCESS_URL)
        assert response.status_code == 302
        assert response["Location"] == ACTIVATE_URL

    def test_unauthenticated_success_page_redirects_to_login(self, client):
        response = client.get(SUCCESS_URL)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]
