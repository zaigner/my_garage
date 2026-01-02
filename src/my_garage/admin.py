"""Django admin configuration for my_garage."""
from django.contrib import admin
from my_garage.models import Vehicle, ServiceRecord, Upgrade, ConditionReport


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    """Admin for Vehicle model."""

    list_display = ['__str__', 'owner', 'year', 'mileage', 'current_market_value', 'created_at']
    list_filter = ['make', 'year', 'owner']
    search_fields = ['make', 'model', 'vin', 'owner__username']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Vehicle Information', {
            'fields': ('owner', 'make', 'model', 'year', 'trim', 'vin')
        }),
        ('Financial', {
            'fields': ('purchase_price', 'current_market_value')
        }),
        ('Metadata', {
            'fields': ('mileage', 'created_at')
        }),
    )


@admin.register(ServiceRecord)
class ServiceRecordAdmin(admin.ModelAdmin):
    """Admin for ServiceRecord model."""

    list_display = ['vehicle', 'date', 'vendor', 'category', 'total_cost', 'is_verified']
    list_filter = ['category', 'is_verified', 'date']
    search_fields = ['vehicle__make', 'vehicle__model', 'vendor', 'description']
    readonly_fields = ['ocr_raw_data']
    date_hierarchy = 'date'

    fieldsets = (
        ('Service Information', {
            'fields': ('vehicle', 'date', 'vendor', 'category', 'description')
        }),
        ('Financial', {
            'fields': ('total_cost',)
        }),
        ('Document', {
            'fields': ('receipt_image', 'ocr_raw_data', 'is_verified')
        }),
    )


@admin.register(Upgrade)
class UpgradeAdmin(admin.ModelAdmin):
    """Admin for Upgrade model."""

    list_display = ['vehicle', 'part_name', 'brand', 'status', 'cost', 'installation_date']
    list_filter = ['status', 'brand']
    search_fields = ['vehicle__make', 'vehicle__model', 'part_name', 'brand', 'part_number']
    date_hierarchy = 'installation_date'

    fieldsets = (
        ('Part Information', {
            'fields': ('vehicle', 'part_name', 'brand', 'part_number')
        }),
        ('Status & Cost', {
            'fields': ('status', 'cost', 'installation_date')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )


@admin.register(ConditionReport)
class ConditionReportAdmin(admin.ModelAdmin):
    """Admin for ConditionReport model."""

    list_display = ['vehicle', 'area', 'grade', 'value_adjustment', 'created_at']
    list_filter = ['area', 'created_at']
    search_fields = ['vehicle__make', 'vehicle__model', 'ai_feedback']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Report Information', {
            'fields': ('vehicle', 'area', 'photo')
        }),
        ('Assessment', {
            'fields': ('grade', 'ai_feedback', 'value_adjustment')
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )
