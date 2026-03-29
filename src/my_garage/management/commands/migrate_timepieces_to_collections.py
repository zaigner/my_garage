"""
Management command: migrate_timepieces_to_collections

Migrates all existing Timepiece rows into DynamicCollectionItem rows under the
"horology-salon" system CollectionType, carrying across every related record:

  Timepiece            → DynamicCollectionItem (custom_fields)
  GenericUpgrade       → re-linked (content_type → DynamicCollectionItem)

Note: Timepieces have no ServiceRecord or ValuationHistory equivalents in the
legacy model — those were already generic (GenericServiceRecord /
GenericValuationHistory).  GenericUpgrade rows are re-linked via the item FK.

Usage:
    pixi run manage migrate_timepieces_to_collections --dry-run   # preview
    pixi run manage migrate_timepieces_to_collections             # run
    pixi run manage migrate_timepieces_to_collections --timepiece 7  # single

The command is IDEMPOTENT: running it twice will not create duplicates.
Idempotency is keyed on the `_source_timepiece_id` value in custom_fields.

IMPORTANT: Original Timepiece rows are NOT deleted.  Deletion is Phase 5.
"""
from __future__ import annotations

import logging

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate Timepiece rows to DynamicCollectionItem under the Horology Salon collection."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be migrated without writing to the database.",
        )
        parser.add_argument(
            "--timepiece",
            type=int,
            default=None,
            metavar="ID",
            help="Migrate a single timepiece by primary key (omit to migrate all).",
        )

    def handle(self, *args, **options):
        from my_garage.models import (
            CollectionType,
            DynamicCollectionItem,
            GenericUpgrade,
            Timepiece,
        )

        dry_run: bool = options["dry_run"]
        timepiece_id: int | None = options["timepiece"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be written.\n"))

        # ── Resolve CollectionType ────────────────────────────────────────────
        try:
            horology_ct = CollectionType.objects.get(slug="horology-salon")
        except CollectionType.DoesNotExist:
            raise CommandError(
                "CollectionType 'horology-salon' not found. "
                "Run seed_system_collections first."
            )

        # ── Resolve timepieces to migrate ─────────────────────────────────────
        qs = Timepiece.objects.select_related("owner").prefetch_related("projects")
        if timepiece_id is not None:
            qs = qs.filter(pk=timepiece_id)
            if not qs.exists():
                raise CommandError(f"Timepiece with id={timepiece_id} not found.")

        total = qs.count()
        self.stdout.write(f"Timepieces to migrate: {total}\n")

        migrated = skipped = 0

        for timepiece in qs.iterator(chunk_size=100):
            result = self._migrate_timepiece(
                timepiece=timepiece,
                horology_ct=horology_ct,
                dry_run=dry_run,
                DynamicCollectionItem=DynamicCollectionItem,
                GenericUpgrade=GenericUpgrade,
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

    def _migrate_timepiece(
        self, *, timepiece, horology_ct, dry_run, DynamicCollectionItem, GenericUpgrade
    ) -> str:
        """Migrate a single Timepiece.  Returns 'migrated' or 'skipped'."""

        # Idempotency check
        already_exists = DynamicCollectionItem.objects.filter(
            collection_type=horology_ct,
            owner=timepiece.owner,
            custom_fields__source_timepiece_id=timepiece.pk,
        ).exists()

        if already_exists:
            self.stdout.write(
                f"  SKIP  Timepiece pk={timepiece.pk} ({timepiece}) — already migrated"
            )
            return "skipped"

        self.stdout.write(
            f"  {'DRY ' if dry_run else ''}MIGRATE  Timepiece pk={timepiece.pk} ({timepiece})"
        )

        if dry_run:
            self._print_timepiece_summary(timepiece)
            return "migrated"

        with transaction.atomic():
            item = self._create_item(timepiece, horology_ct, DynamicCollectionItem)
            self._relink_generic_upgrades(timepiece, item, GenericUpgrade)

        self.stdout.write(
            f"    → DynamicCollectionItem pk={item.pk}: "
            f"{timepiece.projects.count()} generic upgrades relinked"
        )
        return "migrated"

    # ── DynamicCollectionItem creation ────────────────────────────────────────

    def _create_item(self, timepiece, horology_ct, DynamicCollectionItem):
        """Build the DynamicCollectionItem from Timepiece fields.

        Note: Timepiece.model is stored as 'watch_model' to avoid Python/ORM
        naming collision (see docs/schemas/FIELD_TYPES.md).
        """
        custom_fields = {
            # Identity
            "brand": timepiece.brand,
            "watch_model": timepiece.model,          # renamed to avoid collision
            "reference_number": timepiece.reference_number,
            "serial_number": timepiece.serial_number,
            "year": timepiece.year,
            # Horological details
            "movement_type": timepiece.movement_type,
            "case_material": timepiece.case_material,
            "dial_color": timepiece.dial_color,
            "complications": timepiece.complications or [],
            # Value factors
            "has_box": timepiece.has_box,
            "has_papers": timepiece.has_papers,
            "condition_grade": timepiece.condition_grade,
            # Source reference — used for idempotency and audit
            "source_timepiece_id": timepiece.pk,
            "migrated": True,
        }

        item = DynamicCollectionItem.objects.create(
            collection_type=horology_ct,
            owner=timepiece.owner,
            name=str(timepiece),                         # "Rolex Submariner (116610LN)"
            purchase_price=timepiece.purchase_price,
            purchase_date=timepiece.purchase_date,
            current_market_value=timepiece.current_market_value,
            notes=timepiece.notes,
            custom_fields=custom_fields,
        )

        # Copy photo reference if one exists (file stays in place)
        if timepiece.photo:
            item.photo = timepiece.photo
            item.save(update_fields=["photo"])

        return item

    # ── Re-link existing GenericUpgrade (content_type=Timepiece) ─────────────

    def _relink_generic_upgrades(self, timepiece, item, GenericUpgrade):
        """
        GenericUpgrade rows pointing to Timepiece via content_type + object_id
        get their item FK set to the new DynamicCollectionItem.
        """
        timepiece_ct = ContentType.objects.get_for_model(timepiece)
        GenericUpgrade.objects.filter(
            content_type=timepiece_ct,
            object_id=timepiece.pk,
            item__isnull=True,
        ).update(item=item)

    # ── Dry-run summary ───────────────────────────────────────────────────────

    def _print_timepiece_summary(self, timepiece):
        generic_upgrade_count = timepiece.projects.count()
        has_photo = bool(timepiece.photo)
        has_box = timepiece.has_box
        has_papers = timepiece.has_papers

        self.stdout.write(
            f"    generic_upgrades={generic_upgrade_count}  "
            f"photo={'yes' if has_photo else 'no'}  "
            f"box={'yes' if has_box else 'no'}  "
            f"papers={'yes' if has_papers else 'no'}"
        )
