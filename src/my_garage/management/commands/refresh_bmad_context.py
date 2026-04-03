"""
Management command: refresh_bmad_context

Queries live portfolio statistics and rewrites the `## Current Project State`
section of _bmad/_memory/project-context.md.

Safe to run on a schedule — the static sections of the file are never touched.
Only the table under `## Current Project State` is replaced.

Usage:
    pixi run refresh-context
    pixi run manage refresh_bmad_context
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.db.models.functions import Coalesce

from my_garage.models import CollectionType, DynamicCollectionItem

User = get_user_model()

# Path to the context file relative to BASE_DIR
CONTEXT_FILE = Path(settings.BASE_DIR) / "_bmad/_memory/project-context.md"

# Regex to find and replace the Current Project State section
_SECTION_PATTERN = re.compile(
    r"(## Current Project State\n)(.*?)(\Z|\n## )",
    re.DOTALL,
)


class Command(BaseCommand):
    help = (
        "Refresh the ## Current Project State section of "
        "_bmad/_memory/project-context.md with live portfolio data."
    )

    def handle(self, *args, **options):
        if not CONTEXT_FILE.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Context file not found: {CONTEXT_FILE}\n"
                    "Run the BMAD generate-project-context command first."
                )
            )
            return

        stats = self._collect_stats()
        new_section = self._build_section(stats)

        original = CONTEXT_FILE.read_text(encoding="utf-8")
        updated = self._replace_section(original, new_section)

        if updated == original:
            self.stdout.write("No changes — context is already up to date.")
            return

        CONTEXT_FILE.write_text(updated, encoding="utf-8")
        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {CONTEXT_FILE.name} with latest portfolio stats."
            )
        )

    # ------------------------------------------------------------------

    def _collect_stats(self) -> dict:
        def _sum(qs, field="current_market_value") -> Decimal:
            result = qs.aggregate(total=Coalesce(Sum(field), Decimal("0.00")))["total"]
            return result or Decimal("0.00")

        items = DynamicCollectionItem.objects.all()
        collection_types = CollectionType.objects.filter(is_active=True)

        items_val = _sum(items)

        type_names = list(
            collection_types.values_list("name", flat=True).order_by("name")
        )

        return {
            "collection_type_count": collection_types.count(),
            "collection_item_count": items.count(),
            "total_collections_value": items_val,
            "total_portfolio_value": items_val,
            "collection_types": type_names,
            "refreshed_at": datetime.now(tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
        }

    def _build_section(self, stats: dict) -> str:
        types_str = (
            ", ".join(stats["collection_types"])
            if stats["collection_types"]
            else "none"
        )

        return (
            "## Current Project State\n\n"
            "> Auto-refreshed by `pixi run refresh-context`. "
            f"Last updated: {stats['refreshed_at']}\n\n"
            "| Metric | Value |\n"
            "|---|---|\n"
            f"| Collection types | {stats['collection_type_count']} ({types_str}) |\n"
            f"| Collection items | {stats['collection_item_count']} |\n"
            f"| Collections value | ${stats['total_collections_value']:,.2f} |\n"
            f"| **Total portfolio value** | **${stats['total_portfolio_value']:,.2f}** |\n"
            f"| Last refresh | {stats['refreshed_at']} |\n"
        )

    def _replace_section(self, content: str, new_section: str) -> str:
        """
        Replace the ## Current Project State section.
        Handles files that end with the section (no following ## header).
        """
        # Find the section start
        marker = "## Current Project State\n"
        start_idx = content.find(marker)
        if start_idx == -1:
            # Section not found — append it
            return content.rstrip() + "\n\n---\n\n" + new_section + "\n"

        # Find the next ## heading after the section (or EOF)
        next_header = re.search(r"\n## ", content[start_idx + len(marker) :])
        if next_header:
            end_idx = start_idx + len(marker) + next_header.start()
            return content[:start_idx] + new_section + "\n" + content[end_idx:]
        else:
            # Section is the last one in the file
            return content[:start_idx] + new_section + "\n"
