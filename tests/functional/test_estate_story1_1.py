"""
Functional tests for Story 1.1: Beneficiary Profile Data Model & CRUD.

Covers:
  - GET /estate/beneficiaries/ — 200 for auth, 302 for anon
  - Beneficiary list renders existing records
  - Empty state message when no beneficiaries
  - POST /estate/beneficiaries/add/ — creates record, redirects, shows toast
  - POST with blank name — returns 200 with error, no record created
  - POST /estate/beneficiaries/<pk>/delete/ — deletes, redirects, shows toast
  - DELETE of another user's beneficiary — 404
  - Owner isolation: other user's beneficiaries not visible
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import Beneficiary

User = get_user_model()

pytestmark = pytest.mark.django_db

LIST_URL = "/estate/beneficiaries/"
ADD_URL = "/estate/beneficiaries/add/"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(username="estate_user", password="pass")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="other_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def beneficiary(user):
    return Beneficiary.objects.create(
        owner=user,
        name="Jane Doe",
        relationship="Spouse",
        contact_info="jane@example.com",
    )


# ── GET tests ─────────────────────────────────────────────────────────────────


class TestBeneficiaryListGET:
    def test_returns_200_for_authenticated_user(self, auth_client):
        assert auth_client.get(LIST_URL).status_code == 200

    def test_redirects_unauthenticated_to_login(self):
        response = Client().get(LIST_URL)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_shows_existing_beneficiaries(self, auth_client, beneficiary):
        content = auth_client.get(LIST_URL).content.decode()
        assert "Jane Doe" in content

    def test_empty_state_shown_when_no_beneficiaries(self, auth_client):
        content = auth_client.get(LIST_URL).content.decode()
        assert "No beneficiaries added yet" in content

    def test_does_not_show_other_users_beneficiaries(self, auth_client, other_user):
        Beneficiary.objects.create(
            owner=other_user, name="Other Person", relationship="Friend"
        )
        content = auth_client.get(LIST_URL).content.decode()
        assert "Other Person" not in content

    def test_add_form_is_present(self, auth_client):
        content = auth_client.get(LIST_URL).content.decode()
        assert 'action="/estate/beneficiaries/add/"' in content

    def test_add_beneficiary_heading_present(self, auth_client):
        content = auth_client.get(LIST_URL).content.decode()
        assert "Add Beneficiary" in content


# ── POST create tests ─────────────────────────────────────────────────────────


class TestBeneficiaryCreate:
    def test_valid_post_creates_record(self, auth_client, user):
        auth_client.post(ADD_URL, {"name": "Bob Smith", "relationship": "Child"})
        assert Beneficiary.objects.filter(owner=user, name="Bob Smith").exists()

    def test_valid_post_redirects_to_list(self, auth_client):
        response = auth_client.post(
            ADD_URL, {"name": "Bob Smith", "relationship": "Child"}
        )
        assert response.status_code == 302
        assert response["Location"].endswith(LIST_URL)

    def test_valid_post_shows_success_toast(self, auth_client):
        response = auth_client.post(
            ADD_URL, {"name": "Bob Smith", "relationship": "Child"}, follow=True
        )
        assert "Bob Smith" in response.content.decode()

    def test_blank_name_returns_200_with_error(self, auth_client):
        response = auth_client.post(ADD_URL, {"name": "", "relationship": "Child"})
        assert response.status_code == 200

    def test_blank_name_does_not_create_record(self, auth_client, user):
        auth_client.post(ADD_URL, {"name": "", "relationship": "Child"})
        assert not Beneficiary.objects.filter(owner=user).exists()

    def test_record_owner_set_to_current_user(self, auth_client, user):
        auth_client.post(ADD_URL, {"name": "Alice", "relationship": "Sibling"})
        b = Beneficiary.objects.get(name="Alice")
        assert b.owner == user

    def test_unauthenticated_post_redirects_to_login(self):
        response = Client().post(ADD_URL, {"name": "X", "relationship": "Friend"})
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]


# ── DELETE tests ──────────────────────────────────────────────────────────────


class TestBeneficiaryDelete:
    def test_post_deletes_record(self, auth_client, beneficiary):
        auth_client.post(f"/estate/beneficiaries/{beneficiary.pk}/delete/")
        assert not Beneficiary.objects.filter(pk=beneficiary.pk).exists()

    def test_post_redirects_to_list(self, auth_client, beneficiary):
        response = auth_client.post(f"/estate/beneficiaries/{beneficiary.pk}/delete/")
        assert response.status_code == 302
        assert response["Location"].endswith(LIST_URL)

    def test_post_shows_success_message(self, auth_client, beneficiary):
        response = auth_client.post(
            f"/estate/beneficiaries/{beneficiary.pk}/delete/", follow=True
        )
        assert "Jane Doe" in response.content.decode()

    def test_get_shows_confirm_page(self, auth_client, beneficiary):
        response = auth_client.get(f"/estate/beneficiaries/{beneficiary.pk}/delete/")
        assert response.status_code == 200
        assert "Jane Doe" in response.content.decode()

    def test_other_users_beneficiary_returns_404(self, auth_client, other_user):
        other_b = Beneficiary.objects.create(
            owner=other_user, name="Theirs", relationship="Friend"
        )
        response = auth_client.post(f"/estate/beneficiaries/{other_b.pk}/delete/")
        assert response.status_code == 404
        assert Beneficiary.objects.filter(pk=other_b.pk).exists()

    def test_unauthenticated_delete_redirects_to_login(self, beneficiary):
        response = Client().post(f"/estate/beneficiaries/{beneficiary.pk}/delete/")
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]
