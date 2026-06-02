"""
Management command: backfill_nfp

Calculates and saves net_financial_position for every DynamicCollectionItem
that was created before the NFP signal handlers were active.

This is a one-time deployment step run after applying migration 0012.
Safe to re-run — idempotent.

Usage:
    pixi run manage backfill_nfp
    pixi run manage backfill_nfp --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from my_garage.api.services import refresh_item_nfp
from my_garage.models import DynamicCollectionItem


class Command(BaseCommand):
    help = "Backfill net_financial_position for all existing DynamicCollectionItem records."  # noqa: E501

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report counts without writing any values.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        total = DynamicCollectionItem.objects.count()

        if total == 0:
            self.stdout.write("backfill_nfp: 0 items found — nothing to do.")
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"backfill_nfp --dry-run: {total} item(s) would be processed "
                    "(no writes performed)."
                )
            )
            return

        updated = 0
        skipped = 0

        for item in DynamicCollectionItem.objects.iterator():
            refresh_item_nfp(item)
            item.refresh_from_db(fields=["net_financial_position"])
            if item.net_financial_position is None:
                skipped += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"backfill_nfp: {total} item(s) processed — "
                f"{updated} updated, {skipped} skipped (null market value)."
            )
        )
