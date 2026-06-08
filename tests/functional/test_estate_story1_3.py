"""
Functional tests for Story 1.3: Per-Item Beneficiary Assignment & Change History.

Covers:
  - GET item detail includes Estate Assignment section
  - POST /estate/assign/<slug>/items/<id>/ creates BeneficiaryAssignment
  - POST creates EstateChangeLog with action=ASSIGNED
  - POST with existing assignment updates (no duplicate) and logs CHANGED
  - POST charitable designation: is_charitable=True, org stored, beneficiary=None
  - POST /estate/assign/<slug>/items/<id>/remove/ deletes assignment and logs REMOVED
  - Beneficiary SET_NULL: deleting beneficiary leaves assignment with beneficiary=None
  - Owner isolation: cannot assign/remove another user's item
  - GET /estate/assign/ lists all items with assignment status
  - Unassigned items shown with Unassigned badge
  - Quality gate: all tests pass
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
)

User = get_user_model()

pytestmark = pytest.mark.django_db

OVERVIEW_URL = "/estate/assign/"


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
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Test Collection",
        slug="test-collection",
        field_schema={"fields": []},
    )


@pytest.fixture
def item(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Test Watch",
    )


@pytest.fixture
def beneficiary(user):
    return Beneficiary.objects.create(
        owner=user,
        name="Jane Doe",
        relationship="Spouse",
    )


def assign_url(collection_type, item):
    return f"/estate/assign/{collection_type.slug}/items/{item.id}/"


def remove_url(collection_type, item):
    return f"/estate/assign/{collection_type.slug}/items/{item.id}/remove/"


def detail_url(collection_type, item):
    return f"/collections/{collection_type.slug}/items/{item.id}/"


def assign_payload(beneficiary=None, note="", charitable=False, org=""):
    return {
        "beneficiary": beneficiary.pk if beneficiary else "",
        "conditional_note": note,
        "is_charitable": charitable,
        "charitable_org": org,
    }


# ── Item detail includes estate section ───────────────────────────────────────


class TestItemDetailEstateSection:
    def test_estate_section_heading_present(self, auth_client, item, collection_type):
        content = auth_client.get(detail_url(collection_type, item)).content.decode()
        assert "Estate Assignment" in content

    def test_unassigned_state_shown(self, auth_client, item, collection_type):
        content = auth_client.get(detail_url(collection_type, item)).content.decode()
        assert "Unassigned" in content

    def test_assign_form_present(self, auth_client, item, collection_type):
        content = auth_client.get(detail_url(collection_type, item)).content.decode()
        assert f'action="{assign_url(collection_type, item)}"' in content

    def test_assigned_beneficiary_name_shown(
        self, auth_client, item, collection_type, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        content = auth_client.get(detail_url(collection_type, item)).content.decode()
        assert "Jane Doe" in content

    def test_remove_button_shown_when_assigned(
        self, auth_client, item, collection_type, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        content = auth_client.get(detail_url(collection_type, item)).content.decode()
        assert remove_url(collection_type, item) in content


# ── POST assign ───────────────────────────────────────────────────────────────


class TestItemAssignPOST:
    def test_creates_assignment_record(
        self, auth_client, item, collection_type, beneficiary
    ):
        auth_client.post(assign_url(collection_type, item), assign_payload(beneficiary))
        assert BeneficiaryAssignment.objects.filter(item=item).exists()

    def test_assignment_links_correct_beneficiary(
        self, auth_client, item, collection_type, beneficiary
    ):
        auth_client.post(assign_url(collection_type, item), assign_payload(beneficiary))
        a = BeneficiaryAssignment.objects.get(item=item)
        assert a.beneficiary == beneficiary

    def test_logs_assigned_action(
        self, auth_client, user, item, collection_type, beneficiary
    ):
        auth_client.post(assign_url(collection_type, item), assign_payload(beneficiary))
        assert EstateChangeLog.objects.filter(owner=user, action="ASSIGNED").exists()

    def test_redirects_to_item_detail(
        self, auth_client, item, collection_type, beneficiary
    ):
        response = auth_client.post(
            assign_url(collection_type, item), assign_payload(beneficiary)
        )
        assert response.status_code == 302
        assert response["Location"].endswith(detail_url(collection_type, item))

    def test_shows_success_toast(self, auth_client, item, collection_type, beneficiary):
        response = auth_client.post(
            assign_url(collection_type, item),
            assign_payload(beneficiary),
            follow=True,
        )
        assert "Estate assignment saved" in response.content.decode()

    def test_conditional_note_stored(
        self, auth_client, item, collection_type, beneficiary
    ):
        auth_client.post(
            assign_url(collection_type, item),
            assign_payload(beneficiary, note="Only if over 25"),
        )
        a = BeneficiaryAssignment.objects.get(item=item)
        assert a.conditional_note == "Only if over 25"

    def test_charitable_designation_stores_correctly(
        self, auth_client, item, collection_type
    ):
        auth_client.post(
            assign_url(collection_type, item),
            assign_payload(charitable=True, org="Red Cross"),
        )
        a = BeneficiaryAssignment.objects.get(item=item)
        assert a.is_charitable is True
        assert a.charitable_org == "Red Cross"
        assert a.beneficiary is None

    def test_update_does_not_create_duplicate(
        self, auth_client, item, collection_type, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        auth_client.post(
            assign_url(collection_type, item),
            assign_payload(beneficiary, note="Updated"),
        )
        assert BeneficiaryAssignment.objects.filter(item=item).count() == 1

    def test_update_logs_changed_action(
        self, auth_client, user, item, collection_type, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        auth_client.post(
            assign_url(collection_type, item),
            assign_payload(beneficiary, note="Updated"),
        )
        assert EstateChangeLog.objects.filter(owner=user, action="CHANGED").exists()

    def test_get_redirects_to_item_detail(self, auth_client, item, collection_type):
        response = auth_client.get(assign_url(collection_type, item))
        assert response.status_code == 302
        assert response["Location"].endswith(detail_url(collection_type, item))

    def test_other_users_item_returns_404(
        self, auth_client, other_user, collection_type
    ):
        other_ct = CollectionType.objects.create(
            owner=other_user,
            name="Other",
            slug="other",
            field_schema={"fields": []},
        )
        other_item = DynamicCollectionItem.objects.create(
            owner=other_user,
            collection_type=other_ct,
            name="Other Item",
        )
        response = auth_client.post(
            f"/estate/assign/{other_ct.slug}/items/{other_item.id}/",
            assign_payload(),
        )
        assert response.status_code == 404


# ── POST remove ───────────────────────────────────────────────────────────────


class TestItemAssignRemove:
    def test_deletes_assignment(
        self, auth_client, user, item, collection_type, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        auth_client.post(remove_url(collection_type, item))
        assert not BeneficiaryAssignment.objects.filter(item=item).exists()

    def test_logs_removed_action(
        self, auth_client, user, item, collection_type, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        auth_client.post(remove_url(collection_type, item))
        assert EstateChangeLog.objects.filter(owner=user, action="REMOVED").exists()

    def test_redirects_to_item_detail(
        self, auth_client, item, collection_type, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        response = auth_client.post(remove_url(collection_type, item))
        assert response.status_code == 302
        assert response["Location"].endswith(detail_url(collection_type, item))

    def test_shows_success_toast(self, auth_client, item, collection_type, beneficiary):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        response = auth_client.post(remove_url(collection_type, item), follow=True)
        assert "Estate assignment removed" in response.content.decode()

    def test_no_assignment_is_safe(self, auth_client, item, collection_type):
        response = auth_client.post(remove_url(collection_type, item))
        assert response.status_code == 302

    def test_get_redirects_to_item_detail(self, auth_client, item, collection_type):
        response = auth_client.get(remove_url(collection_type, item))
        assert response.status_code == 302
        assert response["Location"].endswith(detail_url(collection_type, item))


# ── Beneficiary SET_NULL cascade ──────────────────────────────────────────────


class TestBeneficiaryDeleteCascade:
    def test_assignment_survives_beneficiary_deletion(
        self, item, collection_type, beneficiary
    ):
        a = BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        beneficiary.delete()
        a.refresh_from_db()
        assert a.beneficiary is None

    def test_assignment_record_still_exists_after_beneficiary_deletion(
        self, item, collection_type, beneficiary
    ):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        beneficiary.delete()
        assert BeneficiaryAssignment.objects.filter(item=item).exists()


# ── /estate/assign/ overview ──────────────────────────────────────────────────


class TestAssignOverview:
    def test_returns_200_for_authenticated_user(self, auth_client):
        assert auth_client.get(OVERVIEW_URL).status_code == 200

    def test_redirects_unauthenticated(self):
        response = Client().get(OVERVIEW_URL)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_lists_items(self, auth_client, item):
        content = auth_client.get(OVERVIEW_URL).content.decode()
        assert "Test Watch" in content

    def test_unassigned_badge_shown(self, auth_client, item):
        content = auth_client.get(OVERVIEW_URL).content.decode()
        assert "Unassigned" in content

    def test_assigned_beneficiary_name_shown(self, auth_client, item, beneficiary):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        content = auth_client.get(OVERVIEW_URL).content.decode()
        assert "Jane Doe" in content

    def test_does_not_show_other_users_items(self, auth_client, other_user):
        other_ct = CollectionType.objects.create(
            owner=other_user,
            name="Other",
            slug="other2",
            field_schema={"fields": []},
        )
        DynamicCollectionItem.objects.create(
            owner=other_user,
            collection_type=other_ct,
            name="Theirs",
        )
        content = auth_client.get(OVERVIEW_URL).content.decode()
        assert "Theirs" not in content
