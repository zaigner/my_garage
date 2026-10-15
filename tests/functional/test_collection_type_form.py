"""
Functional tests for the collection type create/edit form.

The AI "Generate UI" feature was removed from this form. These tests pin
down that it is gone, that the rest of the form still works, and that saving
the form never wipes a theme a collection already has (e.g. the Coin
Collection blueprint theme).
"""

import json
import re

import pytest
from django.urls import NoReverseMatch, reverse

from my_garage.models import CollectionType

pytestmark = pytest.mark.django_db

THEME_HTML = '<div id="stored-theme">{{ collection_type.name }} themed</div>'


@pytest.fixture
def themed_type(collection_type):
    collection_type.ui_theme_html = THEME_HTML
    collection_type.save()
    return collection_type


def _form_post(name, schema_fields=None, **extra):
    fields = schema_fields or []
    return {
        "name": name,
        "icon": "fa-solid fa-layer-group",
        "description": "Updated description",
        "is_active": "on",
        "field_schema_json": json.dumps({"fields": fields}),
        "list_display_fields_json": json.dumps([f["name"] for f in fields]),
        **extra,
    }


def _has_id(html: str, element_id: str) -> bool:
    return re.search(rf'id="{element_id}"', html) is not None


class TestGenerateUiRemovedFromForm:
    def test_edit_page_has_no_generate_ui_controls(self, auth_client, themed_type):
        response = auth_client.get(
            reverse("collections:collection_type_edit", args=[themed_type.slug])
        )
        assert response.status_code == 200
        html = response.content.decode()
        for element_id in (
            "generate-ui-btn",
            "ui-preview-container",
            "regenerate-ui-btn",
            "accept-ui-btn",
            "reset-ui-btn",
            "preview-full-btn",
            "ui-theme-html",
        ):
            assert not _has_id(html, element_id), element_id

    def test_edit_page_does_not_leak_stored_theme(self, auth_client, themed_type):
        response = auth_client.get(
            reverse("collections:collection_type_edit", args=[themed_type.slug])
        )
        assert "stored-theme" not in response.content.decode()

    def test_edit_page_keeps_schema_tools(self, auth_client, collection_type):
        response = auth_client.get(
            reverse("collections:collection_type_edit", args=[collection_type.slug])
        )
        html = response.content.decode()
        assert _has_id(html, "generate-schema-btn")
        assert _has_id(html, "add-field-btn")
        assert _has_id(html, "field-schema-json")

    def test_automobiles_edit_page_renders(self, auth_client, automobiles_type):
        response = auth_client.get(
            reverse("collections:collection_type_edit", args=["automobiles"])
        )
        assert response.status_code == 200
        assert not _has_id(response.content.decode(), "generate-ui-btn")

    def test_create_page_has_no_generate_ui_controls(self, auth_client):
        response = auth_client.get(reverse("collections:collection_type_create"))
        assert response.status_code == 200
        assert not _has_id(response.content.decode(), "generate-ui-btn")

    @pytest.mark.parametrize("path", ["api/generate-ui/", "api/preview-ui/"])
    def test_removed_endpoints_return_404(self, auth_client, path):
        assert auth_client.get(f"/collections/{path}").status_code == 404
        assert auth_client.post(f"/collections/{path}").status_code == 404

    @pytest.mark.parametrize(
        "name", ["generate_collection_ui", "preview_collection_ui"]
    )
    def test_removed_url_names(self, name):
        with pytest.raises(NoReverseMatch):
            reverse(f"collections:{name}")


class TestCollectionTypeEditSave:
    def test_edit_saves_fields_and_schema(self, auth_client, collection_type):
        fields = [{"name": "brand", "type": "text", "label": "Brand"}]
        response = auth_client.post(
            reverse("collections:collection_type_edit", args=[collection_type.slug]),
            _form_post("Sneaker Vault", fields),
        )
        assert response.status_code == 302
        collection_type.refresh_from_db()
        assert collection_type.name == "Sneaker Vault"
        assert collection_type.description == "Updated description"
        assert collection_type.field_schema == {"fields": fields}
        assert collection_type.list_display_fields == ["brand"]

    def test_edit_preserves_existing_theme(self, auth_client, themed_type):
        response = auth_client.post(
            reverse("collections:collection_type_edit", args=[themed_type.slug]),
            _form_post("Sneaker Collection"),
        )
        assert response.status_code == 302
        themed_type.refresh_from_db()
        assert themed_type.ui_theme_html == THEME_HTML

    def test_edit_ignores_posted_theme(self, auth_client, themed_type):
        auth_client.post(
            reverse("collections:collection_type_edit", args=[themed_type.slug]),
            _form_post("Sneaker Collection", ui_theme_html="<p>injected</p>"),
        )
        themed_type.refresh_from_db()
        assert themed_type.ui_theme_html == THEME_HTML

    def test_create_has_no_theme(self, auth_client, user):
        response = auth_client.post(
            reverse("collections:collection_type_create"),
            _form_post("Rare Coins", ui_theme_html="<p>injected</p>"),
        )
        assert response.status_code == 302
        created = CollectionType.objects.get(owner=user, name="Rare Coins")
        assert created.ui_theme_html == ""


class TestStoredThemesStillRender:
    def test_themed_collection_list_uses_theme(self, auth_client, themed_type):
        response = auth_client.get(
            reverse("collections:collection_list", args=[themed_type.slug])
        )
        assert response.status_code == 200
        html = response.content.decode()
        assert _has_id(html, "custom-theme-root")
        assert "Sneaker Collection themed" in html

    def test_unthemed_collection_list_uses_default(self, auth_client, collection_type):
        response = auth_client.get(
            reverse("collections:collection_list", args=[collection_type.slug])
        )
        assert response.status_code == 200
        assert not _has_id(response.content.decode(), "custom-theme-root")
