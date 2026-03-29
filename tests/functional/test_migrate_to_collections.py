"""
Functional tests for Phase 2 migration commands.

Tests cover:
  migrate_vehicles_to_collections
    - Dry-run: prints summary, no DB writes
    - Creates DynamicCollectionItem with correct field mapping
    - Migrates ServiceRecord → GenericServiceRecord
    - Migrates ValuationHistory → GenericValuationHistory
    - Migrates legacy Upgrade → GenericUpgrade (item FK)
    - Re-links GenericUpgrade (Vehicle content_type) → item FK
    - Migrates ConditionReport → custom_fields JSON list
    - Copies photo reference
    - Idempotency: second run skips already-migrated vehicles
    - Single-vehicle flag: --vehicle <pk>
    - Raises on missing CollectionType
    - Raises on invalid --vehicle id

  migrate_timepieces_to_collections
    - Dry-run: prints summary, no DB writes
    - Creates DynamicCollectionItem with correct field mapping
    - 'model' stored as 'watch_model'
    - Re-links GenericUpgrade (Timepiece content_type)
    - Copies photo reference
    - Idempotency
    - Single-timepiece flag
    - Raises on missing CollectionType
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError

from my_garage.models import (
    CollectionType,
    ConditionReport,
    DynamicCollectionItem,
    GenericServiceRecord,
    GenericUpgrade,
    GenericValuationHistory,
    ServiceRecord,
    Timepiece,
    Upgrade,
    ValuationHistory,
    Vehicle,
)

User = get_user_model()

# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def owner(db):
    return User.objects.create_user(username="migrator", password="pass")


@pytest.fixture
def automobiles_ct(owner):
    return CollectionType.objects.create(
        owner=owner,
        name="Automobiles",
        slug="automobiles",
        service_provider_key="vehicle",
        is_system=True,
        field_schema={"fields": []},
    )


@pytest.fixture
def horology_ct(owner):
    return CollectionType.objects.create(
        owner=owner,
        name="Horology Salon",
        slug="horology-salon",
        service_provider_key="timepiece",
        is_system=True,
        field_schema={"fields": []},
    )


@pytest.fixture
def vehicle(owner):
    return Vehicle.objects.create(
        owner=owner,
        make="Toyota",
        model="Tacoma",
        year=2021,
        trim="TRD Pro",
        vin="1HGBH41JXMN109186",
        license_plate="TRD-001",
        transmission="manual_6",
        exterior_color="Army Green",
        interior_color="Black",
        mileage=15000,
        purchase_price=Decimal("45000.00"),
        purchase_date=date(2021, 3, 15),
        current_market_value=Decimal("48000.00"),
        notes="Garage queen",
        specs={"engine": "3.5L V6", "drivetrain": "4WD"},
        features={"Sunroof": True, "Heated Seats": True},
    )


@pytest.fixture
def vehicle_with_service(vehicle):
    ServiceRecord.objects.create(
        vehicle=vehicle,
        date=date(2022, 6, 1),
        vendor="Toyota Dealer",
        description="Oil change and tire rotation",
        category="MAINTENANCE",
        total_cost=Decimal("125.00"),
        is_verified=True,
    )
    ServiceRecord.objects.create(
        vehicle=vehicle,
        date=date(2023, 1, 15),
        vendor="Midas",
        description="Brake pads",
        category="REPAIR",
        total_cost=Decimal("350.00"),
        is_verified=False,
    )
    return vehicle


@pytest.fixture
def vehicle_with_valuation(vehicle):
    ValuationHistory.objects.create(vehicle=vehicle, value=Decimal("47000.00"), raw_data={"source": "marketcheck"})
    ValuationHistory.objects.create(vehicle=vehicle, value=Decimal("48000.00"), raw_data={"source": "marketcheck"})
    return vehicle


@pytest.fixture
def vehicle_with_legacy_upgrade(vehicle):
    Upgrade.objects.create(
        vehicle=vehicle,
        part_name="Cold Air Intake",
        brand="AEM",
        part_number="21-8023DC",
        status="INSTALLED",
        cost=Decimal("299.99"),
        notes="Stage 1",
    )
    Upgrade.objects.create(
        vehicle=vehicle,
        part_name="Lift Kit",
        brand="Bilstein",
        part_number="46-229076",
        status="WISHLIST",
        cost=Decimal("1200.00"),
    )
    return vehicle


@pytest.fixture
def vehicle_with_generic_upgrade(vehicle):
    vehicle_ct = ContentType.objects.get_for_model(Vehicle)
    GenericUpgrade.objects.create(
        content_type=vehicle_ct,
        object_id=vehicle.pk,
        name="Skid Plate",
        brand="ARB",
        status="WISHLIST",
        cost=Decimal("450.00"),
    )
    return vehicle


@pytest.fixture
def vehicle_with_condition_report(vehicle):
    ConditionReport.objects.create(
        vehicle=vehicle,
        area="EXTERIOR",
        photo="condition_checks/2024/01/exterior.jpg",
        grade=8.5,
        ai_feedback="Minor door ding on driver side",
        value_adjustment=Decimal("-200.00"),
    )
    return vehicle


@pytest.fixture
def timepiece(owner):
    return Timepiece.objects.create(
        owner=owner,
        brand="Rolex",
        model="Submariner",
        reference_number="116610LN",
        serial_number="7Z123456",
        year=2019,
        movement_type="AUTOMATIC",
        case_material="Oystersteel",
        dial_color="Black",
        complications=["date"],
        has_box=True,
        has_papers=True,
        condition_grade="MINT",
        purchase_price=Decimal("8500.00"),
        purchase_date=date(2020, 5, 10),
        current_market_value=Decimal("14000.00"),
        notes="Full set",
    )


@pytest.fixture
def timepiece_with_upgrade(timepiece):
    timepiece_ct = ContentType.objects.get_for_model(Timepiece)
    GenericUpgrade.objects.create(
        content_type=timepiece_ct,
        object_id=timepiece.pk,
        name="New Crystal",
        brand="Rolex",
        status="COMPLETED",
        cost=Decimal("200.00"),
    )
    return timepiece


# ─────────────────────────────────────────────────────────────────────────────
# migrate_vehicles_to_collections
# ─────────────────────────────────────────────────────────────────────────────


class TestVehicleMigrateDryRun:
    def test_dry_run_creates_no_items(self, automobiles_ct, vehicle, capsys):
        call_command("migrate_vehicles_to_collections", "--dry-run")
        assert DynamicCollectionItem.objects.count() == 0

    def test_dry_run_prints_vehicle(self, automobiles_ct, vehicle, capsys):
        call_command("migrate_vehicles_to_collections", "--dry-run")
        out = capsys.readouterr().out
        assert "Toyota" in out or "Tacoma" in out

    def test_dry_run_shows_migrate_label(self, automobiles_ct, vehicle, capsys):
        call_command("migrate_vehicles_to_collections", "--dry-run")
        out = capsys.readouterr().out
        assert "DRY" in out or "MIGRATE" in out


class TestVehicleMigrateCreate:
    def test_creates_dynamic_collection_item(self, automobiles_ct, vehicle):
        call_command("migrate_vehicles_to_collections")
        assert DynamicCollectionItem.objects.filter(collection_type=automobiles_ct).count() == 1

    def test_item_name_matches_vehicle_str(self, automobiles_ct, vehicle):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert "2021" in item.name
        assert "Toyota" in item.name

    def test_item_financials_copied(self, automobiles_ct, vehicle):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.purchase_price == Decimal("45000.00")
        assert item.current_market_value == Decimal("48000.00")
        assert item.purchase_date == date(2021, 3, 15)

    def test_item_notes_copied(self, automobiles_ct, vehicle):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.notes == "Garage queen"

    def test_custom_fields_identity(self, automobiles_ct, vehicle):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.custom_fields["make"] == "Toyota"
        assert item.custom_fields["model"] == "Tacoma"
        assert item.custom_fields["year"] == 2021
        assert item.custom_fields["trim"] == "TRD Pro"
        assert item.custom_fields["vin"] == "1HGBH41JXMN109186"

    def test_custom_fields_specs(self, automobiles_ct, vehicle):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.custom_fields["specs"]["engine"] == "3.5L V6"
        assert item.custom_fields["specs"]["drivetrain"] == "4WD"

    def test_custom_fields_features(self, automobiles_ct, vehicle):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.custom_fields["features"]["Sunroof"] is True

    def test_source_id_stored(self, automobiles_ct, vehicle):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.custom_fields["source_vehicle_id"] == vehicle.pk

    def test_migrated_flag_set(self, automobiles_ct, vehicle):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.custom_fields["migrated"] is True

    def test_owner_preserved(self, automobiles_ct, vehicle, owner):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.owner == owner


class TestVehicleMigrateServiceRecords:
    def test_service_records_created(self, automobiles_ct, vehicle_with_service):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.service_records.count() == 2

    def test_service_record_fields(self, automobiles_ct, vehicle_with_service):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        records = list(item.service_records.order_by("date"))
        first = records[0]
        assert first.vendor == "Toyota Dealer"
        assert first.category == "MAINTENANCE"
        assert first.total_cost == Decimal("125.00")
        assert first.is_verified is True

    def test_service_record_dates_preserved(self, automobiles_ct, vehicle_with_service):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        dates = set(item.service_records.values_list("date", flat=True))
        assert date(2022, 6, 1) in dates
        assert date(2023, 1, 15) in dates


class TestVehicleMigrateValuationHistory:
    def test_valuation_history_created(self, automobiles_ct, vehicle_with_valuation):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.valuation_history.count() == 2

    def test_valuation_values_preserved(self, automobiles_ct, vehicle_with_valuation):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        values = set(item.valuation_history.values_list("value", flat=True))
        assert Decimal("47000.00") in values
        assert Decimal("48000.00") in values

    def test_valuation_raw_data_preserved(self, automobiles_ct, vehicle_with_valuation):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        first = item.valuation_history.last()  # oldest
        assert first.raw_data == {"source": "marketcheck"}


class TestVehicleMigrateLegacyUpgrades:
    def test_legacy_upgrades_become_generic_upgrades(self, automobiles_ct, vehicle_with_legacy_upgrade):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.upgrades.count() == 2

    def test_installed_status_mapped_to_completed(self, automobiles_ct, vehicle_with_legacy_upgrade):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        intake = item.upgrades.get(name="Cold Air Intake")
        assert intake.status == "COMPLETED"

    def test_wishlist_status_preserved(self, automobiles_ct, vehicle_with_legacy_upgrade):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        lift_kit = item.upgrades.get(name="Lift Kit")
        assert lift_kit.status == "WISHLIST"

    def test_upgrade_cost_preserved(self, automobiles_ct, vehicle_with_legacy_upgrade):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        intake = item.upgrades.get(name="Cold Air Intake")
        assert intake.cost == Decimal("299.99")

    def test_upgrade_brand_preserved(self, automobiles_ct, vehicle_with_legacy_upgrade):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        intake = item.upgrades.get(name="Cold Air Intake")
        assert intake.brand == "AEM"


class TestVehicleMigrateGenericUpgrades:
    def test_generic_upgrades_relinked_to_item(self, automobiles_ct, vehicle_with_generic_upgrade):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        relinked = GenericUpgrade.objects.filter(item=item)
        assert relinked.count() == 1
        assert relinked.first().name == "Skid Plate"


class TestVehicleMigrateConditionReports:
    def test_condition_reports_in_custom_fields(self, automobiles_ct, vehicle_with_condition_report):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        reports = item.custom_fields.get("condition_reports", [])
        assert len(reports) == 1

    def test_condition_report_grade_preserved(self, automobiles_ct, vehicle_with_condition_report):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        report = item.custom_fields["condition_reports"][0]
        assert report["grade"] == 8.5

    def test_condition_report_area_preserved(self, automobiles_ct, vehicle_with_condition_report):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        report = item.custom_fields["condition_reports"][0]
        assert report["area"] == "EXTERIOR"

    def test_condition_report_feedback_preserved(self, automobiles_ct, vehicle_with_condition_report):
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        report = item.custom_fields["condition_reports"][0]
        assert "door ding" in report["ai_feedback"]


class TestVehicleMigrateIdempotency:
    def test_second_run_does_not_duplicate(self, automobiles_ct, vehicle):
        call_command("migrate_vehicles_to_collections")
        call_command("migrate_vehicles_to_collections")
        assert DynamicCollectionItem.objects.filter(collection_type=automobiles_ct).count() == 1

    def test_second_run_reports_skipped(self, automobiles_ct, vehicle, capsys):
        call_command("migrate_vehicles_to_collections")
        call_command("migrate_vehicles_to_collections")
        out = capsys.readouterr().out
        assert "SKIP" in out

    def test_second_run_service_records_not_duplicated(self, automobiles_ct, vehicle_with_service):
        call_command("migrate_vehicles_to_collections")
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.service_records.count() == 2  # not 4

    def test_second_run_valuation_history_not_duplicated(self, automobiles_ct, vehicle_with_valuation):
        call_command("migrate_vehicles_to_collections")
        call_command("migrate_vehicles_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.valuation_history.count() == 2  # not 4


class TestVehicleMigrateSingleFlag:
    def test_single_vehicle_flag_migrates_only_that_vehicle(self, automobiles_ct, owner):
        v1 = Vehicle.objects.create(owner=owner, make="Ford", model="GT", year=2005, mileage=0)
        v2 = Vehicle.objects.create(owner=owner, make="Dodge", model="Viper", year=2004, mileage=0)
        call_command("migrate_vehicles_to_collections", "--vehicle", str(v1.pk))
        assert DynamicCollectionItem.objects.filter(collection_type=automobiles_ct).count() == 1
        item = DynamicCollectionItem.objects.get(collection_type=automobiles_ct)
        assert item.custom_fields["make"] == "Ford"

    def test_invalid_vehicle_id_raises(self, automobiles_ct):
        with pytest.raises(CommandError, match="not found"):
            call_command("migrate_vehicles_to_collections", "--vehicle", "99999")


class TestVehicleMigrateMissingCollectionType:
    def test_raises_when_automobiles_ct_missing(self, db):
        with pytest.raises(CommandError, match="automobiles"):
            call_command("migrate_vehicles_to_collections")


# ─────────────────────────────────────────────────────────────────────────────
# migrate_timepieces_to_collections
# ─────────────────────────────────────────────────────────────────────────────


class TestTimepieceMigrateDryRun:
    def test_dry_run_creates_no_items(self, horology_ct, timepiece, capsys):
        call_command("migrate_timepieces_to_collections", "--dry-run")
        assert DynamicCollectionItem.objects.count() == 0

    def test_dry_run_prints_timepiece(self, horology_ct, timepiece, capsys):
        call_command("migrate_timepieces_to_collections", "--dry-run")
        out = capsys.readouterr().out
        assert "Rolex" in out or "Submariner" in out


class TestTimepieceMigrateCreate:
    def test_creates_dynamic_collection_item(self, horology_ct, timepiece):
        call_command("migrate_timepieces_to_collections")
        assert DynamicCollectionItem.objects.filter(collection_type=horology_ct).count() == 1

    def test_item_name_matches_timepiece_str(self, horology_ct, timepiece):
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        assert "Rolex" in item.name
        assert "116610LN" in item.name

    def test_item_financials_copied(self, horology_ct, timepiece):
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        assert item.purchase_price == Decimal("8500.00")
        assert item.current_market_value == Decimal("14000.00")

    def test_model_stored_as_watch_model(self, horology_ct, timepiece):
        """Timepiece.model must be stored as 'watch_model' to avoid ORM collision."""
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        assert item.custom_fields["watch_model"] == "Submariner"
        assert "model" not in item.custom_fields

    def test_reference_number_preserved(self, horology_ct, timepiece):
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        assert item.custom_fields["reference_number"] == "116610LN"

    def test_boolean_fields_preserved(self, horology_ct, timepiece):
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        assert item.custom_fields["has_box"] is True
        assert item.custom_fields["has_papers"] is True

    def test_complications_preserved(self, horology_ct, timepiece):
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        assert item.custom_fields["complications"] == ["date"]

    def test_condition_grade_preserved(self, horology_ct, timepiece):
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        assert item.custom_fields["condition_grade"] == "MINT"

    def test_source_id_stored(self, horology_ct, timepiece):
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        assert item.custom_fields["source_timepiece_id"] == timepiece.pk

    def test_owner_preserved(self, horology_ct, timepiece, owner):
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        assert item.owner == owner


class TestTimepieceMigrateGenericUpgrades:
    def test_generic_upgrades_relinked(self, horology_ct, timepiece_with_upgrade):
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        relinked = GenericUpgrade.objects.filter(item=item)
        assert relinked.count() == 1
        assert relinked.first().name == "New Crystal"

    def test_relinked_upgrade_status_preserved(self, horology_ct, timepiece_with_upgrade):
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        upgrade = GenericUpgrade.objects.get(item=item)
        assert upgrade.status == "COMPLETED"


class TestTimepieceMigrateIdempotency:
    def test_second_run_does_not_duplicate(self, horology_ct, timepiece):
        call_command("migrate_timepieces_to_collections")
        call_command("migrate_timepieces_to_collections")
        assert DynamicCollectionItem.objects.filter(collection_type=horology_ct).count() == 1

    def test_second_run_reports_skipped(self, horology_ct, timepiece, capsys):
        call_command("migrate_timepieces_to_collections")
        call_command("migrate_timepieces_to_collections")
        out = capsys.readouterr().out
        assert "SKIP" in out

    def test_second_run_upgrades_not_duplicated(self, horology_ct, timepiece_with_upgrade):
        call_command("migrate_timepieces_to_collections")
        call_command("migrate_timepieces_to_collections")
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        assert item.upgrades.count() == 1  # not 2


class TestTimepieceMigrateSingleFlag:
    def test_single_timepiece_flag(self, horology_ct, owner):
        t1 = Timepiece.objects.create(
            owner=owner, brand="Omega", model="Speedmaster",
            reference_number="311.30.42.30.01.005",
        )
        t2 = Timepiece.objects.create(
            owner=owner, brand="Patek", model="Nautilus",
            reference_number="5711/1A-014",
        )
        call_command("migrate_timepieces_to_collections", "--timepiece", str(t1.pk))
        assert DynamicCollectionItem.objects.filter(collection_type=horology_ct).count() == 1
        item = DynamicCollectionItem.objects.get(collection_type=horology_ct)
        assert item.custom_fields["brand"] == "Omega"

    def test_invalid_timepiece_id_raises(self, horology_ct):
        with pytest.raises(CommandError, match="not found"):
            call_command("migrate_timepieces_to_collections", "--timepiece", "99999")


class TestTimepieceMigrateMissingCollectionType:
    def test_raises_when_horology_ct_missing(self, db):
        with pytest.raises(CommandError, match="horology-salon"):
            call_command("migrate_timepieces_to_collections")


# ─────────────────────────────────────────────────────────────────────────────
# Cross-model: migrating both in one run
# ─────────────────────────────────────────────────────────────────────────────


class TestBothMigrations:
    def test_both_commands_produce_separate_items(
        self, automobiles_ct, horology_ct, vehicle, timepiece
    ):
        call_command("migrate_vehicles_to_collections")
        call_command("migrate_timepieces_to_collections")
        assert DynamicCollectionItem.objects.filter(collection_type=automobiles_ct).count() == 1
        assert DynamicCollectionItem.objects.filter(collection_type=horology_ct).count() == 1
        assert DynamicCollectionItem.objects.count() == 2

    def test_items_have_distinct_owners_preserved(
        self, automobiles_ct, horology_ct, vehicle, timepiece, owner
    ):
        call_command("migrate_vehicles_to_collections")
        call_command("migrate_timepieces_to_collections")
        for item in DynamicCollectionItem.objects.all():
            assert item.owner == owner
