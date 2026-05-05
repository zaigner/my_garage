"""
Functional tests for the home page navigation bar.

Covers:
  - Profile/user button has correct aria-label (not a search trigger)
  - Profile dropdown shows signed-in username
  - Profile dropdown contains sign-out action
  - The magnifying-glass search path is NOT used for the profile button
  - Unauthenticated visitors see a login link instead of the profile button
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()

HOME_URL = "/"

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(db):
    return User.objects.create_user(username="nav_test_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


class TestNavProfileButton:
    def test_user_menu_aria_label_present(self, auth_client):
        """Profile button must declare itself as a user menu, not a search."""
        response = auth_client.get(HOME_URL)
        assert 'aria-label="User menu"' in response.content.decode()

    def test_search_icon_path_not_on_profile_button(self, auth_client):
        """The magnifying-glass SVG path must not appear inside the profile button group."""
        content = response_content = auth_client.get(HOME_URL).content.decode()
        # The old incorrect path for the magnifying glass was:
        old_search_path = "M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196"
        assert old_search_path not in content

    def test_profile_dropdown_shows_username(self, auth_client, user):
        response = auth_client.get(HOME_URL)
        assert user.username in response.content.decode()

    def test_profile_dropdown_has_sign_out(self, auth_client):
        response = auth_client.get(HOME_URL)
        assert "Sign Out" in response.content.decode()

    def test_unauthenticated_shows_login_link(self):
        response = Client().get(HOME_URL)
        content = response.content.decode()
        assert "Login" in content
        assert "Sign Out" not in content
        assert "aria-label=\"User menu\"" not in content
