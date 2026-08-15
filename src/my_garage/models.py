from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.text import slugify


class CollectionType(models.Model):
    """
    Defines a user-created collection type (e.g., Wine, Art, Bikes).
    Stores the schema (field definitions) and display preferences.
    """

    # Basic Info
    name = models.CharField(
        max_length=100, help_text="e.g., Wine Collection, Art Collection"
    )
    # Unique per owner, not globally — see Meta.unique_together.  Every user gets
    # their own "automobiles" slug so per-user collections share stable URLs.
    slug = models.SlugField(max_length=100, blank=True)
    icon = models.CharField(
        max_length=50,
        default="fa-solid fa-box",
        help_text="FontAwesome icon class (FA6 needs a style prefix, e.g. 'fa-solid fa-car')",  # noqa: E501
    )
    description = models.TextField(blank=True)

    # Owner
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collection_types",
    )

    # Schema Definition
    field_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Define custom fields as JSON:
        {
          "fields": [
            {
              "name": "vintage",
              "type": "number",
              "label": "Vintage Year",
              "required": true,
              "help_text": "Year the wine was produced"
            },
            {
              "name": "region",
              "type": "text",
              "label": "Region",
              "required": false
            }
          ]
        }
        Supported types: text, number, date, file, relationship
        """,
    )

    # Display Configuration
    list_display_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="List of field names to display in list view, e.g., ['vintage', 'region']",  # noqa: E501
    )

    # UI Customization
    ui_theme_html = models.TextField(
        blank=True, help_text="Custom UI component HTML for this collection"
    )

    # Service Provider — drives specialised enrichment/valuation behaviour
    SERVICE_PROVIDER_CHOICES = [
        ("default", "Default"),
        ("vehicle", "Automobile"),
        ("timepiece", "Timepiece / Horology"),
    ]
    service_provider_key = models.CharField(
        max_length=50,
        choices=SERVICE_PROVIDER_CHOICES,
        default="default",
        help_text="Pluggable service provider for enrichment and valuation",
    )

    # System flag — prevents deletion/rename through the UI
    is_system = models.BooleanField(
        default=False,
        help_text="System-managed collection; not editable or deletable by users",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        unique_together = [["owner", "slug"]]

    def __str__(self):
        return f"{self.name} ({self.owner.username})"

    def save(self, *args, **kwargs):
        # Auto-generate slug from name if not provided
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            # Ensure uniqueness for this owner
            while CollectionType.objects.filter(owner=self.owner, slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class DynamicCollectionItem(models.Model):
    """
    Represents an item in a user-defined collection.
    Common fields are in the model, custom fields are in the JSONField.
    """

    # Link to collection type
    collection_type = models.ForeignKey(
        CollectionType, on_delete=models.CASCADE, related_name="items"
    )

    # Core Identity
    name = models.CharField(
        max_length=200, help_text="Primary identifier for this item"
    )

    # Financial Tracking (common to all collections)
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="What you paid for it",
    )
    purchase_date = models.DateField(null=True, blank=True)
    current_market_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current estimated value",
    )

    # NFP fields: cached, refreshed by signals on item/service-record/upgrade saves
    total_cost_basis = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cached cost basis: purchase price + services + completed upgrades",
    )
    net_financial_position = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cached NFP: market value minus all-in cost basis",
    )

    # Visual & Notes
    photo = models.ImageField(
        upload_to="collections/%Y/%m/",
        null=True,
        blank=True,
        help_text="Main photo of the item",
    )
    notes = models.TextField(blank=True)

    # Owner
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collection_items",
    )

    # Dynamic Fields (collection-specific attributes)
    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Collection-specific fields defined in CollectionType schema",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["collection_type", "owner"]),
            models.Index(fields=["owner", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.collection_type.name})"

    @property
    def equity(self):
        """Calculate equity (current value - purchase price)"""
        if self.current_market_value and self.purchase_price:
            return self.current_market_value - self.purchase_price
        return None

    def get_field_value(self, field_name):
        """Helper to get custom field value"""
        return self.custom_fields.get(field_name)

    def set_field_value(self, field_name, value):
        """Helper to set custom field value"""
        self.custom_fields[field_name] = value

    def get_display_name(self):
        """Get a display-friendly name for this item"""
        return self.name


class GenericValuationHistory(models.Model):
    """
    Immutable audit trail of market valuations for any DynamicCollectionItem.
    Replaces the Vehicle-specific ValuationHistory for the unified collections model.
    """

    item = models.ForeignKey(
        DynamicCollectionItem,
        on_delete=models.CASCADE,
        related_name="valuation_history",
    )
    date = models.DateTimeField(auto_now_add=True)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    raw_data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.item.name} valued at {self.value} on {self.date.date()}"


class GenericServiceRecord(models.Model):
    """
    Generic service/maintenance record that works with ANY collection item.
    Similar to ServiceRecord but not tied to Vehicle.
    """

    CATEGORY_CHOICES = [
        ("MAINTENANCE", "Maintenance"),
        ("REPAIR", "Repair"),
        ("UPGRADE", "Upgrade"),
        ("RESTORATION", "Restoration"),
        ("APPRAISAL", "Appraisal"),
        ("OTHER", "Other"),
    ]

    # Link to any collection item
    item = models.ForeignKey(
        DynamicCollectionItem, on_delete=models.CASCADE, related_name="service_records"
    )

    # Service Details
    date = models.DateField()
    vendor = models.CharField(max_length=255, help_text="Who performed the service")
    description = models.TextField()
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="MAINTENANCE"
    )

    # Financial
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)

    # Document Digitization
    receipt_image = models.ImageField(
        upload_to="service_receipts/%Y/%m/", null=True, blank=True
    )
    ocr_raw_data = models.JSONField(
        null=True, blank=True, help_text="OCR extracted data from receipt"
    )

    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["item", "-date"]),
        ]

    def __str__(self):
        return f"{self.item.name} - {self.category} on {self.date}"


class GenericUpgrade(models.Model):
    """
    Generic upgrade/modification tracking for any collection item.
    Similar to Upgrade but not tied to Vehicle.
    """

    STATUS_CHOICES = [
        ("WISHLIST", "Wishlist"),
        ("ORDERED", "Ordered"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    # Link to any collection item (Legacy/Specific)
    item = models.ForeignKey(
        DynamicCollectionItem,
        on_delete=models.CASCADE,
        related_name="upgrades",
        null=True,
        blank=True,
    )

    # Generic Relation (New System)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    # Upgrade Details
    name = models.CharField(
        max_length=255, help_text="Name of the upgrade/modification"
    )
    brand = models.CharField(max_length=100, blank=True)
    part_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="WISHLIST")

    # Financial
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Dates
    ordered_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-completion_date", "-ordered_date"]

    def __str__(self):
        if self.content_object:
            return f"{self.content_object} - {self.name} ({self.status})"
        elif self.item:
            return f"{self.item.name} - {self.name} ({self.status})"
        return f"Unknown Item - {self.name} ({self.status})"


class CollectionItemAttachment(models.Model):
    """
    File attachments for collection items (receipts, certificates, documentation).
    """

    ATTACHMENT_TYPES = [
        ("RECEIPT", "Receipt"),
        ("CERTIFICATE", "Certificate of Authenticity"),
        ("APPRAISAL", "Appraisal Document"),
        ("MANUAL", "Manual/Documentation"),
        ("PHOTO", "Additional Photo"),
        ("OTHER", "Other"),
    ]

    # Link to any collection item
    item = models.ForeignKey(
        DynamicCollectionItem, on_delete=models.CASCADE, related_name="attachments"
    )

    # File Details
    file = models.FileField(upload_to="collection_attachments/%Y/%m/")
    file_type = models.CharField(
        max_length=20, choices=ATTACHMENT_TYPES, default="OTHER"
    )
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.item.name} - {self.file_type}"


class CollectionItemRelationship(models.Model):
    """
    Defines relationships between collection items.
    E.g., a watch can be related to a vehicle, artwork to a timepiece, etc.
    """

    RELATIONSHIP_TYPES = [
        ("PAIRED_WITH", "Paired With"),
        ("PART_OF", "Part Of"),
        ("INSPIRED_BY", "Inspired By"),
        ("RELATED_TO", "Related To"),
        ("CUSTOM", "Custom"),
    ]

    # From and To items
    from_item = models.ForeignKey(
        DynamicCollectionItem,
        on_delete=models.CASCADE,
        related_name="relationships_from",
    )
    to_item = models.ForeignKey(
        DynamicCollectionItem, on_delete=models.CASCADE, related_name="relationships_to"
    )

    # Relationship Details
    relationship_type = models.CharField(
        max_length=20, choices=RELATIONSHIP_TYPES, default="RELATED_TO"
    )
    custom_label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Custom label if relationship_type is CUSTOM",
    )
    notes = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        unique_together = [["from_item", "to_item", "relationship_type"]]

    def __str__(self):
        label = (
            self.custom_label
            if self.relationship_type == "CUSTOM"
            else self.get_relationship_type_display()
        )
        return f"{self.from_item.name} {label} {self.to_item.name}"


# ── Estate & Legacy ───────────────────────────────────────────────────────────


class Beneficiary(models.Model):
    RELATIONSHIP_CHOICES = [
        ("Spouse", "Spouse"),
        ("Child", "Child"),
        ("Sibling", "Sibling"),
        ("Parent", "Parent"),
        ("Friend", "Friend"),
        ("Charity", "Charity"),
        ("Other", "Other"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="beneficiaries",
    )
    name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=50, choices=RELATIONSHIP_CHOICES)
    contact_info = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.relationship})"


class EstateExecutor(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="estate_executor",
    )
    name = models.CharField(max_length=200)
    contact_info = models.TextField(blank=True)
    designated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Executor for {self.owner.username}: {self.name}"


class BeneficiaryAssignment(models.Model):
    item = models.OneToOneField(
        "DynamicCollectionItem",
        on_delete=models.CASCADE,
        related_name="estate_assignment",
    )
    beneficiary = models.ForeignKey(
        Beneficiary,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments",
    )
    conditional_note = models.TextField(blank=True)
    is_charitable = models.BooleanField(default=False)
    charitable_org = models.CharField(max_length=200, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.is_charitable:
            return f"{self.item.name} → {self.charitable_org} (charitable)"
        if self.beneficiary:
            return f"{self.item.name} → {self.beneficiary.name}"
        return f"{self.item.name} → Unassigned"


class EstateChangeLog(models.Model):
    ACTION_CHOICES = [
        ("ASSIGNED", "Assigned"),
        ("CHANGED", "Changed"),
        ("REMOVED", "Removed"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="estate_change_logs",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    item_name = models.CharField(max_length=200)
    beneficiary_name = models.CharField(max_length=200, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d} {self.action} — {self.item_name}"


class EstateAccessToken(models.Model):
    # ForeignKey (not OneToOneField) allows keeping deactivated tokens as audit trail.
    # Service enforces: only one is_active=True per owner at any time.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="estate_access_tokens",
    )
    token_hash = models.CharField(max_length=64)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    use_count = models.IntegerField(default=0)

    def __str__(self):
        return f"EstateAccessToken for {self.owner.username} (active={self.is_active})"


class ValuationSnapshot(models.Model):
    TRIGGER_CHOICES = [
        ("ESTATE_ACTIVATION", "Estate Activation"),
        ("MANUAL", "Manual"),
    ]

    item = models.ForeignKey(
        "DynamicCollectionItem",
        on_delete=models.CASCADE,
        related_name="valuation_snapshots",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="valuation_snapshots",
    )
    snapshot_date = models.DateField()
    market_value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    cost_basis = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    equity = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    snapshot_trigger = models.CharField(max_length=30, choices=TRIGGER_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Snapshot {self.snapshot_date} — {self.item.name}"


class PortfolioSnapshot(models.Model):
    """
    Daily total portfolio value per user. One row per (user, date).
    Used to compute year-over-year % change on the dashboard.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio_snapshots",
    )
    date = models.DateField()
    total_value = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        unique_together = [["user", "date"]]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.username} portfolio on {self.date}: {self.total_value}"
