"""
Functional tests for the view/edit mode toggle on collection item detail pages.

Verifies:
  - Default (view) mode: field values rendered as text, "Edit Details" button present
  - Edit mode controls exist in HTML (Alpine.js toggles visibility client-side)
  - Save Changes button and form are present in the HTML output
  - Custom fields appear in view mode display
  - System fields (specs, features) are NOT shown in view mode display
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(username="detail_mode_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def sneaker_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Sneakers",
        slug="sneakers",
        field_schema={
            "fields": [
                {"name": "size", "type": "text", "label": "Size"},
                {"name": "colorway", "type": "text", "label": "Colorway"},
                {"name": "specs", "type": "system_json", "label": "Specs", "system": True},
            ]
        },
    )


@pytest.fixture
def sneaker_item(user, sneaker_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=sneaker_type,
        name="Air Jordan 1 Retro High OG",
        purchase_price=Decimal("180.00"),
        current_market_value=Decimal("420.00"),
        notes="Deadstock, original box.",
        custom_fields={
            "size": "11",
            "colorway": "Chicago",
            "specs": {"some": "data"},  # system field — should be hidden in view mode
        },
    )


def _detail_url(item):
    return reverse(
        "collections:collection_item_detail",
        kwargs={"collection_slug": item.collection_type.slug, "item_id": item.id},
    )


# ---------------------------------------------------------------------------
# View mode (default on page load)
# ---------------------------------------------------------------------------

class TestViewMode:
    def test_page_renders_ok(self, auth_client, sneaker_item):
        response = auth_client.get(_detail_url(sneaker_item))
        assert response.status_code == 200

    def test_edit_details_button_present(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "Edit Details" in content

    def test_item_name_in_heading(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert sneaker_item.name in content

    def test_purchase_price_rendered_as_text(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "180.00" in content

    def test_current_value_rendered_as_text(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "420.00" in content

    def test_notes_rendered_as_text(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "Deadstock, original box." in content

    def test_user_custom_fields_shown_in_view_mode(self, auth_client, sneaker_item):
        """Non-system custom fields (size, colorway) appear in view-mode display."""
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "Chicago" in content  # colorway value

    def test_system_fields_not_shown_in_view_mode(self, auth_client, sneaker_item):
        """system_json fields (specs) must not appear as editable or readable data."""
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "'some'" not in content

    def test_enrichment_keys_not_shown_in_view_mode(self, auth_client, user, sneaker_type):
        """specs, features, migrated keys injected by enrichment must not surface
        as display_custom_fields labels in the view-mode grid."""
        from decimal import Decimal
        item = DynamicCollectionItem.objects.create(
            owner=user,
            collection_type=sneaker_type,
            name="Test Item",
            purchase_price=Decimal("100.00"),
            custom_fields={
                "size": "10",
                "colorway": "Black",
                "specs": {"engine": "V8"},
                "features": ["sunroof"],
                "migrated": "xsentinel_migrated_val",
            },
        )
        content = auth_client.get(_detail_url(item)).content.decode()
        # If migrated leaked into display_custom_fields it would render as a
        # <dt>Migrated</dt> label — that word doesn't appear anywhere else in
        # the template, making it a reliable sentinel.
        assert "Migrated" not in content
        # If specs leaked into display_custom_fields the raw dict repr would
        # appear (the Technical Specs panel renders individual k/v pairs, not
        # the whole dict string).
        assert "&#x27;engine&#x27;" not in content


# ---------------------------------------------------------------------------
# Edit mode controls present in HTML (Alpine toggles via x-show)
# ---------------------------------------------------------------------------

class TestEditModeHTML:
    def test_alpine_x_data_attribute_present(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert 'x-data="{ editing: false }"' in content

    def test_save_changes_button_in_html(self, auth_client, sneaker_item):
        """Save Changes button is in the DOM (Alpine hides it via x-show until Edit clicked)."""
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "Save Changes" in content

    def test_cancel_button_in_html(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "Cancel" in content

    def test_form_has_post_method(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert 'method="post"' in content

    def test_delete_item_link_present(self, auth_client, sneaker_item):
        content = auth_client.get(_detail_url(sneaker_item)).content.decode()
        assert "Delete Item" in content


# ---------------------------------------------------------------------------
# POST (form submission) still works correctly
# ---------------------------------------------------------------------------

class TestEditSubmit:
    def test_post_updates_item_name(self, auth_client, sneaker_item):
        url = _detail_url(sneaker_item)
        response = auth_client.post(url, {
            "name": "Air Jordan 1 Royal Blue",
            "purchase_price": "180.00",
            "current_market_value": "420.00",
            "custom_size": "11",
            "custom_colorway": "Royal Blue",
        })
        assert response.status_code in (200, 302)
        sneaker_item.refresh_from_db()
        assert sneaker_item.name == "Air Jordan 1 Royal Blue"

    def test_post_redirects_on_success(self, auth_client, sneaker_item):
        url = _detail_url(sneaker_item)
        response = auth_client.post(url, {
            "name": sneaker_item.name,
            "purchase_price": "180.00",
            "current_market_value": "420.00",
            "custom_size": "11",
            "custom_colorway": "Chicago",
        })
        assert response.status_code == 302
