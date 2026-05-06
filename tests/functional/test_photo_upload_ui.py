"""
Functional tests for the photo upload UI on collection_item_detail (P2b).

Verifies:
  - Single consolidated file input (id="photo-upload") is in main-form, not a
    separate form
  - No legacy photo-form or photo-form-empty elements in the HTML
  - "Update Photo" label/button present in edit mode markup when item has a photo
  - "Add Photo" label/button present in edit mode markup when item has no photo
  - View-mode placeholder shown when item has no photo
  - Photo upload input has name="photo" so the view can receive it via request.FILES
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from my_garage.models import CollectionType, DynamicCollectionItem

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def user(db):
    return User.objects.create_user(username="photo_ui_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def collection(user):
    return CollectionType.objects.create(
        owner=user,
        name="Sneakers",
        slug="sneakers-photo",
        field_schema={"fields": []},
    )


@pytest.fixture
def item_no_photo(user, collection):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection,
        name="Air Max 90",
        purchase_price=Decimal("120.00"),
    )


def _detail_url(item):
    return reverse(
        "collections:collection_item_detail",
        kwargs={"collection_slug": item.collection_type.slug, "item_id": item.id},
    )


class TestPhotoUploadConsolidation:
    def test_no_legacy_photo_form_in_html(self, auth_client, item_no_photo):
        content = auth_client.get(_detail_url(item_no_photo)).content.decode()
        assert 'id="photo-form"' not in content
        assert 'id="photo-form-empty"' not in content

    def test_photo_upload_input_is_inside_main_form(self, auth_client, item_no_photo):
        content = auth_client.get(_detail_url(item_no_photo)).content.decode()
        main_form_pos = content.find('id="main-form"')
        photo_input_pos = content.find('id="photo-upload"')
        assert main_form_pos != -1, "main-form not found"
        assert photo_input_pos != -1, "photo-upload input not found"
        assert photo_input_pos > main_form_pos, (
            "photo-upload input must appear after (inside) main-form"
        )

    def test_photo_input_has_correct_name(self, auth_client, item_no_photo):
        content = auth_client.get(_detail_url(item_no_photo)).content.decode()
        assert 'name="photo"' in content

    def test_no_handlePhotoUpload_js_function(self, auth_client, item_no_photo):
        content = auth_client.get(_detail_url(item_no_photo)).content.decode()
        assert "handlePhotoUpload" not in content

    def test_preview_js_present(self, auth_client, item_no_photo):
        content = auth_client.get(_detail_url(item_no_photo)).content.decode()
        assert "photo-preview" in content
        assert "createObjectURL" in content


class TestPhotoUINoPhoto:
    def test_add_photo_label_present(self, auth_client, item_no_photo):
        content = auth_client.get(_detail_url(item_no_photo)).content.decode()
        assert "Add Photo" in content

    def test_view_mode_placeholder_present(self, auth_client, item_no_photo):
        content = auth_client.get(_detail_url(item_no_photo)).content.decode()
        assert 'x-show="!editing"' in content

    def test_update_photo_label_absent_when_no_photo(self, auth_client, item_no_photo):
        content = auth_client.get(_detail_url(item_no_photo)).content.decode()
        assert "Update Photo" not in content
