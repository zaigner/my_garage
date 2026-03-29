"""
Management command: migrate_vehicles_to_collections

Migrates all existing Vehicle rows into DynamicCollectionItem rows under the
"automobiles" system CollectionType, carrying across every related record:

  Vehicle              → DynamicCollectionItem (custom_fields)
  ServiceRecord        → GenericServiceRecord
  ValuationHistory     → GenericValuationHistory
  GenericUpgrade       → re-linked (content_type → DynamicCollectionItem)
  Upgrade (legacy)     → GenericUpgrade linked to new DynamicCollectionItem
  ConditionReport      → custom_fields["condition_reports"] JSON list
                         (Phase 5 can promote to a first-class model later)

Usage:
    pixi run manage migrate_vehicles_to_collections --dry-run   # preview
    pixi run manage migrate_vehicles_to_collections             # run
    pixi run manage migrate_vehicles_to_collections --vehicle 42  # single vehicle

The command is IDEMPOTENT: running it twice will not create duplicate
DynamicCollectionItem rows.  Idempotency is keyed on the `_source_vehicle_id`
value stored in the new item's custom_fields.

IMPORTANT: The original Vehicle rows and their related objects are NOT deleted.
Deletion is a separate Phase 5 step, performed only after the views and
templates are migrated and the new items are verified correct.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger(__name__)

# ── Category mapping: ServiceRecord choices → GenericServiceRecord choices ───
CATEGORY_MAP = {
    "MAINTENANCE": "MAINTENANCE",
    "REPAIR": "REPAIR",
    "UPGRADE": "UPGRADE",
}

# ── Upgrade status mapping: Upgrade → GenericUpgrade ─────────────────────────
UPGRADE_STATUS_MAP = {
    "WISHLIST": "WISHLIST",
    "ORDERED": "ORDERED",
    "INSTALLED": "COMPLETED",
}


class Command(BaseCommand):
    help = "Migrate Vehicle rows to DynamicCollectionItem under the Automobiles collection."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be migrated without writing to the database.",
        )
        parser.add_argument(
            "--vehicle",
            type=int,
            default=None,
            metavar="ID",
            help="Migrate a single vehicle by primary key (omit to migrate all).",
        )

    def handle(self, *args, **options):
        from my_garage.models import (
            CollectionType,
            ConditionReport,
            DynamicCollectionItem,
            GenericServiceRecord,
            GenericUpgrade,
            GenericValuationHistory,
            ServiceRecord,
            Upgrade,
            Vehicle,
            ValuationHistory,
        )

        dry_run: bool = options["dry_run"]
        vehicle_id: int | None = options["vehicle"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be written.\n"))

        # ── Resolve CollectionType ────────────────────────────────────────────
        try:
            automobiles_ct = CollectionType.objects.get(slug="automobiles")
        except CollectionType.DoesNotExist:
            raise CommandError(
                "CollectionType 'automobiles' not found. "
                "Run seed_system_collections first."
            )

        # ── Resolve vehicles to migrate ───────────────────────────────────────
        qs = Vehicle.objects.select_related("owner").prefetch_related(
            "services", "valuation_history", "upgrades", "projects", "condition_reports"
        )
        if vehicle_id is not None:
            qs = qs.filter(pk=vehicle_id)
            if not qs.exists():
                raise CommandError(f"Vehicle with id={vehicle_id} not found.")

        total = qs.count()
        self.stdout.write(f"Vehicles to migrate: {total}\n")

        migrated = skipped = 0

        for vehicle in qs.iterator(chunk_size=100):
            result = self._migrate_vehicle(
                vehicle=vehicle,
                automobiles_ct=automobiles_ct,
                dry_run=dry_run,
                models={
                    "DynamicCollectionItem": DynamicCollectionItem,
                    "GenericServiceRecord": GenericServiceRecord,
                    "GenericUpgrade": GenericUpgrade,
                    "GenericValuationHistory": GenericValuationHistory,
                    "ServiceRecord": ServiceRecord,
                    "Upgrade": Upgrade,
                    "ValuationHistory": ValuationHistory,
                    "ConditionReport": ConditionReport,
                },
            )
            if result == "migrated":
                migrated += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. migrated={migrated} skipped(already exists)={skipped}"
            )
        )

    # ─────────────────────────────────────────────────────────────────────────

    def _migrate_vehicle(self, *, vehicle, automobiles_ct, dry_run, models) -> str:
        """
        Migrate a single Vehicle.  Returns 'migrated' or 'skipped'.
        The entire operation for one vehicle is wrapped in an atomic transaction
        so a partial failure leaves no orphaned rows.
        """
        DynamicCollectionItem = models["DynamicCollectionItem"]

        # Idempotency check — keyed on _source_vehicle_id in custom_fields
        already_exists = DynamicCollectionItem.objects.filter(
            collection_type=automobiles_ct,
            owner=vehicle.owner,
            custom_fields__source_vehicle_id=vehicle.pk,
        ).exists()

        if already_exists:
            self.stdout.write(f"  SKIP  Vehicle pk={vehicle.pk} ({vehicle}) — already migrated")
            return "skipped"

        self.stdout.write(f"  {'DRY ' if dry_run else ''}MIGRATE  Vehicle pk={vehicle.pk} ({vehicle})")

        if dry_run:
            self._print_vehicle_summary(vehicle)
            return "migrated"

        with transaction.atomic():
            item = self._create_item(vehicle, automobiles_ct, DynamicCollectionItem)
            self._migrate_service_records(vehicle, item, models)
            self._migrate_valuation_history(vehicle, item, models)
            self._migrate_legacy_upgrades(vehicle, item, models)
            self._relink_generic_upgrades(vehicle, item, models)
            self._migrate_condition_reports(vehicle, item, models)

        self.stdout.write(
            f"    → DynamicCollectionItem pk={item.pk}: "
            f"{len(vehicle.services.all())} service records, "
            f"{vehicle.valuation_history.count()} valuation history entries, "
            f"{vehicle.upgrades.count()} legacy upgrades relinked"
        )
        return "migrated"

    # ── DynamicCollectionItem creation ────────────────────────────────────────

    def _create_item(self, vehicle, automobiles_ct, DynamicCollectionItem):
        """Build the DynamicCollectionItem from Vehicle fields."""
        custom_fields = {
            # Identity
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "trim": vehicle.trim,
            "vin": vehicle.vin or "",
            "license_plate": vehicle.license_plate,
            # Collector specs
            "transmission": vehicle.transmission,
            "exterior_color": vehicle.exterior_color,
            "interior_color": vehicle.interior_color,
            "mileage": vehicle.mileage,
            # System-populated VIN decoder fields
            "specs": vehicle.specs or {},
            "features": vehicle.features or {},
            # Source reference — used for idempotency and audit
            "source_vehicle_id": vehicle.pk,
            "migrated": True,
        }

        item = DynamicCollectionItem.objects.create(
            collection_type=automobiles_ct,
            owner=vehicle.owner,
            name=str(vehicle),                          # "2021 Toyota Tacoma"
            purchase_price=vehicle.purchase_price,
            purchase_date=vehicle.purchase_date,
            current_market_value=vehicle.current_market_value,
            notes=vehicle.notes,
            custom_fields=custom_fields,
        )

        # Copy the photo reference if one exists (file stays in place)
        if vehicle.photo:
            item.photo = vehicle.photo
            item.save(update_fields=["photo"])

        return item

    # ── ServiceRecord → GenericServiceRecord ─────────────────────────────────

    def _migrate_service_records(self, vehicle, item, models):
        GenericServiceRecord = models["GenericServiceRecord"]

        for record in vehicle.services.all():
            GenericServiceRecord.objects.create(
                item=item,
                date=record.date,
                vendor=record.vendor,
                description=record.description,
                category=CATEGORY_MAP.get(record.category, "OTHER"),
                total_cost=record.total_cost,
                ocr_raw_data=record.ocr_raw_data,
                is_verified=record.is_verified,
                # receipt_image: copy file reference if one exists (file stays in place)
                receipt_image=record.receipt_image if record.receipt_image else None,
            )

    # ── ValuationHistory → GenericValuationHistory ────────────────────────────

    def _migrate_valuation_history(self, vehicle, item, models):
        GenericValuationHistory = models["GenericValuationHistory"]

        for entry in vehicle.valuation_history.all():
            GenericValuationHistory.objects.create(
                item=item,
                value=entry.value,
                raw_data=entry.raw_data,
            )
            # Note: auto_now_add on date means we lose the original timestamp.
            # The raw_data preserves the full API response for audit purposes.

    # ── Legacy Upgrade → GenericUpgrade ──────────────────────────────────────

    def _migrate_legacy_upgrades(self, vehicle, item, models):
        """
        Migrate Upgrade (Vehicle FK) rows to GenericUpgrade linked via item FK.
        These are the pre-GenericRelation upgrades not yet migrated by the
        migrate_vehicle_upgrades command.
        """
        GenericUpgrade = models["GenericUpgrade"]
        Upgrade = models["Upgrade"]

        for upgrade in Upgrade.objects.filter(vehicle=vehicle):
            GenericUpgrade.objects.create(
                item=item,
                name=upgrade.part_name,
                brand=upgrade.brand,
                part_number=upgrade.part_number,
                status=UPGRADE_STATUS_MAP.get(upgrade.status, "WISHLIST"),
                cost=upgrade.cost,
                completion_date=upgrade.installation_date,
                notes=upgrade.notes,
            )

    # ── Re-link existing GenericUpgrade (content_type=Vehicle) ───────────────

    def _relink_generic_upgrades(self, vehicle, item, models):
        """
        GenericUpgrade rows that currently point to the Vehicle via
        content_type + object_id need their item FK set to the new
        DynamicCollectionItem.  We keep content_type/object_id intact for
        the Phase 5 cleanup; the item FK is sufficient for Phase 2 views.
        """
        GenericUpgrade = models["GenericUpgrade"]

        vehicle_ct = ContentType.objects.get_for_model(vehicle)
        GenericUpgrade.objects.filter(
            content_type=vehicle_ct,
            object_id=vehicle.pk,
            item__isnull=True,
        ).update(item=item)

    # ── ConditionReport → custom_fields JSON list ─────────────────────────────

    def _migrate_condition_reports(self, vehicle, item, models):
        """
        Store condition reports as a JSON list in custom_fields so the data
        is preserved until Phase 5 can introduce a proper generic model.
        The photo FileField names are stored as strings; files stay in place.
        """
        ConditionReport = models["ConditionReport"]

        reports = list(
            ConditionReport.objects.filter(vehicle=vehicle)
            .values("area", "grade", "ai_feedback", "value_adjustment", "created_at", "photo")
            .order_by("-created_at")
        )

        if not reports:
            return

        serialisable = []
        for r in reports:
            serialisable.append({
                "area": r["area"],
                "grade": float(r["grade"]),
                "ai_feedback": r["ai_feedback"],
                "value_adjustment": str(r["value_adjustment"]),
                "created_at": r["created_at"].isoformat(),
                "photo": str(r["photo"]) if r["photo"] else "",
            })

        item.custom_fields["condition_reports"] = serialisable
        item.save(update_fields=["custom_fields"])

    # ── Dry-run summary helper ────────────────────────────────────────────────

    def _print_vehicle_summary(self, vehicle):
        from my_garage.models import Upgrade

        service_count = vehicle.services.count()
        valuation_count = vehicle.valuation_history.count()
        legacy_upgrade_count = Upgrade.objects.filter(vehicle=vehicle).count()
        generic_upgrade_count = vehicle.projects.count()
        condition_count = vehicle.condition_reports.count()
        has_photo = bool(vehicle.photo)

        self.stdout.write(
            f"    service_records={service_count}  "
            f"valuation_history={valuation_count}  "
            f"legacy_upgrades={legacy_upgrade_count}  "
            f"generic_upgrades={generic_upgrade_count}  "
            f"condition_reports={condition_count}  "
            f"photo={'yes' if has_photo else 'no'}"
        )
