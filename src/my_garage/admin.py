"""Django admin configuration for my_garage."""
from django.contrib import admin
from my_garage.models import (
    Vehicle, ServiceRecord, Upgrade, ConditionReport,
    CollectionType, DynamicCollectionItem, GenericServiceRecord,
    GenericUpgrade, CollectionItemAttachment, CollectionItemRelationship
)


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


# ============================================================================
# DYNAMIC COLLECTION SYSTEM ADMIN
# ============================================================================

@admin.register(CollectionType)
class CollectionTypeAdmin(admin.ModelAdmin):
    """Admin for CollectionType model."""

    list_display = ['name', 'slug', 'owner', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at', 'owner']
    search_fields = ['name', 'description', 'owner__username']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'icon', 'description', 'owner', 'is_active')
        }),
        ('Schema Definition', {
            'fields': ('field_schema', 'list_display_fields'),
            'description': 'Define custom fields in JSON format. See model help text for examples.'
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(DynamicCollectionItem)
class DynamicCollectionItemAdmin(admin.ModelAdmin):
    """Admin for DynamicCollectionItem model."""

    list_display = ['name', 'collection_type', 'owner', 'purchase_price', 'current_market_value', 'created_at']
    list_filter = ['collection_type', 'owner', 'created_at']
    search_fields = ['name', 'notes', 'owner__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'collection_type', 'owner', 'photo')
        }),
        ('Financial Information', {
            'fields': ('purchase_price', 'purchase_date', 'current_market_value')
        }),
        ('Custom Fields', {
            'fields': ('custom_fields',),
            'description': 'Collection-specific attributes defined in CollectionType schema'
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(GenericServiceRecord)
class GenericServiceRecordAdmin(admin.ModelAdmin):
    """Admin for GenericServiceRecord model."""

    list_display = ['item', 'date', 'vendor', 'category', 'total_cost', 'is_verified']
    list_filter = ['category', 'is_verified', 'date']
    search_fields = ['item__name', 'vendor', 'description']
    readonly_fields = ['ocr_raw_data']
    date_hierarchy = 'date'

    fieldsets = (
        ('Service Information', {
            'fields': ('item', 'date', 'vendor', 'category', 'description')
        }),
        ('Financial', {
            'fields': ('total_cost',)
        }),
        ('Document', {
            'fields': ('receipt_image', 'ocr_raw_data', 'is_verified')
        }),
    )


@admin.register(GenericUpgrade)
class GenericUpgradeAdmin(admin.ModelAdmin):
    """Admin for GenericUpgrade model."""

    list_display = ['item', 'name', 'brand', 'status', 'cost', 'completion_date']
    list_filter = ['status', 'brand']
    search_fields = ['item__name', 'name', 'brand', 'part_number']
    date_hierarchy = 'completion_date'

    fieldsets = (
        ('Upgrade Information', {
            'fields': ('item', 'name', 'brand', 'part_number')
        }),
        ('Status & Dates', {
            'fields': ('status', 'ordered_date', 'completion_date')
        }),
        ('Financial', {
            'fields': ('cost',)
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )


@admin.register(CollectionItemAttachment)
class CollectionItemAttachmentAdmin(admin.ModelAdmin):
    """Admin for CollectionItemAttachment model."""

    list_display = ['item', 'file_type', 'title', 'uploaded_at', 'uploaded_by']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['item__name', 'title', 'description']
    readonly_fields = ['uploaded_at']
    date_hierarchy = 'uploaded_at'

    fieldsets = (
        ('Attachment Information', {
            'fields': ('item', 'file', 'file_type', 'title', 'description')
        }),
        ('Metadata', {
            'fields': ('uploaded_at', 'uploaded_by')
        }),
    )


@admin.register(CollectionItemRelationship)
class CollectionItemRelationshipAdmin(admin.ModelAdmin):
    """Admin for CollectionItemRelationship model."""

    list_display = ['from_item', 'relationship_type', 'to_item', 'created_at', 'created_by']
    list_filter = ['relationship_type', 'created_at']
    search_fields = ['from_item__name', 'to_item__name', 'notes']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Relationship', {
            'fields': ('from_item', 'relationship_type', 'to_item', 'custom_label')
        }),
        ('Details', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by')
        }),
    )
