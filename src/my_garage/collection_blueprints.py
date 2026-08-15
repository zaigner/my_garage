"""
Collection blueprints — the starter catalogue offered to every user.

A *blueprint* is a fully-formed CollectionType definition held in code.  Users
adopt one from the onboarding picker and get a working collection immediately:
no AI schema generation, no JSON editing, no input screens.

Two consumers share this module:

  * ``services.collection_provisioning.provision_collections`` — instantiates
    blueprints for a user who picked them.
  * ``management.commands.seed_system_collections`` — creates/repairs the
    ``is_system`` blueprints for an existing owner.

Field type vocabulary
---------------------
Rendered by ``DynamicCollectionItemForm``:

  text        Plain text input
  number      Numeric input (integer or decimal)
  date        Date picker
  file        File upload
  select      Single-choice dropdown; entry carries a "choices" list
  boolean     Checkbox; always optional at the HTML level
  json_list   Comma-separated input stored as a JSON array; entry may carry
              a "suggestions" list used as placeholder/autocomplete hints

Skipped by the form renderer, written by service providers instead:

  system_json Read-only JSON blob; entry carries "system": true

Icons
-----
FontAwesome 6 needs a style-family prefix — a bare ``fa-car`` renders nothing.
Every icon here is written as ``fa-solid fa-*``.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

THEME_DIR = Path(__file__).parent / "collection_themes"


# ---------------------------------------------------------------------------
# System blueprints — backed by dedicated service providers
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
            "help_text": "17-character Vehicle Identification Number — enables VIN decode",  # noqa: E501
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
        # The form renderer skips fields with "system": true.
        # They are stored in custom_fields and read by templates / MCP tools.
        {
            "name": "specs",
            "type": "system_json",
            "label": "Technical Specs",
            "required": False,
            "system": True,
            "help_text": "Auto-populated by VIN decoder — engine, drivetrain, body style, etc.",  # noqa: E501
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

AUTOMOBILES_LIST_DISPLAY = [
    "year",
    "make",
    "model",
    "trim",
    "mileage",
    "exterior_color",
]

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
            "help_text": "Manufacturer reference (e.g. 5711/1A-014) — primary valuation key",  # noqa: E501
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
            "help_text": "Enter each complication separated by commas: Chronograph, GMT, Moonphase, Annual Calendar",  # noqa: E501
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
            "help_text": "Includes warranty card, certificate, and documentation (+value)",  # noqa: E501
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
                {
                    "value": "EXCELLENT",
                    "label": "Excellent — light micro-scratches only",
                },
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
# The catalogue
# ---------------------------------------------------------------------------

COLLECTION_BLUEPRINTS: list[dict] = [
    {
        "slug": "automobiles",
        "name": "Automobiles",
        "icon": "fa-solid fa-car",
        "description": (
            "Your vehicle collection. Supports VIN decoding, multi-source market "
            "valuation, service records, and project tracking."
        ),
        "preview": "VIN decoding, market valuation, service history, and projects.",
        "service_provider_key": "vehicle",
        "is_system": True,
        "field_schema": AUTOMOBILES_SCHEMA,
        "list_display_fields": AUTOMOBILES_LIST_DISPLAY,
    },
    {
        "slug": "horology-salon",
        "name": "Horology Salon",
        "icon": "fa-solid fa-clock",
        "description": (
            "Fine timepiece gallery. Supports watch valuation with brand multipliers "
            "and completeness scoring."
        ),
        "preview": "Watch valuation with brand multipliers and box/papers completeness scoring.",  # noqa: E501
        "service_provider_key": "timepiece",
        "is_system": True,
        "field_schema": HOROLOGY_SCHEMA,
        "list_display_fields": HOROLOGY_LIST_DISPLAY,
    },
    # ── Generic blueprints (default service provider) ────────────────────────
    # Extracted from the reference collection set; see git history for origin.
    {
        "slug": "the-gun-safe",
        "name": "The Gun Safe",
        "icon": "fa-solid fa-gun",
        "description": "The Gun Safe keeps records of all my firearms",
        "preview": "Serialised firearms register with NRA condition grading.",
        "service_provider_key": "default",
        "is_system": False,
        "field_schema": {
            "fields": [
                {
                    "name": "serial_number",
                    "type": "text",
                    "label": "Serial Number",
                    "required": True,
                    "help_text": (
                        "Unique identification number etched or stamped on the firearm."
                    ),
                },
                {
                    "name": "manufacturer",
                    "type": "text",
                    "label": "Manufacturer",
                    "required": True,
                    "help_text": (
                        "The company or entity that originally produced the firearm."
                    ),
                },
                {
                    "name": "model",
                    "type": "text",
                    "label": "Model",
                    "required": True,
                    "help_text": (
                        "The specific model name or designation of the firearm (e.g., "
                        "'1911', 'AR-15', 'Model 70')."
                    ),
                },
                {
                    "name": "caliber_gauge",
                    "type": "text",
                    "label": "Caliber / Gauge",
                    "required": True,
                    "help_text": (
                        "The specific ammunition caliber (e.g., '.45 ACP', '9mm "
                        "Luger', '.30-06 Springfield') or shotgun gauge (e.g., '12 "
                        "GA', '20 GA')."
                    ),
                },
                {
                    "name": "firearm_type",
                    "type": "text",
                    "label": "Firearm Type",
                    "required": True,
                    "help_text": (
                        "General classification of the firearm (e.g., 'Rifle', "
                        "'Pistol', 'Revolver', 'Shotgun', 'Derringer')."
                    ),
                },
                {
                    "name": "action_type",
                    "type": "text",
                    "label": "Action Type",
                    "required": True,
                    "help_text": (
                        "The mechanism by which the firearm loads, fires, and ejects "
                        "cartridges (e.g., 'Bolt-Action', 'Semi-Automatic', "
                        "'Pump-Action', 'Lever-Action', 'Break-Action', "
                        "'Double-Action/Single-Action')."
                    ),
                },
                {
                    "name": "barrel_length_inches",
                    "type": "number",
                    "label": "Barrel Length (in)",
                    "required": True,
                    "help_text": (
                        "The length of the barrel, typically measured from the muzzle "
                        "to the bolt face, in inches."
                    ),
                },
                {
                    "name": "condition_nra_rating",
                    "type": "text",
                    "label": "NRA Condition Rating",
                    "required": False,
                    "help_text": (
                        "The firearm's condition based on NRA Modern Gun Condition "
                        "Standards (e.g., 'Excellent', 'Very Good', 'Good', 'Fair', "
                        "'Poor')."
                    ),
                },
            ],
        },
        "list_display_fields": [
            "serial_number",
            "manufacturer",
            "model",
            "caliber_gauge",
            "firearm_type",
            "action_type",
            "barrel_length_inches",
            "condition_nra_rating",
        ],
    },
    {
        "slug": "coin-collection",
        "name": "Coin Collection",
        "icon": "fa-solid fa-coins",
        "description": "This collection is made up of rare coins",
        "preview": "Numismatic catalogue with mint marks, grades, and a gallery theme.",
        "service_provider_key": "default",
        "is_system": False,
        "field_schema": {
            "fields": [
                {
                    "name": "country_of_origin",
                    "type": "text",
                    "label": "Country/Issuing Authority",
                    "required": True,
                    "help_text": "The country or entity that issued the coin.",
                },
                {
                    "name": "denomination",
                    "type": "text",
                    "label": "Denomination",
                    "required": True,
                    "help_text": (
                        "The face value of the coin (e.g., '1 Dollar', '5 Cents', '1/2"
                        " Anna')."
                    ),
                },
                {
                    "name": "year_of_issue",
                    "type": "number",
                    "label": "Year of Issue",
                    "required": True,
                    "help_text": "The calendar year the coin was minted.",
                },
                {
                    "name": "mint_mark",
                    "type": "text",
                    "label": "Mint Mark",
                    "required": False,
                    "help_text": (
                        "The identifier indicating the specific minting facility "
                        "(e.g., 'S' for San Francisco, 'D' for Denver)."
                    ),
                },
                {
                    "name": "metal_composition",
                    "type": "text",
                    "label": "Metal Composition",
                    "required": True,
                    "help_text": (
                        "The primary metals and purity used in the coin (e.g., '90% "
                        "Silver', 'Copper-Nickel', 'Gold .999 Fine')."
                    ),
                },
                {
                    "name": "edge_type",
                    "type": "text",
                    "label": "Edge Type",
                    "required": False,
                    "help_text": (
                        "Description of the coin's edge (e.g., 'Reeded', 'Plain', "
                        "'Lettered')."
                    ),
                },
                {
                    "name": "certified_grade",
                    "type": "text",
                    "label": "Certified Grade",
                    "required": False,
                    "help_text": (
                        "The professional numeric or alphanumeric grade assigned to "
                        "the coin (e.g., 'MS-65', 'AU-58', 'VF-30')."
                    ),
                },
                {
                    "name": "grading_service",
                    "type": "select",
                    "label": "Grading Service",
                    "required": False,
                    "help_text": (
                        "The professional third-party service that certified the "
                        "coin's grade (e.g., PCGS, NGC, ANACS)."
                    ),
                    "choices": [
                        {
                            "value": "PCGS",
                            "label": "PCGS",
                        },
                        {
                            "value": "NGC",
                            "label": "NGC",
                        },
                        {
                            "value": "ANACS",
                            "label": "ANACS",
                        },
                        {
                            "value": "ICG",
                            "label": "ICG",
                        },
                        {
                            "value": "UNGRADED",
                            "label": "Ungraded / Raw",
                        },
                        {
                            "value": "OTHER",
                            "label": "Other",
                        },
                    ],
                },
            ],
        },
        "list_display_fields": [
            "country_of_origin",
            "denomination",
            "year_of_issue",
            "mint_mark",
            "metal_composition",
            "edge_type",
            "certified_grade",
            "grading_service",
        ],
        "ui_theme_file": "coin-collection.html",
    },
    {
        "slug": "wine-collection",
        "name": "Wine Collection",
        "icon": "fa-solid fa-wine-glass",
        "description": "This collection will catalog the contents of my cellar",
        "preview": (
            "Cellar book tracking format, appellation, bin location, and critic scores."
        ),
        "service_provider_key": "default",
        "is_system": False,
        "field_schema": {
            "fields": [
                {
                    "name": "bottle_format",
                    "type": "text",
                    "label": "Bottle Format",
                    "required": True,
                    "help_text": (
                        "Size of the bottle (e.g., standard 750ml, Magnum 1.5L, Half "
                        "Bottle 375ml)."
                    ),
                },
                {
                    "name": "closure_type",
                    "type": "text",
                    "label": "Closure Type",
                    "required": False,
                    "help_text": (
                        "Type of bottle closure (e.g., natural cork, synthetic cork, "
                        "screwcap, glass stopper)."
                    ),
                },
                {
                    "name": "appellation",
                    "type": "text",
                    "label": "Appellation",
                    "required": True,
                    "help_text": (
                        "Specific geographical wine-producing area or origin within a "
                        "region (e.g., Pauillac, Barolo, Rutherford AVA)."
                    ),
                },
                {
                    "name": "cellar_location",
                    "type": "text",
                    "label": "Cellar Location",
                    "required": False,
                    "help_text": (
                        "Specific physical location within your cellar (e.g., Rack "
                        "A-3, Bin 12, Offsite Storage Bay)."
                    ),
                },
                {
                    "name": "bottle_condition",
                    "type": "text",
                    "label": "Bottle Condition",
                    "required": False,
                    "help_text": (
                        "Overall condition of the bottle, including fill level (e.g., "
                        "High Shoulder, Base Neck), label integrity, and capsule "
                        "state."
                    ),
                },
                {
                    "name": "alcohol_content",
                    "type": "number",
                    "label": "Alcohol % (ABV)",
                    "required": False,
                    "help_text": (
                        "Percentage of alcohol by volume (ABV) as stated on the label."
                    ),
                },
                {
                    "name": "critic_score",
                    "type": "number",
                    "label": "Critic Score",
                    "required": False,
                    "help_text": (
                        "Numeric score from a recognized wine critic (e.g., 95 "
                        "points). Optionally include source in notes."
                    ),
                },
            ],
        },
        "list_display_fields": [
            "bottle_format",
            "closure_type",
            "appellation",
            "cellar_location",
            "bottle_condition",
            "alcohol_content",
            "critic_score",
        ],
    },
    {
        "slug": "hand-bags",
        "name": "Hand Bags",
        "icon": "fa-solid fa-bag-shopping",
        "description": "This is a collection of designer handbags",
        "preview": (
            "Designer handbag archive with materials, hardware, and authenticity codes."
        ),
        "service_provider_key": "default",
        "is_system": False,
        "field_schema": {
            "fields": [
                {
                    "name": "designer_brand",
                    "type": "text",
                    "label": "Designer Brand",
                    "required": True,
                    "help_text": (
                        "The brand or specific designer of the handbag (e.g., Hermès, "
                        "Chanel, Louis Vuitton)."
                    ),
                },
                {
                    "name": "model_style_name",
                    "type": "text",
                    "label": "Model/Style Name",
                    "required": True,
                    "help_text": (
                        "The specific model or style name of the handbag (e.g., Birkin"
                        " 30, Classic Flap, Lady Dior, Speedy 25)."
                    ),
                },
                {
                    "name": "material",
                    "type": "text",
                    "label": "Material",
                    "required": True,
                    "help_text": (
                        "The primary material of the handbag (e.g., Togo leather, "
                        "Caviar leather, Canvas, Crocodile, Lizard, Lambskin)."
                    ),
                },
                {
                    "name": "color",
                    "type": "text",
                    "label": "Color",
                    "required": True,
                    "help_text": (
                        "The specific color of the handbag, often with brand-specific "
                        "names (e.g., Black, Gold, Rose Sakura, Bleu Nuit)."
                    ),
                },
                {
                    "name": "hardware_finish",
                    "type": "text",
                    "label": "Hardware Finish",
                    "required": True,
                    "help_text": (
                        "The finish of the metal hardware on the handbag (e.g., Gold, "
                        "Palladium, Silver, Rose Gold, Ruthenium, Brushed Gold)."
                    ),
                },
                {
                    "name": "size_dimensions",
                    "type": "text",
                    "label": "Size/Dimensions",
                    "required": True,
                    "help_text": (
                        "The official size or approximate dimensions of the handbag "
                        "(e.g., Birkin 30, W25cm x H20cm x D13cm, Mini, MM)."
                    ),
                },
                {
                    "name": "production_year",
                    "type": "number",
                    "label": "Production Year",
                    "required": False,
                    "help_text": (
                        "The approximate year the handbag was produced or released as "
                        "part of a specific collection."
                    ),
                },
                {
                    "name": "authenticity_serial_number",
                    "type": "text",
                    "label": "Authenticity/Serial Number",
                    "required": False,
                    "help_text": (
                        "The unique serial number, date code, or authenticity code "
                        "found on the handbag (e.g., for Hermès, 'A' stamp for 2017; "
                        "for Chanel, 7-digit serial)."
                    ),
                },
            ],
        },
        "list_display_fields": [
            "designer_brand",
            "model_style_name",
            "material",
            "color",
            "hardware_finish",
            "size_dimensions",
            "production_year",
            "authenticity_serial_number",
        ],
    },
    {
        "slug": "football-cards",
        "name": "Football Cards",
        "icon": "fa-solid fa-football",
        "description": "Collectible sports cards, graded and catalogued.",
        "preview": "Graded sports card inventory with parallels and serial numbering.",
        "service_provider_key": "default",
        "is_system": False,
        "field_schema": {
            "fields": [
                {
                    "name": "set_year",
                    "type": "number",
                    "label": "Set Year",
                    "required": True,
                    "help_text": "The year the card set was released.",
                },
                {
                    "name": "manufacturer",
                    "type": "text",
                    "label": "Manufacturer",
                    "required": True,
                    "help_text": (
                        "The company that produced the card (e.g., Topps, Panini, "
                        "Upper Deck)."
                    ),
                },
                {
                    "name": "set_name",
                    "type": "text",
                    "label": "Set Name",
                    "required": True,
                    "help_text": (
                        "The specific name of the card set (e.g., Prizm, Chrome, "
                        "Donruss Optic)."
                    ),
                },
                {
                    "name": "card_number",
                    "type": "text",
                    "label": "Card Number",
                    "required": True,
                    "help_text": (
                        "The unique number or identifier assigned to the card within "
                        "its set, often alphanumeric."
                    ),
                },
                {
                    "name": "parallel_type",
                    "type": "text",
                    "label": "Parallel/Insert Type",
                    "required": False,
                    "help_text": (
                        "Description of the card's parallel or insert variation (e.g.,"
                        " Silver Prizm, Gold Refractor, Downtown)."
                    ),
                },
                {
                    "name": "serial_number",
                    "type": "text",
                    "label": "Serial Number",
                    "required": False,
                    "help_text": (
                        "The unique serial number for limited edition cards, typically"
                        " displayed as 'X/Y' (e.g., '15/99' or '1/1')."
                    ),
                },
                {
                    "name": "grading_company",
                    "type": "text",
                    "label": "Grading Company",
                    "required": False,
                    "help_text": (
                        "The professional grading service that authenticated and "
                        "graded the card (e.g., PSA, BGS, SGC)."
                    ),
                },
                {
                    "name": "grade",
                    "type": "text",
                    "label": "Grade",
                    "required": False,
                    "help_text": (
                        "The numerical grade assigned by the grading company, "
                        "including subgrades if applicable (e.g., 'PSA 10', 'BGS 9.5 "
                        "True Gem+', 'SGC 9')."
                    ),
                },
            ],
        },
        "list_display_fields": [
            "set_year",
            "manufacturer",
            "set_name",
            "card_number",
            "parallel_type",
            "serial_number",
            "grading_company",
            "grade",
        ],
    },
]

# Blueprints that are created and maintained by seed_system_collections.
SYSTEM_BLUEPRINTS: list[dict] = [
    bp for bp in COLLECTION_BLUEPRINTS if bp.get("is_system")
]

_BY_SLUG: dict[str, dict] = {bp["slug"]: bp for bp in COLLECTION_BLUEPRINTS}


def list_blueprints() -> list[dict]:
    """Return every blueprint in catalogue order (deep-copied, safe to mutate)."""
    return [deepcopy(bp) for bp in COLLECTION_BLUEPRINTS]


def get_blueprint(slug: str) -> dict | None:
    """Return the blueprint for *slug*, or None if it is not in the catalogue."""
    blueprint = _BY_SLUG.get(slug)
    return deepcopy(blueprint) if blueprint else None


def load_ui_theme(blueprint: dict) -> str:
    """
    Return the custom theme HTML for *blueprint*, or "" when it has none.

    Themes live as files under ``collection_themes/`` rather than inline strings
    so they stay diffable and syntax-highlighted.
    """
    filename = blueprint.get("ui_theme_file")
    if not filename:
        return ""
    path = THEME_DIR / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
