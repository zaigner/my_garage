"""
Management command: seed_system_collections

Creates (or repairs) the built-in ``is_system`` CollectionType records for a
single owner.  Schemas live in ``my_garage.collection_blueprints`` — this
command only applies them.

Usage:
    pixi run manage seed_system_collections                      # first superuser
    pixi run manage seed_system_collections --owner alice        # specific user
    pixi run manage seed_system_collections --dry-run            # preview only
    pixi run manage seed_system_collections --coerce-data        # + repair item data

Everything is scoped to ``(owner, slug)``.  Running it for one user never reads
or writes another user's collections.

Why --coerce-data exists
------------------------
The ``select`` / ``boolean`` / ``json_list`` field types were defined in the
blueprints before the form renderer could render them, so early collections had
those fields flattened to ``text``.  Re-applying the blueprint fixes the schema
but leaves item values in the old shape — a ``condition_grade`` of ``"Good"``
where the choice value is now ``"GOOD"`` would render as an empty dropdown.

``--coerce-data`` walks the owner's items in the affected collections and
migrates each stored value to match the new field type.  It is idempotent:
values already in the target shape are left alone.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from my_garage.collection_blueprints import SYSTEM_BLUEPRINTS, load_ui_theme

User = get_user_model()


# ---------------------------------------------------------------------------
# Value coercion
# ---------------------------------------------------------------------------

_TRUTHY = {"true", "yes", "y", "1", "on", "t"}
_FALSY = {"false", "no", "n", "0", "off", "f", ""}


def _coerce_boolean(value):
    """Map common textual truth values onto real bools."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _TRUTHY:
            return True
        if lowered in _FALSY:
            return False
    return value


def _coerce_json_list(value):
    """Split a comma-separated string into a list; pass lists through."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return value


def _coerce_select(value, field_def: dict):
    """
    Map a free-text value onto one of the field's choice values.

    Tries, in order: exact value, case-insensitive value, full label, then the
    label's head (labels often read "Good — visible wear, fully functional").
    """
    if not isinstance(value, str):
        return value

    choices = field_def.get("choices", [])
    valid_values = {choice.get("value") for choice in choices}
    if value in valid_values:
        return value  # already a choice value

    candidate = value.strip().lower()

    for choice_value in valid_values:
        if choice_value and candidate == str(choice_value).lower():
            return choice_value

    for choice in choices:
        label = str(choice.get("label", ""))
        if candidate == label.lower():
            return choice.get("value")
        head = label.split("—")[0].strip()
        if head and candidate == head.lower():
            return choice.get("value")

    return value  # unmappable — left for a human to resolve


_COERCERS = {
    "boolean": lambda value, _field: _coerce_boolean(value),
    "json_list": lambda value, _field: _coerce_json_list(value),
    "select": _coerce_select,
}


def coerce_value(value, field_def: dict):
    """
    Return *value* reshaped to suit ``field_def["type"]``.

    Returns the value unchanged when it is already correct or cannot be mapped
    confidently — this never guesses destructively.
    """
    if value is None:
        return value
    coercer = _COERCERS.get(field_def.get("type"))
    return coercer(value, field_def) if coercer else value


def coerce_item_fields(custom_fields: dict, schema: dict) -> tuple[dict, list[str]]:
    """
    Coerce every value in *custom_fields* to match *schema*.

    Returns ``(new_custom_fields, changes)`` where ``changes`` is a list of
    human-readable descriptions of what moved.
    """
    updated = dict(custom_fields or {})
    changes: list[str] = []

    for field_def in schema.get("fields", []):
        name = field_def.get("name")
        if name not in updated:
            continue
        before = updated[name]
        after = coerce_value(before, field_def)
        if after != before:
            updated[name] = after
            changes.append(f"{name}: {before!r} -> {after!r}")

    return updated, changes


def find_unmappable(custom_fields: dict, schema: dict) -> list[str]:
    """Return descriptions of select values that survived coercion unmapped."""
    problems: list[str] = []
    for field_def in schema.get("fields", []):
        if field_def.get("type") != "select":
            continue
        name = field_def.get("name")
        value = (custom_fields or {}).get(name)
        if not value or not isinstance(value, str):
            continue
        valid = {choice.get("value") for choice in field_def.get("choices", [])}
        if value not in valid:
            problems.append(
                f"{name}={value!r} is not one of {sorted(v for v in valid)}"
            )
    return problems


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Seed or repair the built-in system collection types for one owner."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created/updated without writing to the database.",
        )
        parser.add_argument(
            "--owner",
            type=str,
            default=None,
            help=(
                "Username to assign as owner of the system collections. "
                "Defaults to the first superuser found."
            ),
        )
        parser.add_argument(
            "--coerce-data",
            action="store_true",
            help=(
                "Also migrate existing item values to match the refreshed schema "
                "(text -> select/boolean/json_list)."
            ),
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        coerce_data = options["coerce_data"]
        owner = self._resolve_owner(options["owner"])

        self.stdout.write(f"Owner: {owner.username}")
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN — no changes will be written.\n")
            )

        with transaction.atomic():
            for blueprint in SYSTEM_BLUEPRINTS:
                self._seed_one(blueprint, owner, dry_run=dry_run)
                if coerce_data:
                    self._coerce_one(blueprint, owner, dry_run=dry_run)

            if dry_run:
                transaction.set_rollback(True)

        if not dry_run:
            self.stdout.write(self.style.SUCCESS("\nDone."))

    # -- helpers ---------------------------------------------------------

    def _resolve_owner(self, owner_username: str | None):
        if owner_username:
            try:
                return User.objects.get(username=owner_username)
            except User.DoesNotExist as e:
                raise CommandError(f"User '{owner_username}' not found.") from e

        owner = User.objects.filter(is_superuser=True).order_by("date_joined").first()
        if not owner:
            raise CommandError(
                "No superuser found. Create one first or pass --owner <username>."
            )
        return owner

    def _seed_one(self, blueprint: dict, owner, *, dry_run: bool) -> None:
        from my_garage.models import CollectionType

        slug = blueprint["slug"]
        # Scoped to this owner — never touches another user's collections.
        existing = CollectionType.objects.filter(owner=owner, slug=slug).first()
        action = "UPDATE" if existing else "CREATE"

        self.stdout.write(f"\n[{action}] CollectionType slug='{slug}'")
        self._print_schema_summary(blueprint["field_schema"])

        if dry_run and not existing:
            return

        if existing:
            existing.name = blueprint["name"]
            existing.icon = blueprint["icon"]
            existing.description = blueprint["description"]
            existing.field_schema = blueprint["field_schema"]
            existing.list_display_fields = blueprint["list_display_fields"]
            existing.service_provider_key = blueprint["service_provider_key"]
            existing.is_system = blueprint.get("is_system", False)
            # Preserve a theme the user customised in the UI; only fill a blank.
            if not existing.ui_theme_html:
                existing.ui_theme_html = load_ui_theme(blueprint)
            existing.save()
            self.stdout.write(self.style.SUCCESS(f"  Updated: {existing}"))
        else:
            ctype = CollectionType(
                owner=owner,
                slug=blueprint["slug"],
                name=blueprint["name"],
                icon=blueprint["icon"],
                description=blueprint["description"],
                field_schema=blueprint["field_schema"],
                list_display_fields=blueprint["list_display_fields"],
                service_provider_key=blueprint["service_provider_key"],
                is_system=blueprint.get("is_system", False),
                ui_theme_html=load_ui_theme(blueprint),
            )
            ctype.save()
            self.stdout.write(self.style.SUCCESS(f"  Created: {ctype}"))

    def _coerce_one(self, blueprint: dict, owner, *, dry_run: bool) -> None:
        from my_garage.models import CollectionType, DynamicCollectionItem

        ctype = CollectionType.objects.filter(
            owner=owner, slug=blueprint["slug"]
        ).first()
        if not ctype:
            return

        schema = blueprint["field_schema"]
        items = DynamicCollectionItem.objects.filter(collection_type=ctype, owner=owner)

        for item in items:
            updated, changes = coerce_item_fields(item.custom_fields, schema)
            if changes:
                for change in changes:
                    self.stdout.write(f"    [{item.id}] {item.name}: {change}")
                if not dry_run:
                    item.custom_fields = updated
                    item.save(update_fields=["custom_fields"])

            for problem in find_unmappable(updated, schema):
                self.stdout.write(
                    self.style.WARNING(
                        f"    [{item.id}] {item.name}: {problem} — set it manually"
                    )
                )

    def _print_schema_summary(self, schema: dict) -> None:
        """Print a compact summary of a field_schema for dry-run output."""
        for field in schema.get("fields", []):
            required_marker = "*" if field.get("required") else " "
            system_marker = " [system]" if field.get("system") else ""
            choices_count = len(field.get("choices", []))
            type_hint = field["type"]
            if choices_count:
                type_hint = f"{type_hint}({choices_count} choices)"
            self.stdout.write(
                f"  {required_marker} {field['name']:<25} {type_hint}{system_marker}"
            )
