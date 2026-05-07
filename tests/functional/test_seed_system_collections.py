"""
Functional tests for the seed_system_collections management command (Phase 1).

Tests verify:
  - Dry-run prints expected output without writing to DB
  - First run creates both system CollectionType records
  - Re-run is idempotent (update, not duplicate)
  - Created records have correct field values
  - --owner flag selects the correct user
  - Missing superuser raises CommandError
  - GenericValuationHistory model can be created and is linked to a
    DynamicCollectionItem (confirms the Phase 1 migration is applied)
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    GenericValuationHistory,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def superuser(db):
    return User.objects.create_superuser(
        username="admin", password="admin", email="admin@example.com"
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(username="regular", password="pass")


# ---------------------------------------------------------------------------
# Seed command — dry run
# ---------------------------------------------------------------------------


class TestSeedDryRun:
    def test_dry_run_creates_nothing(self, superuser, capsys):
        call_command("seed_system_collections", "--dry-run", "--owner", "admin")
        assert CollectionType.objects.count() == 0

    def test_dry_run_prints_automobiles(self, superuser, capsys):
        call_command("seed_system_collections", "--dry-run", "--owner", "admin")
        out = capsys.readouterr().out
        assert "automobiles" in out.lower()

    def test_dry_run_prints_horology(self, superuser, capsys):
        call_command("seed_system_collections", "--dry-run", "--owner", "admin")
        out = capsys.readouterr().out
        assert "horology" in out.lower()

    def test_dry_run_prints_create_action(self, superuser, capsys):
        call_command("seed_system_collections", "--dry-run", "--owner", "admin")
        out = capsys.readouterr().out
        assert "CREATE" in out


# ---------------------------------------------------------------------------
# Seed command — first run (creates records)
# ---------------------------------------------------------------------------


class TestSeedCreate:
    def test_creates_two_collection_types(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        assert CollectionType.objects.count() == 2

    def test_automobiles_slug(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        assert CollectionType.objects.filter(slug="automobiles").exists()

    def test_horology_slug(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        assert CollectionType.objects.filter(slug="horology-salon").exists()

    def test_automobiles_is_system(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        ct = CollectionType.objects.get(slug="automobiles")
        assert ct.is_system is True

    def test_horology_is_system(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        ct = CollectionType.objects.get(slug="horology-salon")
        assert ct.is_system is True

    def test_automobiles_service_provider_key(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        ct = CollectionType.objects.get(slug="automobiles")
        assert ct.service_provider_key == "vehicle"

    def test_horology_service_provider_key(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        ct = CollectionType.objects.get(slug="horology-salon")
        assert ct.service_provider_key == "timepiece"

    def test_automobiles_field_schema_has_vin(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        ct = CollectionType.objects.get(slug="automobiles")
        field_names = [f["name"] for f in ct.field_schema["fields"]]
        assert "vin" in field_names

    def test_automobiles_field_schema_has_make_model_year(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        ct = CollectionType.objects.get(slug="automobiles")
        field_names = [f["name"] for f in ct.field_schema["fields"]]
        assert "make" in field_names
        assert "model" in field_names
        assert "year" in field_names

    def test_automobiles_field_schema_system_fields_present(self, superuser):
        """specs and features are system_json fields (not user-editable)."""
        call_command("seed_system_collections", "--owner", "admin")
        ct = CollectionType.objects.get(slug="automobiles")
        system_fields = [f for f in ct.field_schema["fields"] if f.get("system")]
        system_names = {f["name"] for f in system_fields}
        assert "specs" in system_names
        assert "features" in system_names

    def test_horology_field_schema_has_reference_number(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        ct = CollectionType.objects.get(slug="horology-salon")
        field_names = [f["name"] for f in ct.field_schema["fields"]]
        assert "reference_number" in field_names

    def test_horology_field_schema_has_condition_fields(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        ct = CollectionType.objects.get(slug="horology-salon")
        field_names = [f["name"] for f in ct.field_schema["fields"]]
        assert "has_box" in field_names
        assert "has_papers" in field_names
        assert "condition_grade" in field_names

    def test_horology_list_display_includes_brand(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        ct = CollectionType.objects.get(slug="horology-salon")
        assert "brand" in ct.list_display_fields

    def test_automobiles_list_display_includes_year_and_make(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        ct = CollectionType.objects.get(slug="automobiles")
        assert "year" in ct.list_display_fields
        assert "make" in ct.list_display_fields

    def test_owner_is_correct_user(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        for ct in CollectionType.objects.all():
            assert ct.owner == superuser


# ---------------------------------------------------------------------------
# Seed command — idempotency (re-run updates, not duplicates)
# ---------------------------------------------------------------------------


class TestSeedIdempotency:
    def test_second_run_does_not_create_duplicates(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        call_command("seed_system_collections", "--owner", "admin")
        assert CollectionType.objects.count() == 2

    def test_second_run_prints_update_action(self, superuser, capsys):
        call_command("seed_system_collections", "--owner", "admin")
        call_command("seed_system_collections", "--owner", "admin")
        out = capsys.readouterr().out
        assert "UPDATE" in out

    def test_update_preserves_slug(self, superuser):
        call_command("seed_system_collections", "--owner", "admin")
        call_command("seed_system_collections", "--owner", "admin")
        assert CollectionType.objects.filter(slug="automobiles").count() == 1
        assert CollectionType.objects.filter(slug="horology-salon").count() == 1


# ---------------------------------------------------------------------------
# Seed command — --owner flag
# ---------------------------------------------------------------------------


class TestSeedOwnerFlag:
    def test_owner_flag_selects_named_user(self, regular_user):
        call_command("seed_system_collections", "--owner", "regular")
        for ct in CollectionType.objects.all():
            assert ct.owner == regular_user

    def test_invalid_owner_raises_command_error(self, superuser):
        with pytest.raises(CommandError, match="not found"):
            call_command("seed_system_collections", "--owner", "nonexistent_user_xyz")

    def test_no_superuser_raises_command_error(self, db):
        """With no --owner and no superuser in DB, command must raise."""
        with pytest.raises(CommandError, match="No superuser"):
            call_command("seed_system_collections")


# ---------------------------------------------------------------------------
# GenericValuationHistory model (Phase 1 migration contract)
# ---------------------------------------------------------------------------


class TestGenericValuationHistory:
    def test_can_create_valuation_history_for_collection_item(self, superuser):
        """Confirm the new model and FK are wired up correctly."""
        ct = CollectionType.objects.create(
            owner=superuser,
            name="Test Autos",
            slug="test-autos-vh",
            service_provider_key="vehicle",
            is_system=False,
        )
        item = DynamicCollectionItem.objects.create(
            owner=superuser,
            collection_type=ct,
            name="2021 Toyota Tacoma",
            current_market_value=Decimal("40000.00"),
            custom_fields={"make": "Toyota", "model": "Tacoma", "year": 2021},
        )
        record = GenericValuationHistory.objects.create(
            item=item,
            value=Decimal("41500.00"),
            raw_data={"source": "test"},
        )

        assert record.pk is not None
        assert record.item == item
        assert record.value == Decimal("41500.00")
        assert record.raw_data == {"source": "test"}

    def test_valuation_history_reverse_relation(self, superuser):
        """item.valuation_history.all() should work."""
        ct = CollectionType.objects.create(
            owner=superuser,
            name="Test Autos 2",
            slug="test-autos-vh2",
            service_provider_key="vehicle",
            is_system=False,
        )
        item = DynamicCollectionItem.objects.create(
            owner=superuser,
            collection_type=ct,
            name="2022 Porsche 911",
            custom_fields={},
        )
        GenericValuationHistory.objects.create(item=item, value=Decimal("100000"))
        GenericValuationHistory.objects.create(item=item, value=Decimal("102000"))

        assert item.valuation_history.count() == 2

    def test_valuation_history_ordered_by_date_desc(self, superuser):
        """Most recent valuation should be first."""
        ct = CollectionType.objects.create(
            owner=superuser,
            name="Test Autos 3",
            slug="test-autos-vh3",
            service_provider_key="vehicle",
            is_system=False,
        )
        item = DynamicCollectionItem.objects.create(
            owner=superuser,
            collection_type=ct,
            name="2020 Ford GT",
            custom_fields={},
        )
        GenericValuationHistory.objects.create(item=item, value=Decimal("200000"))
        h2 = GenericValuationHistory.objects.create(item=item, value=Decimal("210000"))

        history = list(item.valuation_history.all())
        # Latest insert (h2) should come first due to ordering = ['-date']
        assert history[0].pk == h2.pk

    def test_cascade_delete_with_item(self, superuser):
        """Deleting item must cascade to GenericValuationHistory."""
        ct = CollectionType.objects.create(
            owner=superuser,
            name="Test Cascade",
            slug="test-cascade-vh",
            service_provider_key="default",
            is_system=False,
        )
        item = DynamicCollectionItem.objects.create(
            owner=superuser,
            collection_type=ct,
            name="Doomed Item",
            custom_fields={},
        )
        GenericValuationHistory.objects.create(item=item, value=Decimal("999"))

        item_pk = item.pk
        item.delete()

        assert GenericValuationHistory.objects.filter(item_id=item_pk).count() == 0
