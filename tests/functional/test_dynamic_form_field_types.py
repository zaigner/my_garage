"""
Functional tests for schema-driven field rendering in DynamicCollectionItemForm.

select / boolean / json_list were declared in the blueprints long before the
renderer could build them, and the renderer's final ``else: continue`` dropped
them silently — no error, just missing inputs. These tests pin the behaviour so
a blueprint field can never disappear from the form again.
"""

from __future__ import annotations

import pytest
from django import forms
from django.contrib.auth import get_user_model

from my_garage.collection_blueprints import COLLECTION_BLUEPRINTS, get_blueprint
from my_garage.forms import DynamicCollectionItemForm
from my_garage.models import CollectionType, DynamicCollectionItem

User = get_user_model()


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="owner", password="pass")


def make_type(owner, fields, slug="test-collection"):
    return CollectionType.objects.create(
        owner=owner,
        name="Test Collection",
        slug=slug,
        field_schema={"fields": fields},
    )


SELECT_FIELD = {
    "name": "condition",
    "type": "select",
    "label": "Condition",
    "required": False,
    "choices": [
        {"value": "MINT", "label": "Mint"},
        {"value": "GOOD", "label": "Good"},
    ],
}
BOOLEAN_FIELD = {"name": "has_box", "type": "boolean", "label": "Original Box"}
JSON_LIST_FIELD = {
    "name": "complications",
    "type": "json_list",
    "label": "Complications",
    "suggestions": ["Chronograph", "GMT", "Moonphase"],
}


class TestSelectField:
    def test_renders_as_choice_field(self, owner):
        form = DynamicCollectionItemForm(
            collection_type=make_type(owner, [SELECT_FIELD])
        )
        field = form.fields["custom_condition"]
        assert isinstance(field, forms.ChoiceField)

    def test_optional_select_gets_blank_choice(self, owner):
        form = DynamicCollectionItemForm(
            collection_type=make_type(owner, [SELECT_FIELD])
        )
        values = [value for value, _ in form.fields["custom_condition"].choices]
        assert values == ["", "MINT", "GOOD"]

    def test_required_select_has_no_blank_choice(self, owner):
        required = {**SELECT_FIELD, "required": True}
        form = DynamicCollectionItemForm(collection_type=make_type(owner, [required]))
        values = [value for value, _ in form.fields["custom_condition"].choices]
        assert values == ["MINT", "GOOD"]

    def test_saves_choice_value(self, owner):
        ctype = make_type(owner, [SELECT_FIELD])
        form = DynamicCollectionItemForm(
            {"name": "Item", "custom_condition": "MINT"}, collection_type=ctype
        )
        assert form.is_valid(), form.errors
        item = form.save(commit=False)
        item.owner = owner
        item.collection_type = ctype
        item.save()
        assert item.custom_fields["condition"] == "MINT"

    def test_rejects_value_outside_choices(self, owner):
        form = DynamicCollectionItemForm(
            {"name": "Item", "custom_condition": "SHINY"},
            collection_type=make_type(owner, [SELECT_FIELD]),
        )
        assert not form.is_valid()
        assert "custom_condition" in form.errors


class TestBooleanField:
    def test_renders_as_checkbox(self, owner):
        form = DynamicCollectionItemForm(
            collection_type=make_type(owner, [BOOLEAN_FIELD])
        )
        field = form.fields["custom_has_box"]
        assert isinstance(field, forms.BooleanField)
        assert isinstance(field.widget, forms.CheckboxInput)

    def test_never_required(self, owner):
        """A required checkbox would block submission until ticked."""
        required = {**BOOLEAN_FIELD, "required": True}
        form = DynamicCollectionItemForm(collection_type=make_type(owner, [required]))
        assert form.fields["custom_has_box"].required is False

    @pytest.mark.parametrize(
        "posted,expected", [({"custom_has_box": "on"}, True), ({}, False)]
    )
    def test_saves_bool(self, owner, posted, expected):
        ctype = make_type(owner, [BOOLEAN_FIELD])
        form = DynamicCollectionItemForm(
            {"name": "Item", **posted}, collection_type=ctype
        )
        assert form.is_valid(), form.errors
        item = form.save(commit=False)
        item.owner = owner
        item.collection_type = ctype
        item.save()
        assert item.custom_fields["has_box"] is expected


class TestJsonListField:
    def test_renders_as_text_input(self, owner):
        form = DynamicCollectionItemForm(
            collection_type=make_type(owner, [JSON_LIST_FIELD])
        )
        assert isinstance(form.fields["custom_complications"], forms.CharField)

    def test_suggestions_reach_the_widget(self, owner):
        form = DynamicCollectionItemForm(
            collection_type=make_type(owner, [JSON_LIST_FIELD])
        )
        attrs = form.fields["custom_complications"].widget.attrs
        assert "Chronograph" in attrs["data-suggestions"]
        assert attrs["placeholder"]

    def test_splits_input_into_json_array(self, owner):
        ctype = make_type(owner, [JSON_LIST_FIELD])
        form = DynamicCollectionItemForm(
            {"name": "Item", "custom_complications": "Chronograph, GMT , Moonphase"},
            collection_type=ctype,
        )
        assert form.is_valid(), form.errors
        item = form.save(commit=False)
        item.owner = owner
        item.collection_type = ctype
        item.save()
        assert item.custom_fields["complications"] == [
            "Chronograph",
            "GMT",
            "Moonphase",
        ]

    def test_blank_input_becomes_empty_list(self, owner):
        ctype = make_type(owner, [JSON_LIST_FIELD])
        form = DynamicCollectionItemForm(
            {"name": "Item", "custom_complications": ""}, collection_type=ctype
        )
        assert form.is_valid(), form.errors
        item = form.save(commit=False)
        item.owner = owner
        item.collection_type = ctype
        item.save()
        assert item.custom_fields["complications"] == []

    def test_existing_list_is_rendered_as_comma_string(self, owner):
        """Regression: the dict/list guard used to skip json_list fields entirely."""
        ctype = make_type(owner, [JSON_LIST_FIELD])
        item = DynamicCollectionItem.objects.create(
            owner=owner,
            collection_type=ctype,
            name="Item",
            custom_fields={"complications": ["Chronograph", "GMT"]},
        )
        form = DynamicCollectionItemForm(instance=item, collection_type=ctype)
        assert "custom_complications" in form.fields
        assert form.fields["custom_complications"].initial == "Chronograph, GMT"

    def test_round_trips_without_loss(self, owner):
        ctype = make_type(owner, [JSON_LIST_FIELD])
        item = DynamicCollectionItem.objects.create(
            owner=owner,
            collection_type=ctype,
            name="Item",
            custom_fields={"complications": ["Chronograph", "GMT"]},
        )
        form = DynamicCollectionItemForm(
            {"name": "Item", "custom_complications": "Chronograph, GMT"},
            instance=item,
            collection_type=ctype,
        )
        assert form.is_valid(), form.errors
        saved = form.save()
        assert saved.custom_fields["complications"] == ["Chronograph", "GMT"]


class TestSystemFieldsStaySkipped:
    def test_system_json_is_not_rendered(self, owner):
        field = {"name": "specs", "type": "system_json", "system": True}
        form = DynamicCollectionItemForm(collection_type=make_type(owner, [field]))
        assert "custom_specs" not in form.fields

    def test_dict_values_still_skipped_for_non_json_list(self, owner):
        ctype = make_type(owner, [{"name": "specs", "type": "text"}])
        item = DynamicCollectionItem.objects.create(
            owner=owner,
            collection_type=ctype,
            name="Item",
            custom_fields={"specs": {"engine": "V8"}},
        )
        form = DynamicCollectionItemForm(instance=item, collection_type=ctype)
        assert "custom_specs" not in form.fields

    def test_system_data_survives_a_form_save(self, owner):
        ctype = make_type(
            owner,
            [
                {"name": "make", "type": "text"},
                {"name": "specs", "type": "system_json", "system": True},
            ],
        )
        item = DynamicCollectionItem.objects.create(
            owner=owner,
            collection_type=ctype,
            name="Item",
            custom_fields={"make": "Toyota", "specs": {"engine": "V6"}},
        )
        form = DynamicCollectionItemForm(
            {"name": "Item", "custom_make": "Honda"},
            instance=item,
            collection_type=ctype,
        )
        assert form.is_valid(), form.errors
        saved = form.save()
        assert saved.custom_fields["specs"] == {"engine": "V6"}
        assert saved.custom_fields["make"] == "Honda"


class TestEveryBlueprintRenders:
    """No blueprint field may be silently dropped by the renderer."""

    @pytest.mark.parametrize("slug", [bp["slug"] for bp in COLLECTION_BLUEPRINTS])
    def test_all_non_system_fields_render(self, owner, slug):
        blueprint = get_blueprint(slug)
        ctype = CollectionType.objects.create(
            owner=owner,
            name=blueprint["name"],
            slug=blueprint["slug"],
            field_schema=blueprint["field_schema"],
        )
        form = DynamicCollectionItemForm(collection_type=ctype)

        expected = {
            f"custom_{f['name']}"
            for f in blueprint["field_schema"]["fields"]
            if not (f.get("system") or f["type"] == "system_json")
        }
        rendered = {name for name in form.fields if name.startswith("custom_")}
        assert expected == rendered, f"{slug} dropped {expected - rendered}"
