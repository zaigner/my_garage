"""
Management command: seed_system_collections

Creates (or updates) the two built-in CollectionType records that replace the
standalone Vehicle and Timepiece models after the unified-collections refactor.

Usage:
    pixi run manage seed_system_collections          # create/update
    pixi run manage seed_system_collections --dry-run  # preview only

These records are "system" collections distinguished by is_system=True (requires
the migration that adds that field to CollectionType).  They are seeded once and
then managed in code; do not let users delete or rename them via the UI.

Field type vocabulary used in these schemas
-------------------------------------------
Existing (already rendered by templates):
  text        Plain text input
  number      Numeric input (integer or decimal)
  date        Date picker

New types introduced by this refactor (requires template updates in Phase 3):
  select      Single-choice dropdown; field entry has a "choices" list
  boolean     Checkbox (yes/no); field entry has no extra keys
  json_list   Comma-separated tags rendered as a JSON array on save

System-only fields (populated by service providers, not user forms):
  system_json Read-only JSON blob; field entry has "system": true
              The form renderer must skip these. Service providers write to them.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

AUTOMOBILES_SCHEMA = {
    "fields": [
        # ── Primary Identity ────────────────────────────────────────────────
        {
            "name": "make",
            "type": "text",
            "label": "Make",
            "required": True,
            "help_text": "Manufacturer (e.g. Porsche, Toyota, Ford)",
        },
        {
            "name": "model",
            "type": "text",
            "label": "Model",
            "required": True,
            "help_text": "Model name (e.g. 911, Supra, Mustang)",
        },
        {
            "name": "year",
            "type": "number",
            "label": "Model Year",
            "required": True,
            "help_text": "Four-digit model year",
            "min": 1885,
            "max": 2100,
        },
        {
            "name": "trim",
            "type": "text",
            "label": "Trim / Edition",
            "required": False,
            "help_text": "e.g. GT3 RS, TRD Pro, Shelby GT500",
        },
        # ── Legal / Registration ─────────────────────────────────────────────
        {
            "name": "vin",
            "type": "text",
            "label": "VIN",
            "required": False,
            "help_text": "17-character Vehicle Identification Number — enables VIN decode",
            "max_length": 17,
            # NOTE: uniqueness is enforced at the service layer, not the schema.
            # The VehicleCollectionServices provider validates this before save.
        },
        {
            "name": "license_plate",
            "type": "text",
            "label": "License Plate",
            "required": False,
            "help_text": "Current registration plate",
            "max_length": 20,
        },
        # ── Collector Specs ──────────────────────────────────────────────────
        {
            "name": "transmission",
            "type": "select",
            "label": "Transmission",
            "required": False,
            "help_text": "Gearbox type",
            "choices": [
                {"value": "manual_4", "label": "4-Speed Manual"},
                {"value": "manual_5", "label": "5-Speed Manual"},
                {"value": "manual_6", "label": "6-Speed Manual"},
                {"value": "manual_7", "label": "7-Speed Manual"},
                {"value": "auto_4", "label": "4-Speed Automatic"},
                {"value": "auto_6", "label": "6-Speed Automatic"},
                {"value": "auto_7", "label": "7-Speed Automatic"},
                {"value": "auto_8", "label": "8-Speed Automatic"},
                {"value": "auto_10", "label": "10-Speed Automatic"},
                {"value": "dct_6", "label": "6-Speed DCT"},
                {"value": "dct_7", "label": "7-Speed DCT"},
                {"value": "dct_8", "label": "8-Speed DCT"},
                {"value": "pdk", "label": "PDK (Porsche)"},
                {"value": "cvt", "label": "CVT"},
                {"value": "single_speed", "label": "Single Speed (EV)"},
                {"value": "other", "label": "Other"},
            ],
        },
        {
            "name": "exterior_color",
            "type": "text",
            "label": "Exterior Color",
            "required": False,
            "help_text": "Specific paint name or factory code (e.g. Guards Red, 1B3)",
        },
        {
            "name": "interior_color",
            "type": "text",
            "label": "Interior Color",
            "required": False,
            "help_text": "e.g. Black leather, Cognac Alcantara",
        },
        {
            "name": "mileage",
            "type": "number",
            "label": "Odometer (miles)",
            "required": False,
            "help_text": "Current mileage reading — used in market valuation",
            "min": 0,
        },
        # ── System-populated fields (written by VehicleCollectionServices) ───
        # The form renderer MUST skip fields with "system": true.
        # They are stored in custom_fields and read by templates / MCP tools.
        {
            "name": "specs",
            "type": "system_json",
            "label": "Technical Specs",
            "required": False,
            "system": True,
            "help_text": "Auto-populated by VIN decoder — engine, drivetrain, body style, etc.",
        },
        {
            "name": "features",
            "type": "system_json",
            "label": "Factory Features",
            "required": False,
            "system": True,
            "help_text": "Auto-populated by VIN decoder — optional equipment list",
        },
    ]
}

AUTOMOBILES_LIST_DISPLAY = ["year", "make", "model", "trim", "mileage", "exterior_color"]

# ---------------------------------------------------------------------------

HOROLOGY_SCHEMA = {
    "fields": [
        # ── Primary Identity ────────────────────────────────────────────────
        {
            "name": "brand",
            "type": "text",
            "label": "Brand / Manufacture",
            "required": True,
            "help_text": "e.g. Patek Philippe, Rolex, A. Lange & Söhne",
        },
        {
            "name": "reference_number",
            "type": "text",
            "label": "Reference Number",
            "required": True,
            "help_text": "Manufacturer reference (e.g. 5711/1A-014) — primary valuation key",
            "max_length": 100,
        },
        {
            "name": "watch_model",
            "type": "text",
            "label": "Model Name",
            "required": True,
            "help_text": "e.g. Nautilus, Submariner, Saxonia",
        },
        {
            "name": "serial_number",
            "type": "text",
            "label": "Serial Number",
            "required": False,
            "help_text": "Private identifier — not shared in valuations",
            "max_length": 100,
        },
        {
            "name": "year",
            "type": "number",
            "label": "Year of Production",
            "required": False,
            "help_text": "Year the watch was manufactured",
            "min": 1700,
            "max": 2100,
        },
        # ── Horological Details ──────────────────────────────────────────────
        {
            "name": "movement_type",
            "type": "select",
            "label": "Movement Type",
            "required": False,
            "help_text": "The power source and escapement",
            "choices": [
                {"value": "AUTOMATIC", "label": "Automatic (Self-Winding)"},
                {"value": "MANUAL", "label": "Manual Wind"},
                {"value": "QUARTZ", "label": "Quartz"},
                {"value": "SPRING_DRIVE", "label": "Spring Drive (Grand Seiko)"},
                {"value": "COAXIAL", "label": "Co-Axial Escapement"},
                {"value": "TOURBILLON", "label": "Tourbillon"},
                {"value": "OTHER", "label": "Other"},
            ],
        },
        {
            "name": "case_material",
            "type": "text",
            "label": "Case Material",
            "required": False,
            "help_text": "e.g. 18k Rose Gold, Oystersteel, Platinum, Titanium",
        },
        {
            "name": "dial_color",
            "type": "text",
            "label": "Dial Color",
            "required": False,
            "help_text": "e.g. Sunburst Blue, Panda White, Salmon",
        },
        {
            "name": "complications",
            "type": "json_list",
            "label": "Complications",
            "required": False,
            "help_text": "Enter each complication separated by commas: Chronograph, GMT, Moonphase, Annual Calendar",
            # Stored as a JSON array: ["Chronograph", "GMT", "Moonphase"]
            "suggestions": [
                "Chronograph",
                "GMT / Dual Time",
                "Annual Calendar",
                "Perpetual Calendar",
                "Moonphase",
                "Tourbillon",
                "Minute Repeater",
                "Power Reserve Indicator",
                "World Time",
                "Flyback",
                "Rattrapante",
                "Alarm",
            ],
        },
        # ── Asset Value Factors ──────────────────────────────────────────────
        {
            "name": "has_box",
            "type": "boolean",
            "label": "Original Box",
            "required": False,
            "help_text": "Includes the manufacturer's original box (+value)",
        },
        {
            "name": "has_papers",
            "type": "boolean",
            "label": "Original Papers",
            "required": False,
            "help_text": "Includes warranty card, certificate, and documentation (+value)",
        },
        {
            "name": "condition_grade",
            "type": "select",
            "label": "Condition Grade",
            "required": False,
            "help_text": "Overall state of the watch — used in valuation calculation",
            "choices": [
                {"value": "UNWORN", "label": "Unworn / New Old Stock (NOS)"},
                {"value": "MINT", "label": "Mint — no visible wear"},
                {"value": "EXCELLENT", "label": "Excellent — light micro-scratches only"},
                {"value": "VERY_GOOD", "label": "Very Good — minor service marks"},
                {"value": "GOOD", "label": "Good — visible wear, fully functional"},
                {"value": "FAIR", "label": "Fair — heavy wear or polished"},
                {"value": "POOR", "label": "Poor — significant damage or non-running"},
            ],
        },
    ]
}

HOROLOGY_LIST_DISPLAY = [
    "brand",
    "reference_number",
    "watch_model",
    "movement_type",
    "condition_grade",
]

# ---------------------------------------------------------------------------
# The seed records (one entry per system CollectionType)
# ---------------------------------------------------------------------------

SYSTEM_COLLECTIONS = [
    {
        "name": "Automobiles",
        "slug": "automobiles",
        "icon": "fa-car",
        "description": (
            "Your vehicle collection. Supports VIN decoding, multi-source market "
            "valuation, service records, and project tracking."
        ),
        "service_provider_key": "vehicle",
        "field_schema": AUTOMOBILES_SCHEMA,
        "list_display_fields": AUTOMOBILES_LIST_DISPLAY,
    },
    {
        "name": "Horology Salon",
        "slug": "horology-salon",
        "icon": "fa-clock",
        "description": (
            "Fine timepiece gallery. Supports watch valuation with brand multipliers, "
            "completeness scoring, and the ChronoVault winder view."
        ),
        "service_provider_key": "timepiece",
        "field_schema": HOROLOGY_SCHEMA,
        "list_display_fields": HOROLOGY_LIST_DISPLAY,
    },
]


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Seed (create or update) the built-in Automobiles and Horology Salon collection types."

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

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        owner_username = options["owner"]

        # Resolve owner -------------------------------------------------------
        if owner_username:
            try:
                owner = User.objects.get(username=owner_username)
            except User.DoesNotExist:
                raise CommandError(f"User '{owner_username}' not found.")
        else:
            owner = User.objects.filter(is_superuser=True).order_by("date_joined").first()
            if not owner:
                raise CommandError(
                    "No superuser found. Create one first or pass --owner <username>."
                )

        self.stdout.write(f"Owner: {owner.username}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be written.\n"))

        # Import here to avoid app-registry issues at module load time
        from my_garage.models import CollectionType

        # Seed each collection -----------------------------------------------
        for config in SYSTEM_COLLECTIONS:
            slug = config["slug"]

            existing = CollectionType.objects.filter(slug=slug).first()

            if existing:
                action = "UPDATE"
            else:
                action = "CREATE"

            self.stdout.write(f"\n[{action}] CollectionType slug='{slug}'")
            self._print_schema_summary(config["field_schema"])

            if dry_run:
                continue

            if existing:
                # Update all fields except slug and owner (preserves user edits
                # to ui_theme_html but resets the authoritative schema fields).
                existing.name = config["name"]
                existing.icon = config["icon"]
                existing.description = config["description"]
                existing.field_schema = config["field_schema"]
                existing.list_display_fields = config["list_display_fields"]
                # service_provider_key requires the Phase 1 migration to exist.
                # Guard against running this command before that migration.
                if hasattr(existing, "service_provider_key"):
                    existing.service_provider_key = config["service_provider_key"]
                if hasattr(existing, "is_system"):
                    existing.is_system = True
                existing.save()
                self.stdout.write(self.style.SUCCESS(f"  Updated: {existing}"))
            else:
                kwargs = {
                    "name": config["name"],
                    "slug": config["slug"],
                    "icon": config["icon"],
                    "description": config["description"],
                    "owner": owner,
                    "field_schema": config["field_schema"],
                    "list_display_fields": config["list_display_fields"],
                }
                if "service_provider_key" in [
                    f.name for f in CollectionType._meta.get_fields()
                ]:
                    kwargs["service_provider_key"] = config["service_provider_key"]
                if "is_system" in [f.name for f in CollectionType._meta.get_fields()]:
                    kwargs["is_system"] = True

                ct = CollectionType(**kwargs)
                ct.save()
                self.stdout.write(self.style.SUCCESS(f"  Created: {ct}"))

        if not dry_run:
            self.stdout.write(self.style.SUCCESS("\nDone."))

    def _print_schema_summary(self, schema: dict) -> None:
        """Print a compact summary of a field_schema for dry-run output."""
        fields = schema.get("fields", [])
        for field in fields:
            required_marker = "*" if field.get("required") else " "
            system_marker = " [system]" if field.get("system") else ""
            choices_count = len(field.get("choices", []))
            type_hint = field["type"]
            if choices_count:
                type_hint = f"{type_hint}({choices_count} choices)"
            self.stdout.write(
                f"  {required_marker} {field['name']:<25} {type_hint}{system_marker}"
            )
