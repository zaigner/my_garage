"""
Unit tests for value coercion in seed_system_collections.

Coercion repairs item data after a field's type changes from text to
select/boolean/json_list. It must be idempotent and must never guess
destructively — an unmappable value is left alone and reported.
"""

from __future__ import annotations

import pytest

from my_garage.management.commands.seed_system_collections import (
    coerce_item_fields,
    coerce_value,
    find_unmappable,
)

CONDITION_FIELD = {
    "name": "condition_grade",
    "type": "select",
    "choices": [
        {"value": "MINT", "label": "Mint — no visible wear"},
        {"value": "GOOD", "label": "Good — visible wear, fully functional"},
        {"value": "POOR", "label": "Poor — significant damage or non-running"},
    ],
}
BOX_FIELD = {"name": "has_box", "type": "boolean"}
COMPLICATIONS_FIELD = {"name": "complications", "type": "json_list"}
BRAND_FIELD = {"name": "brand", "type": "text"}


class TestSelectCoercion:
    @pytest.mark.parametrize("raw", ["GOOD", "Good", "good", "  Good  "])
    def test_case_insensitive_value_match(self, raw):
        assert coerce_value(raw, CONDITION_FIELD) == "GOOD"

    def test_matches_full_label(self):
        assert coerce_value("Mint — no visible wear", CONDITION_FIELD) == "MINT"

    def test_matches_label_prefix_before_em_dash(self):
        assert coerce_value("Poor", CONDITION_FIELD) == "POOR"

    def test_unmappable_value_is_left_untouched(self):
        assert coerce_value("Refurbished", CONDITION_FIELD) == "Refurbished"

    def test_non_string_left_untouched(self):
        assert coerce_value(7, CONDITION_FIELD) == 7

    def test_idempotent(self):
        once = coerce_value("Good", CONDITION_FIELD)
        assert coerce_value(once, CONDITION_FIELD) == once


class TestBooleanCoercion:
    @pytest.mark.parametrize("raw", ["true", "True", "yes", "Y", "1", "on"])
    def test_truthy_strings(self, raw):
        assert coerce_value(raw, BOX_FIELD) is True

    @pytest.mark.parametrize("raw", ["false", "No", "n", "0", "off", ""])
    def test_falsy_strings(self, raw):
        assert coerce_value(raw, BOX_FIELD) is False

    def test_existing_bool_passes_through(self):
        assert coerce_value(True, BOX_FIELD) is True

    def test_unrecognised_string_left_untouched(self):
        assert coerce_value("maybe", BOX_FIELD) == "maybe"


class TestJsonListCoercion:
    def test_splits_comma_separated_string(self):
        assert coerce_value("Chronograph, GMT , Moonphase", COMPLICATIONS_FIELD) == [
            "Chronograph",
            "GMT",
            "Moonphase",
        ]

    def test_existing_list_passes_through(self):
        assert coerce_value(["GMT"], COMPLICATIONS_FIELD) == ["GMT"]

    def test_empty_string_becomes_empty_list(self):
        assert coerce_value("", COMPLICATIONS_FIELD) == []

    def test_drops_blank_segments(self):
        assert coerce_value("GMT,,  ,Alarm", COMPLICATIONS_FIELD) == ["GMT", "Alarm"]


class TestCoerceItemFields:
    SCHEMA = {"fields": [CONDITION_FIELD, BOX_FIELD, COMPLICATIONS_FIELD, BRAND_FIELD]}

    def test_coerces_and_reports_changes(self):
        updated, changes = coerce_item_fields(
            {
                "condition_grade": "Good",
                "has_box": "yes",
                "complications": "GMT",
                "brand": "Rolex",
            },
            self.SCHEMA,
        )
        assert updated["condition_grade"] == "GOOD"
        assert updated["has_box"] is True
        assert updated["complications"] == ["GMT"]
        assert updated["brand"] == "Rolex"  # text untouched
        assert len(changes) == 3

    def test_no_changes_when_already_correct(self):
        clean = {
            "condition_grade": "GOOD",
            "has_box": True,
            "complications": ["GMT"],
            "brand": "Rolex",
        }
        updated, changes = coerce_item_fields(clean, self.SCHEMA)
        assert updated == clean
        assert changes == []

    def test_absent_fields_are_not_invented(self):
        updated, _ = coerce_item_fields({"brand": "Rolex"}, self.SCHEMA)
        assert set(updated) == {"brand"}

    def test_handles_empty_custom_fields(self):
        assert coerce_item_fields({}, self.SCHEMA) == ({}, [])

    def test_idempotent_across_two_passes(self):
        first, _ = coerce_item_fields(
            {"condition_grade": "Good", "has_box": "yes"}, self.SCHEMA
        )
        second, changes = coerce_item_fields(first, self.SCHEMA)
        assert second == first
        assert changes == []


class TestFindUnmappable:
    SCHEMA = {"fields": [CONDITION_FIELD, BOX_FIELD]}

    def test_reports_value_outside_choices(self):
        problems = find_unmappable({"condition_grade": "Refurbished"}, self.SCHEMA)
        assert len(problems) == 1
        assert "condition_grade" in problems[0]

    def test_silent_when_value_is_valid(self):
        assert find_unmappable({"condition_grade": "GOOD"}, self.SCHEMA) == []

    def test_ignores_missing_and_blank(self):
        assert find_unmappable({}, self.SCHEMA) == []
        assert find_unmappable({"condition_grade": ""}, self.SCHEMA) == []
