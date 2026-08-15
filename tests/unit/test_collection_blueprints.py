"""
Unit tests for the collection blueprint catalogue.

These guard the catalogue's internal consistency and, critically, that every
field type it declares is one the dynamic form renderer can actually build.
A blueprint declaring an unsupported type would silently drop that field from
the item form — the exact failure that flattened the original schemas to text.
"""

from __future__ import annotations

import pytest

from my_garage.collection_blueprints import (
    COLLECTION_BLUEPRINTS,
    SYSTEM_BLUEPRINTS,
    get_blueprint,
    list_blueprints,
    load_ui_theme,
)

# Types DynamicCollectionItemForm builds a widget for.
RENDERABLE_TYPES = {
    "text",
    "number",
    "date",
    "file",
    "select",
    "boolean",
    "json_list",
    "relationship",
}
# Types deliberately skipped by the form (written by service providers).
SKIPPED_TYPES = {"system_json"}

REQUIRED_KEYS = {
    "slug",
    "name",
    "icon",
    "description",
    "service_provider_key",
    "field_schema",
    "list_display_fields",
}


class TestCatalogueShape:
    def test_catalogue_is_not_empty(self):
        assert len(COLLECTION_BLUEPRINTS) == 7

    def test_slugs_are_unique(self):
        slugs = [bp["slug"] for bp in COLLECTION_BLUEPRINTS]
        assert len(slugs) == len(set(slugs))

    @pytest.mark.parametrize(
        "blueprint", COLLECTION_BLUEPRINTS, ids=lambda bp: bp["slug"]
    )
    def test_required_keys_present(self, blueprint):
        assert REQUIRED_KEYS <= set(blueprint)

    @pytest.mark.parametrize(
        "blueprint", COLLECTION_BLUEPRINTS, ids=lambda bp: bp["slug"]
    )
    def test_icons_carry_fa6_style_prefix(self, blueprint):
        # FontAwesome 6 renders nothing for a bare "fa-car".
        assert blueprint["icon"].startswith("fa-solid "), blueprint["icon"]

    @pytest.mark.parametrize(
        "blueprint", COLLECTION_BLUEPRINTS, ids=lambda bp: bp["slug"]
    )
    def test_field_types_are_supported(self, blueprint):
        for field in blueprint["field_schema"]["fields"]:
            assert field["type"] in RENDERABLE_TYPES | SKIPPED_TYPES, (
                f"{blueprint['slug']}.{field['name']} uses unsupported "
                f"type {field['type']!r}"
            )

    @pytest.mark.parametrize(
        "blueprint", COLLECTION_BLUEPRINTS, ids=lambda bp: bp["slug"]
    )
    def test_field_names_are_unique(self, blueprint):
        names = [f["name"] for f in blueprint["field_schema"]["fields"]]
        assert len(names) == len(set(names))

    @pytest.mark.parametrize(
        "blueprint", COLLECTION_BLUEPRINTS, ids=lambda bp: bp["slug"]
    )
    def test_select_fields_declare_choices(self, blueprint):
        for field in blueprint["field_schema"]["fields"]:
            if field["type"] == "select":
                choices = field.get("choices")
                assert choices, f"{field['name']} is a select with no choices"
                assert all(c.get("value") for c in choices)

    @pytest.mark.parametrize(
        "blueprint", COLLECTION_BLUEPRINTS, ids=lambda bp: bp["slug"]
    )
    def test_list_display_fields_exist_in_schema(self, blueprint):
        names = {f["name"] for f in blueprint["field_schema"]["fields"]}
        assert set(blueprint["list_display_fields"]) <= names

    @pytest.mark.parametrize(
        "blueprint", COLLECTION_BLUEPRINTS, ids=lambda bp: bp["slug"]
    )
    def test_list_display_excludes_system_fields(self, blueprint):
        system_names = {
            f["name"]
            for f in blueprint["field_schema"]["fields"]
            if f.get("system") or f["type"] == "system_json"
        }
        assert not (set(blueprint["list_display_fields"]) & system_names)


class TestSystemBlueprints:
    def test_two_system_blueprints(self):
        assert {bp["slug"] for bp in SYSTEM_BLUEPRINTS} == {
            "automobiles",
            "horology-salon",
        }

    def test_system_blueprints_have_real_providers(self):
        providers = {bp["slug"]: bp["service_provider_key"] for bp in SYSTEM_BLUEPRINTS}
        assert providers == {"automobiles": "vehicle", "horology-salon": "timepiece"}

    def test_generic_blueprints_use_default_provider(self):
        for bp in COLLECTION_BLUEPRINTS:
            if not bp.get("is_system"):
                assert bp["service_provider_key"] == "default"


class TestAccessors:
    def test_get_blueprint_returns_match(self):
        assert get_blueprint("wine-collection")["name"] == "Wine Collection"

    def test_get_blueprint_returns_none_for_unknown(self):
        assert get_blueprint("does-not-exist") is None

    def test_returned_blueprints_are_copies(self):
        first = get_blueprint("wine-collection")
        first["name"] = "Mutated"
        assert get_blueprint("wine-collection")["name"] == "Wine Collection"

    def test_list_blueprints_are_copies(self):
        listing = list_blueprints()
        listing[0]["field_schema"]["fields"].clear()
        assert list_blueprints()[0]["field_schema"]["fields"]

    def test_load_ui_theme_returns_empty_when_absent(self):
        assert load_ui_theme(get_blueprint("wine-collection")) == ""

    def test_load_ui_theme_reads_theme_file(self):
        theme = load_ui_theme(get_blueprint("coin-collection"))
        assert len(theme) > 1000
