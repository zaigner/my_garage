"""
Functional tests for Story 2.1: Estate Plan Activation, Executor Token
Generation & Valuation Snapshot.

Covers:
  - Unauthenticated GET → redirect to login
  - Authenticated GET with no executor → 200, submit button disabled
  - Authenticated GET with executor → 200, submit button not disabled
  - POST with confirmed=True and executor → token created, snapshots created, redirect
  - Success page shows the active code, carried in a signed cookie (never the
    session); expired, tampered or replaced codes redirect back to activate
  - POST without confirming checkbox → no token created
  - Reactivation → old token deactivated, new token active
  - Direct GET to success with no code cookie → redirect to activate
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core import signing
from django.test import Client, override_settings

from my_garage.api.services import hash_executor_code
from my_garage.estate_views import ACTIVATION_COOKIE
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


def _shown_code(response):
    soup = BeautifulSoup(response.content.decode(), "html5lib")
    box = soup.select_one("div.select-all")
    return box.get_text(strip=True) if box else None


def _stale_timestamp(seconds):
    """Make TimestampSigner stamp values as if signed `seconds` ago."""
    return patch.object(
        signing.TimestampSigner,
        "timestamp",
        lambda self: signing.b62_encode(int(time.time()) - seconds),
    )


class TestActivateSuccessPage:
    def test_success_page_shows_the_active_code(self, auth_client, executor):
        response = auth_client.post(ACTIVATE_URL, {"confirmed": "on"}, follow=True)
        code = _shown_code(response)
        token = EstateAccessToken.objects.get(owner=executor.owner, is_active=True)
        assert code and hash_executor_code(code) == token.token_hash

    def test_success_page_expiry_has_zone_label(self, auth_client, executor):
        response = auth_client.post(ACTIVATE_URL, {"confirmed": "on"}, follow=True)
        body = response.content.decode()
        start = body.index("Expires ")
        assert " UTC if unused." in body[start : body.index("</p>", start)]

    def test_success_page_with_no_cookie_redirects(self, auth_client):
        response = auth_client.get(SUCCESS_URL)
        assert response.status_code == 302
        assert response["Location"] == ACTIVATE_URL

    def test_activate_sets_short_lived_scoped_cookie(self, auth_client, executor):
        response = auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        cookie = response.cookies[ACTIVATION_COOKIE]
        assert cookie["httponly"] is True
        assert cookie["samesite"] == "Strict"
        assert cookie["path"] == SUCCESS_URL
        # Browser-session cookie: never written to the on-disk cookie store
        assert cookie["max-age"] == "" and cookie["expires"] == ""
        assert "estate_activation_token" not in auth_client.session

    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_cookie_is_secure_when_session_cookie_is(self, auth_client, executor):
        response = auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        assert response.cookies[ACTIVATION_COOKIE]["secure"] is True

    def test_code_never_stored_in_session(self, auth_client, executor):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        # Snapshot the stored sessions in the window before the redirect is followed
        stored = [str(row.get_decoded()) for row in Session.objects.all()]
        code = _shown_code(auth_client.get(SUCCESS_URL))
        assert stored and code
        assert all(code not in data for data in stored)

    def test_success_page_is_never_cached(self, auth_client, executor):
        response = auth_client.post(ACTIVATE_URL, {"confirmed": "on"}, follow=True)
        assert "no-store" in response["Cache-Control"]

    def test_success_page_deletes_cookie(self, auth_client, executor):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        response = auth_client.get(SUCCESS_URL)
        assert response.status_code == 200
        cookie = response.cookies[ACTIVATION_COOKIE]
        assert cookie.value == "" and int(cookie["max-age"]) == 0
        assert cookie["path"] == SUCCESS_URL

    def test_second_visit_redirects(self, auth_client, executor):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        assert auth_client.get(SUCCESS_URL).status_code == 200
        response = auth_client.get(SUCCESS_URL)
        assert response.status_code == 302
        assert response["Location"] == ACTIVATE_URL
        page = auth_client.get(ACTIVATE_URL).content.decode()
        assert "An access code can only be shown once" in page

    def test_expired_cookie_redirects(self, auth_client, executor):
        with _stale_timestamp(601):
            auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        response = auth_client.get(SUCCESS_URL)
        assert response.status_code == 302
        assert response["Location"] == ACTIVATE_URL

    def test_cookie_just_inside_lifetime_is_shown(self, auth_client, executor):
        with _stale_timestamp(590):
            auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        assert auth_client.cookies[ACTIVATION_COOKIE].value
        response = auth_client.get(SUCCESS_URL)
        assert response.status_code == 200
        code = _shown_code(response)
        token = EstateAccessToken.objects.get(owner=executor.owner, is_active=True)
        assert code and hash_executor_code(code) == token.token_hash

    def test_tampered_cookie_redirects(self, auth_client, executor):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        value = auth_client.cookies[ACTIVATION_COOKIE].value
        raw, rest = value.split(":", 1)
        forged = ("B" if raw[0] == "A" else "A") + raw[1:]
        auth_client.cookies[ACTIVATION_COOKIE] = forged + ":" + rest
        response = auth_client.get(SUCCESS_URL)
        assert response.status_code == 302
        assert response["Location"] == ACTIVATE_URL

    def test_replaced_code_redirects_with_message(self, auth_client, executor):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        first = auth_client.cookies[ACTIVATION_COOKIE].value
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        auth_client.cookies[ACTIVATION_COOKIE] = first
        response = auth_client.get(SUCCESS_URL)
        assert response.status_code == 302
        assert response["Location"] == ACTIVATE_URL
        page = auth_client.get(ACTIVATE_URL).content.decode()
        assert "A newer access code was issued" in page

    def test_revoked_code_redirects_with_message(self, auth_client, executor):
        auth_client.post(ACTIVATE_URL, {"confirmed": "on"})
        raw = auth_client.cookies[ACTIVATION_COOKIE].value.split(":", 1)[0]
        auth_client.post("/estate/activate/revoke/")
        response = auth_client.get(SUCCESS_URL)
        assert response.status_code == 302
        assert response["Location"] == ACTIVATE_URL
        page = auth_client.get(ACTIVATE_URL).content.decode()
        assert "no longer active" in page
        assert raw not in response.content.decode() and raw not in page

    def test_unauthenticated_success_page_redirects_to_login(self, client):
        response = client.get(SUCCESS_URL)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]
