from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


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

    def __str__(self):
        return f"{self.brand} {self.model} ({self.reference_number})"
