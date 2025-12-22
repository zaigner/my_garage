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

    # Financials
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    current_market_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # Metadata
    mileage = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.year} {self.make} {self.model}"


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