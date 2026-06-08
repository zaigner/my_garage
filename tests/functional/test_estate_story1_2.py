"""
Functional tests for Story 1.2: Executor Designation.

Covers:
  - GET /estate/executor/ — 200 for auth, 302 for anon
  - Empty state shown when no executor designated
  - "Designate Executor" button visible in empty state
  - POST valid form creates EstateExecutor record
  - POST sets owner to request.user
  - POST redirects and shows success toast
  - GET shows current executor details when one exists
  - "Update" and "Remove" actions present when executor exists
  - POST to existing executor updates (no duplicate record created)
  - POST /estate/executor/remove/ deletes record, redirects, shows success toast
  - POST /estate/executor/remove/ with no executor is a no-op (no crash)
  - POST with blank name returns 200 with form error, no record created
  - Unauthenticated GET and POST redirect to login
  - OneToOne: second POST updates, does not create a second row
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import EstateExecutor

User = get_user_model()

pytestmark = pytest.mark.django_db

EXECUTOR_URL = "/estate/executor/"
REMOVE_URL = "/estate/executor/remove/"


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(username="exec_user", password="pass")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="other_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def executor(user):
    return EstateExecutor.objects.create(
        owner=user,
        name="John Doe",
        contact_info="john@example.com",
    )


# ── GET — unauthenticated & authenticated ─────────────────────────────────────


class TestExecutorViewGET:
    def test_returns_200_for_authenticated_user(self, auth_client):
        assert auth_client.get(EXECUTOR_URL).status_code == 200

    def test_redirects_unauthenticated_to_login(self):
        response = Client().get(EXECUTOR_URL)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_empty_state_shown_when_no_executor(self, auth_client):
        content = auth_client.get(EXECUTOR_URL).content.decode()
        assert "Designate an Executor" in content

    def test_designate_executor_button_visible_in_empty_state(self, auth_client):
        content = auth_client.get(EXECUTOR_URL).content.decode()
        assert "Designate Executor" in content

    def test_shows_current_executor_name(self, auth_client, executor):
        content = auth_client.get(EXECUTOR_URL).content.decode()
        assert "John Doe" in content

    def test_shows_current_executor_contact(self, auth_client, executor):
        content = auth_client.get(EXECUTOR_URL).content.decode()
        assert "john@example.com" in content

    def test_shows_current_executor_heading(self, auth_client, executor):
        content = auth_client.get(EXECUTOR_URL).content.decode()
        assert "Current Executor" in content

    def test_update_action_visible_when_executor_exists(self, auth_client, executor):
        content = auth_client.get(EXECUTOR_URL).content.decode()
        assert "Update" in content

    def test_remove_action_visible_when_executor_exists(self, auth_client, executor):
        content = auth_client.get(EXECUTOR_URL).content.decode()
        assert "Remove" in content


# ── POST create ───────────────────────────────────────────────────────────────


class TestExecutorCreate:
    def test_valid_post_creates_record(self, auth_client, user):
        auth_client.post(EXECUTOR_URL, {"name": "Alice Smith", "contact_info": ""})
        assert EstateExecutor.objects.filter(owner=user, name="Alice Smith").exists()

    def test_record_owner_set_to_current_user(self, auth_client, user):
        auth_client.post(EXECUTOR_URL, {"name": "Alice Smith", "contact_info": ""})
        executor = EstateExecutor.objects.get(owner=user)
        assert executor.name == "Alice Smith"

    def test_valid_post_redirects_to_executor_page(self, auth_client):
        response = auth_client.post(
            EXECUTOR_URL, {"name": "Alice Smith", "contact_info": ""}
        )
        assert response.status_code == 302
        assert response["Location"].endswith(EXECUTOR_URL)

    def test_valid_post_shows_success_toast(self, auth_client):
        response = auth_client.post(
            EXECUTOR_URL,
            {"name": "Alice Smith", "contact_info": ""},
            follow=True,
        )
        assert "Executor designated successfully" in response.content.decode()

    def test_blank_name_returns_200(self, auth_client):
        response = auth_client.post(EXECUTOR_URL, {"name": "", "contact_info": ""})
        assert response.status_code == 200

    def test_blank_name_does_not_create_record(self, auth_client, user):
        auth_client.post(EXECUTOR_URL, {"name": "", "contact_info": ""})
        assert not EstateExecutor.objects.filter(owner=user).exists()

    def test_unauthenticated_post_redirects_to_login(self):
        response = Client().post(EXECUTOR_URL, {"name": "X", "contact_info": ""})
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]


# ── POST update (OneToOne — no duplicate) ─────────────────────────────────────


class TestExecutorUpdate:
    def test_second_post_updates_existing_record(self, auth_client, user, executor):
        auth_client.post(
            EXECUTOR_URL, {"name": "Jane Updated", "contact_info": "jane@new.com"}
        )
        executor.refresh_from_db()
        assert executor.name == "Jane Updated"

    def test_second_post_does_not_create_second_row(self, auth_client, user, executor):
        auth_client.post(EXECUTOR_URL, {"name": "Jane Updated", "contact_info": ""})
        assert EstateExecutor.objects.filter(owner=user).count() == 1

    def test_update_post_redirects(self, auth_client, executor):
        response = auth_client.post(
            EXECUTOR_URL, {"name": "Jane Updated", "contact_info": ""}
        )
        assert response.status_code == 302
        assert response["Location"].endswith(EXECUTOR_URL)


# ── POST remove ───────────────────────────────────────────────────────────────


class TestExecutorRemove:
    def test_post_deletes_record(self, auth_client, user, executor):
        auth_client.post(REMOVE_URL)
        assert not EstateExecutor.objects.filter(owner=user).exists()

    def test_post_redirects_to_executor_page(self, auth_client, executor):
        response = auth_client.post(REMOVE_URL)
        assert response.status_code == 302
        assert response["Location"].endswith(EXECUTOR_URL)

    def test_post_shows_success_message(self, auth_client, executor):
        response = auth_client.post(REMOVE_URL, follow=True)
        assert "Executor removed" in response.content.decode()

    def test_post_with_no_executor_is_safe(self, auth_client, user):
        assert not EstateExecutor.objects.filter(owner=user).exists()
        response = auth_client.post(REMOVE_URL)
        assert response.status_code == 302

    def test_get_remove_redirects_to_executor(self, auth_client):
        response = auth_client.get(REMOVE_URL)
        assert response.status_code == 302
        assert response["Location"].endswith(EXECUTOR_URL)

    def test_unauthenticated_remove_redirects_to_login(self, executor):
        response = Client().post(REMOVE_URL)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_other_users_executor_not_deleted(self, auth_client, other_user):
        other_executor = EstateExecutor.objects.create(
            owner=other_user, name="Other Exec"
        )
        auth_client.post(REMOVE_URL)
        assert EstateExecutor.objects.filter(pk=other_executor.pk).exists()
