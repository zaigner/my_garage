"""
Unit tests for my_garage.context_processors.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from my_garage.context_processors import user_collections
from my_garage.models import CollectionType

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(db):
    return User.objects.create_user(username="ctx_proc_user", password="pass")


@pytest.fixture
def rf():
    return RequestFactory()


class TestUserCollectionsContextProcessor:
    def test_unauthenticated_returns_empty_list(self, rf):
        request = rf.get("/")
        request.user = type("AnonymousUser", (), {"is_authenticated": False})()
        ctx = user_collections(request)
        assert ctx == {"quick_add_collections": []}

    def test_authenticated_user_with_no_collections(self, rf, user):
        request = rf.get("/")
        request.user = user
        ctx = user_collections(request)
        assert ctx["quick_add_collections"] == []

    def test_authenticated_user_sees_their_collections(self, rf, user):
        CollectionType.objects.create(owner=user, name="Sneakers", slug="sneakers")
        CollectionType.objects.create(owner=user, name="Wine", slug="wine")
        request = rf.get("/")
        request.user = user
        ctx = user_collections(request)
        names = [c.name for c in ctx["quick_add_collections"]]
        assert "Sneakers" in names
        assert "Wine" in names

    def test_inactive_collections_excluded(self, rf, user):
        CollectionType.objects.create(
            owner=user, name="Active", slug="active", is_active=True
        )
        CollectionType.objects.create(
            owner=user, name="Inactive", slug="inactive", is_active=False
        )
        request = rf.get("/")
        request.user = user
        ctx = user_collections(request)
        names = [c.name for c in ctx["quick_add_collections"]]
        assert "Active" in names
        assert "Inactive" not in names

    def test_other_users_collections_excluded(self, rf, user, db):
        other = User.objects.create_user(username="other_user", password="pass")
        CollectionType.objects.create(owner=other, name="OtherCollection", slug="other")
        request = rf.get("/")
        request.user = user
        ctx = user_collections(request)
        names = [c.name for c in ctx["quick_add_collections"]]
        assert "OtherCollection" not in names

    def test_collections_ordered_by_name(self, rf, user):
        CollectionType.objects.create(owner=user, name="Zephyr", slug="zephyr")
        CollectionType.objects.create(owner=user, name="Alpha", slug="alpha")
        CollectionType.objects.create(owner=user, name="Mango", slug="mango")
        request = rf.get("/")
        request.user = user
        ctx = user_collections(request)
        names = [c.name for c in ctx["quick_add_collections"]]
        assert names == sorted(names)
