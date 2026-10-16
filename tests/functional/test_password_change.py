"""
Functional tests for the password change pages (/accounts/password_change/).

Covers:
  - GET: the salon-styled template is used, not the django.contrib.admin one
  - GET: redirect to login for unauthenticated users
  - POST: valid change updates the password, keeps the session, and redirects
    to the done page
  - POST: wrong old password / mismatched / weak passwords re-render with errors
  - Done page: salon-styled, links back to profile and home
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()

pytestmark = pytest.mark.django_db

CHANGE_URL = "/accounts/password_change/"
DONE_URL = "/accounts/password_change/done/"
OLD_PASSWORD = "testpass123"
NEW_PASSWORD = "Velvet-Cellar-2026"


@pytest.fixture
def user(db):
    return User.objects.create_user(username="pw_user", password=OLD_PASSWORD)


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


def _post(client, old=OLD_PASSWORD, new1=NEW_PASSWORD, new2=NEW_PASSWORD):
    return client.post(
        CHANGE_URL,
        {"old_password": old, "new_password1": new1, "new_password2": new2},
    )


class TestPasswordChangeForm:
    def test_uses_salon_template_not_admin(self, auth_client):
        response = auth_client.get(CHANGE_URL)
        assert response.status_code == 200
        names = [t.name for t in response.templates]
        assert "registration/password_change_form.html" in names
        assert "registration/_auth_card_base.html" in names
        assert "admin/base_site.html" not in names
        assert "Django administration" not in response.content.decode()

    def test_renders_all_three_fields(self, auth_client):
        content = auth_client.get(CHANGE_URL).content.decode()
        for name in ("old_password", "new_password1", "new_password2"):
            assert f'name="{name}"' in content

    def test_links_back_to_profile(self, auth_client):
        content = auth_client.get(CHANGE_URL).content.decode()
        assert 'href="/accounts/profile/"' in content

    def test_unauthenticated_redirects_to_login(self):
        response = Client().get(CHANGE_URL)
        assert response.status_code == 302
        assert response.url.startswith("/accounts/login/")


class TestPasswordChangeSubmit:
    def test_valid_change_updates_password_and_keeps_session(self, auth_client, user):
        response = _post(auth_client)
        assert response.status_code == 302
        assert response.url == DONE_URL
        user.refresh_from_db()
        assert user.check_password(NEW_PASSWORD)
        # Django rotates the session hash, so the user stays signed in.
        assert auth_client.get("/accounts/profile/").status_code == 200

    def test_wrong_old_password_shows_error(self, auth_client, user):
        response = _post(auth_client, old="not-my-password")
        assert response.status_code == 200
        assert "old_password" in response.context["form"].errors
        assert 'class="errorlist' in response.content.decode()
        user.refresh_from_db()
        assert user.check_password(OLD_PASSWORD)

    def test_mismatched_new_passwords_show_error(self, auth_client):
        response = _post(auth_client, new2="Different-Cellar-2026")
        assert response.status_code == 200
        assert "new_password2" in response.context["form"].errors

    def test_weak_password_rejected_by_validators(self, auth_client):
        response = _post(auth_client, new1="12345678", new2="12345678")
        assert response.status_code == 200
        assert "new_password2" in response.context["form"].errors


class TestPasswordChangeDone:
    def test_done_page_uses_salon_template(self, auth_client):
        response = auth_client.get(DONE_URL)
        assert response.status_code == 200
        names = [t.name for t in response.templates]
        assert "registration/password_change_done.html" in names
        assert "admin/base_site.html" not in names

    def test_done_page_links_to_profile_and_home(self, auth_client):
        content = auth_client.get(DONE_URL).content.decode()
        assert 'href="/accounts/profile/"' in content
        assert 'href="/"' in content
