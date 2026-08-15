"""
Functional tests for starter-collection provisioning.

The headline case is two users adopting the same blueprint: CollectionType.slug
used to carry a global unique constraint, so the second user hit an IntegrityError.
Uniqueness is now scoped to (owner, slug), which also means every user's
automobiles collection lives at the same stable URL.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from my_garage.collection_blueprints import COLLECTION_BLUEPRINTS
from my_garage.models import CollectionType, DynamicCollectionItem
from my_garage.services.collection_provisioning import (
    get_catalog,
    provision_collections,
)

User = get_user_model()

ALL_SLUGS = [bp["slug"] for bp in COLLECTION_BLUEPRINTS]


@pytest.fixture
def alice(db):
    return User.objects.create_user(username="alice", password="pass")


@pytest.fixture
def bob(db):
    return User.objects.create_user(username="bob", password="pass")


# ---------------------------------------------------------------------------
# provision_collections
# ---------------------------------------------------------------------------


class TestProvisioning:
    def test_creates_requested_collections(self, alice):
        created = provision_collections(alice, ["automobiles", "wine-collection"])
        assert {c.slug for c in created} == {"automobiles", "wine-collection"}
        assert CollectionType.objects.filter(owner=alice).count() == 2

    def test_collections_arrive_fully_formed(self, alice):
        (ctype,) = provision_collections(alice, ["horology-salon"])
        assert ctype.name == "Horology Salon"
        assert ctype.icon == "fa-solid fa-clock"
        assert ctype.service_provider_key == "timepiece"
        assert ctype.is_system is True
        assert ctype.description
        assert ctype.list_display_fields
        assert len(ctype.field_schema["fields"]) == 12

    def test_theme_is_attached_when_blueprint_has_one(self, alice):
        (ctype,) = provision_collections(alice, ["coin-collection"])
        assert len(ctype.ui_theme_html) > 1000

    def test_blueprint_without_theme_gets_blank(self, alice):
        (ctype,) = provision_collections(alice, ["wine-collection"])
        assert ctype.ui_theme_html == ""

    def test_slug_is_preserved_verbatim(self, alice):
        (ctype,) = provision_collections(alice, ["automobiles"])
        # Not "automobiles-1" — hardcoded slug routes depend on this.
        assert ctype.slug == "automobiles"

    def test_unknown_slugs_are_ignored(self, alice):
        created = provision_collections(alice, ["automobiles", "not-a-blueprint"])
        assert [c.slug for c in created] == ["automobiles"]

    def test_empty_selection_is_a_noop(self, alice):
        assert provision_collections(alice, []) == []
        assert CollectionType.objects.filter(owner=alice).count() == 0

    def test_returns_catalogue_order(self, alice):
        created = provision_collections(alice, ["wine-collection", "automobiles"])
        assert [c.slug for c in created] == ["automobiles", "wine-collection"]

    def test_all_blueprints_provision_cleanly(self, alice):
        created = provision_collections(alice, ALL_SLUGS)
        assert len(created) == len(ALL_SLUGS)


class TestIdempotency:
    def test_second_run_creates_nothing(self, alice):
        provision_collections(alice, ["automobiles"])
        assert provision_collections(alice, ["automobiles"]) == []
        assert (
            CollectionType.objects.filter(owner=alice, slug="automobiles").count() == 1
        )

    def test_does_not_overwrite_a_user_built_collection(self, alice):
        mine = CollectionType.objects.create(
            owner=alice,
            slug="automobiles",
            name="My Own Cars",
            field_schema={"fields": []},
        )
        assert provision_collections(alice, ["automobiles"]) == []
        mine.refresh_from_db()
        assert mine.name == "My Own Cars"
        assert mine.field_schema == {"fields": []}

    def test_partial_reprovision_adds_only_the_missing(self, alice):
        provision_collections(alice, ["automobiles"])
        created = provision_collections(alice, ["automobiles", "hand-bags"])
        assert [c.slug for c in created] == ["hand-bags"]


class TestMultipleUsers:
    def test_two_users_can_adopt_the_same_blueprint(self, alice, bob):
        """Regression: slug was globally unique, so this raised IntegrityError."""
        provision_collections(alice, ["wine-collection"])
        provision_collections(bob, ["wine-collection"])

        assert CollectionType.objects.filter(slug="wine-collection").count() == 2
        assert CollectionType.objects.get(owner=alice, slug="wine-collection")
        assert CollectionType.objects.get(owner=bob, slug="wine-collection")

    def test_every_blueprint_survives_two_users(self, alice, bob):
        provision_collections(alice, ALL_SLUGS)
        provision_collections(bob, ALL_SLUGS)
        assert CollectionType.objects.count() == len(ALL_SLUGS) * 2

    def test_users_get_identical_slugs(self, alice, bob):
        (a,) = provision_collections(alice, ["automobiles"])
        (b,) = provision_collections(bob, ["automobiles"])
        assert a.slug == b.slug == "automobiles"

    def test_provisioning_does_not_leak_across_owners(self, alice, bob):
        provision_collections(alice, ["automobiles"])
        assert CollectionType.objects.filter(owner=bob).count() == 0


# ---------------------------------------------------------------------------
# get_catalog
# ---------------------------------------------------------------------------


class TestCatalog:
    def test_lists_every_blueprint(self, alice):
        assert len(get_catalog(alice)) == len(COLLECTION_BLUEPRINTS)

    def test_nothing_owned_initially(self, alice):
        assert not any(e["already_owned"] for e in get_catalog(alice))

    def test_marks_owned_after_provisioning(self, alice):
        provision_collections(alice, ["automobiles"])
        by_slug = {e["slug"]: e for e in get_catalog(alice)}
        assert by_slug["automobiles"]["already_owned"] is True
        assert by_slug["wine-collection"]["already_owned"] is False

    def test_ownership_is_per_user(self, alice, bob):
        provision_collections(alice, ["automobiles"])
        by_slug = {e["slug"]: e for e in get_catalog(bob)}
        assert by_slug["automobiles"]["already_owned"] is False

    def test_field_count_excludes_system_fields(self, alice):
        by_slug = {e["slug"]: e for e in get_catalog(alice)}
        # Automobiles has 12 fields, 2 of them system_json.
        assert by_slug["automobiles"]["field_count"] == 10

    def test_entries_carry_display_metadata(self, alice):
        entry = get_catalog(alice)[0]
        assert {"slug", "name", "icon", "description", "preview"} <= set(entry)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


class TestOnboardingPicker:
    def test_requires_login(self, client, db):
        response = client.get(reverse("onboarding"))
        assert response.status_code == 302

    def test_lists_the_catalogue(self, client, alice):
        client.force_login(alice)
        response = client.get(reverse("onboarding"))
        assert response.status_code == 200
        assert len(response.context["catalog"]) == len(COLLECTION_BLUEPRINTS)

    def test_post_provisions_selected(self, client, alice):
        client.force_login(alice)
        response = client.post(
            reverse("onboarding"),
            {"blueprints": ["automobiles", "coin-collection"]},
        )
        assert response.status_code == 302
        assert set(
            CollectionType.objects.filter(owner=alice).values_list("slug", flat=True)
        ) == {"automobiles", "coin-collection"}

    def test_post_creates_no_items(self, client, alice):
        """Adopting a collection provides the schema, not sample data."""
        client.force_login(alice)
        client.post(reverse("onboarding"), {"blueprints": ["automobiles"]})
        assert DynamicCollectionItem.objects.filter(owner=alice).count() == 0

    def test_post_with_nothing_selected(self, client, alice):
        client.force_login(alice)
        response = client.post(reverse("onboarding"), {})
        assert response.status_code == 302
        assert CollectionType.objects.filter(owner=alice).count() == 0

    def test_post_ignores_unknown_slug(self, client, alice):
        client.force_login(alice)
        client.post(reverse("onboarding"), {"blueprints": ["../../etc/passwd"]})
        assert CollectionType.objects.filter(owner=alice).count() == 0

    def test_all_adopted_flag(self, client, alice):
        client.force_login(alice)
        provision_collections(alice, ALL_SLUGS)
        response = client.get(reverse("onboarding"))
        assert response.context["all_adopted"] is True


class TestTemplatesPage:
    def test_requires_login(self, client, db):
        response = client.get(reverse("collections:collection_templates"))
        assert response.status_code == 302

    def test_renders_catalogue(self, client, alice):
        client.force_login(alice)
        response = client.get(reverse("collections:collection_templates"))
        assert response.status_code == 200
        assert len(response.context["catalog"]) == len(COLLECTION_BLUEPRINTS)

    def test_post_provisions_and_redirects_to_list(self, client, alice):
        client.force_login(alice)
        response = client.post(
            reverse("collections:collection_templates"),
            {"blueprints": ["hand-bags"]},
        )
        assert response.status_code == 302
        assert response.url == reverse("collections:collection_type_list")
        assert CollectionType.objects.filter(owner=alice, slug="hand-bags").exists()

    def test_list_page_hides_prompt_once_all_adopted(self, client, alice):
        client.force_login(alice)
        provision_collections(alice, ALL_SLUGS)
        response = client.get(reverse("collections:collection_type_list"))
        assert response.context["has_unadopted_templates"] is False

    def test_list_page_shows_prompt_when_templates_remain(self, client, alice):
        client.force_login(alice)
        response = client.get(reverse("collections:collection_type_list"))
        assert response.context["has_unadopted_templates"] is True
