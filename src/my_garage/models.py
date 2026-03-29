from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType


class Vehicle(models.Model):
    """The core asset: represents a user's car."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicles"
    )
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    year = models.PositiveIntegerField()
    trim = models.CharField(max_length=100, blank=True)
    vin = models.CharField(max_length=17, unique=True, blank=True, null=True)
    license_plate = models.CharField(max_length=20, blank=True)

    # Collector Specs
    transmission = models.CharField(max_length=50, blank=True, help_text="e.g. 6-Speed Manual, 8-Speed Auto")
    exterior_color = models.CharField(max_length=50, blank=True, help_text="Specific paint name/code")
    interior_color = models.CharField(max_length=50, blank=True)

    # Financials
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    current_market_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # Metadata
    mileage = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, help_text="Provenance, history, and other details.")
    
    # Enhanced Data (from VIN Decoder)
    features = models.JSONField(default=dict, blank=True)  # Stores features like "Leather Seats", "Sunroof"
    specs = models.JSONField(default=dict, blank=True)     # Stores technical specs like "Engine: V8", "HP: 400"
    photo = models.ImageField(upload_to="vehicles/%Y/%m/", null=True, blank=True) # Main vehicle photo

    # Generic Projects/Upgrades (New System)
    projects = GenericRelation('GenericUpgrade')

    def __str__(self):
        return f"{self.year} {self.make} {self.model}"


class ValuationHistory(models.Model):
    """Stores the history of market valuations for a vehicle."""
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="valuation_history")
    date = models.DateTimeField(auto_now_add=True)
    value = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Store the full raw response from the API for debugging/audit
    raw_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date']


class ServiceRecord(models.Model):
    """Stores service history and digitized documents."""
    CATEGORY_CHOICES = [
        ('MAINTENANCE', 'Maintenance'),
        ('REPAIR', 'Repair'),
        ('UPGRADE', 'Performance Upgrade'),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="services")
    date = models.DateField()
    vendor = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='MAINTENANCE')

    # Document Digitization
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    receipt_image = models.ImageField(upload_to="receipts/%Y/%m/", null=True, blank=True)
    ocr_raw_data = models.JSONField(null=True, blank=True)  # Data from FastAPI OCR

    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date']


class Upgrade(models.Model):
    """Project Manager: tracks ongoing and planned car modifications."""
    STATUS_CHOICES = [
        ('WISHLIST', 'Wishlist'),
        ('ORDERED', 'Ordered'),
        ('INSTALLED', 'Installed'),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="upgrades")
    part_name = models.CharField(max_length=255)
    brand = models.CharField(max_length=100, blank=True)
    part_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WISHLIST')

    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    installation_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)


class ConditionReport(models.Model):
    """Stores AI-graded assessments of the car's visual state."""
    AREA_CHOICES = [
        ('EXTERIOR', 'Exterior Paint/Body'),
        ('INTERIOR', 'Interior/Upholstery'),
        ('ENGINE', 'Engine Bay'),
        ('WHEELS', 'Wheels/Tires'),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="condition_reports")
    area = models.CharField(max_length=20, choices=AREA_CHOICES)
    photo = models.ImageField(upload_to="condition_checks/%Y/%m/")

    # Grading (1-10 Scale)
    grade = models.FloatField(validators=[MinValueValidator(1.0), MaxValueValidator(10.0)])
    ai_feedback = models.TextField()
    value_adjustment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)


class Timepiece(models.Model):
    """
    Represents a fine timepiece/watch asset.
    Designed for the 'Vacheron' aesthetic gallery.
    """
    MOVEMENT_CHOICES = [
        ('AUTOMATIC', 'Automatic'),
        ('MANUAL', 'Manual Wind'),
        ('QUARTZ', 'Quartz'),
        ('SPRING_DRIVE', 'Spring Drive'),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="timepieces"
    )
    
    # Core Identity
    brand = models.CharField(max_length=100, help_text="e.g. Patek Philippe, Rolex")
    model = models.CharField(max_length=100, help_text="e.g. Nautilus, Submariner")
    reference_number = models.CharField(max_length=100, help_text="Crucial for valuation (e.g. 5711/1A)")
    serial_number = models.CharField(max_length=100, blank=True, help_text="Private identifier")
    year = models.PositiveIntegerField(null=True, blank=True)
    
    # Horological Details
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_CHOICES, blank=True)
    case_material = models.CharField(max_length=50, blank=True, help_text="e.g. 18k Rose Gold, Stainless Steel")
    dial_color = models.CharField(max_length=50, blank=True)
    complications = models.JSONField(default=list, blank=True, help_text="List of features: Chronograph, Moonphase")
    
    # Asset Value Factors
    has_box = models.BooleanField(default=False)
    has_papers = models.BooleanField(default=False)
    condition_grade = models.CharField(max_length=20, blank=True, help_text="e.g. Unworn, Mint, Good")
    
    # Financials
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    current_market_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Visuals
    photo = models.ImageField(upload_to="timepieces/%Y/%m/", null=True, blank=True)
    notes = models.TextField(blank=True)

    # Generic Projects/Upgrades
    projects = GenericRelation('GenericUpgrade')

    def __str__(self):
        return f"{self.brand} {self.model} ({self.reference_number})"


# ============================================================================
# DYNAMIC COLLECTION SYSTEM
# ============================================================================

class CollectionType(models.Model):
    """
    Defines a user-created collection type (e.g., Wine, Art, Bikes).
    Stores the schema (field definitions) and display preferences.
    """
    # Basic Info
    name = models.CharField(max_length=100, help_text="e.g., Wine Collection, Art Collection")
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    icon = models.CharField(max_length=50, default="fa-box", help_text="FontAwesome icon class")
    description = models.TextField(blank=True)

    # Owner
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collection_types"
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
        """
    )

    # Display Configuration
    list_display_fields = models.JSONField(
        default=list,
        blank=True,
        help_text="List of field names to display in list view, e.g., ['vintage', 'region']"
    )
    
    # UI Customization
    ui_theme_html = models.TextField(
        blank=True,
        help_text="Custom UI component HTML for this collection"
    )

    # Service Provider — drives specialised enrichment/valuation behaviour
    SERVICE_PROVIDER_CHOICES = [
        ('default', 'Default'),
        ('vehicle', 'Automobile'),
        ('timepiece', 'Timepiece / Horology'),
    ]
    service_provider_key = models.CharField(
        max_length=50,
        choices=SERVICE_PROVIDER_CHOICES,
        default='default',
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
        ordering = ['name']
        unique_together = [['owner', 'slug']]

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
        CollectionType,
        on_delete=models.CASCADE,
        related_name="items"
    )

    # Core Identity
    name = models.CharField(max_length=200, help_text="Primary identifier for this item")

    # Financial Tracking (common to all collections)
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="What you paid for it"
    )
    purchase_date = models.DateField(null=True, blank=True)
    current_market_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current estimated value"
    )

    # Visual & Notes
    photo = models.ImageField(
        upload_to="collections/%Y/%m/",
        null=True,
        blank=True,
        help_text="Main photo of the item"
    )
    notes = models.TextField(blank=True)

    # Owner
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collection_items"
    )

    # Dynamic Fields (collection-specific attributes)
    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Collection-specific fields defined in CollectionType schema"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['collection_type', 'owner']),
            models.Index(fields=['owner', '-created_at']),
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
        ordering = ['-date']

    def __str__(self):
        return f"{self.item.name} valued at {self.value} on {self.date.date()}"


class GenericServiceRecord(models.Model):
    """
    Generic service/maintenance record that works with ANY collection item.
    Similar to ServiceRecord but not tied to Vehicle.
    """
    CATEGORY_CHOICES = [
        ('MAINTENANCE', 'Maintenance'),
        ('REPAIR', 'Repair'),
        ('UPGRADE', 'Upgrade'),
        ('RESTORATION', 'Restoration'),
        ('APPRAISAL', 'Appraisal'),
        ('OTHER', 'Other'),
    ]

    # Link to any collection item
    item = models.ForeignKey(
        DynamicCollectionItem,
        on_delete=models.CASCADE,
        related_name="service_records"
    )

    # Service Details
    date = models.DateField()
    vendor = models.CharField(max_length=255, help_text="Who performed the service")
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='MAINTENANCE')

    # Financial
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)

    # Document Digitization
    receipt_image = models.ImageField(
        upload_to="service_receipts/%Y/%m/",
        null=True,
        blank=True
    )
    ocr_raw_data = models.JSONField(
        null=True,
        blank=True,
        help_text="OCR extracted data from receipt"
    )

    is_verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['item', '-date']),
        ]

    def __str__(self):
        return f"{self.item.name} - {self.category} on {self.date}"


class GenericUpgrade(models.Model):
    """
    Generic upgrade/modification tracking for any collection item.
    Similar to Upgrade but not tied to Vehicle.
    """
    STATUS_CHOICES = [
        ('WISHLIST', 'Wishlist'),
        ('ORDERED', 'Ordered'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    # Link to any collection item (Legacy/Specific)
    item = models.ForeignKey(
        DynamicCollectionItem,
        on_delete=models.CASCADE,
        related_name="upgrades",
        null=True,
        blank=True
    )

    # Generic Relation (New System)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Upgrade Details
    name = models.CharField(max_length=255, help_text="Name of the upgrade/modification")
    brand = models.CharField(max_length=100, blank=True)
    part_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='WISHLIST')

    # Financial
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Dates
    ordered_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-completion_date', '-ordered_date']

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
        ('RECEIPT', 'Receipt'),
        ('CERTIFICATE', 'Certificate of Authenticity'),
        ('APPRAISAL', 'Appraisal Document'),
        ('MANUAL', 'Manual/Documentation'),
        ('PHOTO', 'Additional Photo'),
        ('OTHER', 'Other'),
    ]

    # Link to any collection item
    item = models.ForeignKey(
        DynamicCollectionItem,
        on_delete=models.CASCADE,
        related_name="attachments"
    )

    # File Details
    file = models.FileField(upload_to="collection_attachments/%Y/%m/")
    file_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES, default='OTHER')
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    # Metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.item.name} - {self.file_type}"


class CollectionItemRelationship(models.Model):
    """
    Defines relationships between collection items.
    E.g., a watch can be related to a vehicle, artwork to a timepiece, etc.
    """
    RELATIONSHIP_TYPES = [
        ('PAIRED_WITH', 'Paired With'),
        ('PART_OF', 'Part Of'),
        ('INSPIRED_BY', 'Inspired By'),
        ('RELATED_TO', 'Related To'),
        ('CUSTOM', 'Custom'),
    ]

    # From and To items
    from_item = models.ForeignKey(
        DynamicCollectionItem,
        on_delete=models.CASCADE,
        related_name="relationships_from"
    )
    to_item = models.ForeignKey(
        DynamicCollectionItem,
        on_delete=models.CASCADE,
        related_name="relationships_to"
    )

    # Relationship Details
    relationship_type = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_TYPES,
        default='RELATED_TO'
    )
    custom_label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Custom label if relationship_type is CUSTOM"
    )
    notes = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    class Meta:
        unique_together = [['from_item', 'to_item', 'relationship_type']]

    def __str__(self):
        label = self.custom_label if self.relationship_type == 'CUSTOM' else self.get_relationship_type_display()
        return f"{self.from_item.name} {label} {self.to_item.name}"
