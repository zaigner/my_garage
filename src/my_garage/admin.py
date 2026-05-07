"""Django admin configuration for my_garage."""

from django.contrib import admin

from my_garage.models import (
    CollectionItemAttachment,
    CollectionItemRelationship,
    CollectionType,
    DynamicCollectionItem,
    GenericServiceRecord,
    GenericUpgrade,
    GenericValuationHistory,
)


@admin.register(CollectionType)
class CollectionTypeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "owner",
        "service_provider_key",
        "is_system",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "is_system", "service_provider_key", "owner"]
    search_fields = ["name", "description", "owner__username"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "slug",
                    "icon",
                    "description",
                    "owner",
                    "is_active",
                    "is_system",
                    "service_provider_key",
                )
            },
        ),
        (
            "Schema Definition",
            {
                "fields": ("field_schema", "list_display_fields"),
            },
        ),
        ("Metadata", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(DynamicCollectionItem)
class DynamicCollectionItemAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "collection_type",
        "owner",
        "purchase_price",
        "current_market_value",
        "created_at",
    ]
    list_filter = ["collection_type", "owner", "created_at"]
    search_fields = ["name", "notes", "owner__username"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "collection_type", "owner", "photo")},
        ),
        (
            "Financial Information",
            {"fields": ("purchase_price", "purchase_date", "current_market_value")},
        ),
        (
            "Custom Fields",
            {
                "fields": ("custom_fields",),
            },
        ),
        ("Notes", {"fields": ("notes",)}),
        ("Metadata", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(GenericServiceRecord)
class GenericServiceRecordAdmin(admin.ModelAdmin):
    list_display = ["item", "date", "vendor", "category", "total_cost", "is_verified"]
    list_filter = ["category", "is_verified", "date"]
    search_fields = ["item__name", "vendor", "description"]
    readonly_fields = ["ocr_raw_data"]
    date_hierarchy = "date"

    fieldsets = (
        (
            "Service Information",
            {"fields": ("item", "date", "vendor", "category", "description")},
        ),
        ("Financial", {"fields": ("total_cost",)}),
        ("Document", {"fields": ("receipt_image", "ocr_raw_data", "is_verified")}),
    )


@admin.register(GenericValuationHistory)
class GenericValuationHistoryAdmin(admin.ModelAdmin):
    list_display = ["item", "date", "value"]
    list_filter = ["date"]
    search_fields = ["item__name"]
    readonly_fields = ["date"]
    date_hierarchy = "date"


@admin.register(GenericUpgrade)
class GenericUpgradeAdmin(admin.ModelAdmin):
    list_display = [
        "content_object",
        "name",
        "brand",
        "status",
        "cost",
        "completion_date",
    ]
    list_filter = ["status", "brand"]
    search_fields = ["name", "brand", "part_number"]
    date_hierarchy = "completion_date"

    fieldsets = (
        (
            "Upgrade Information",
            {"fields": ("content_type", "object_id", "name", "brand", "part_number")},
        ),
        ("Status & Dates", {"fields": ("status", "ordered_date", "completion_date")}),
        ("Financial", {"fields": ("cost",)}),
        ("Notes", {"fields": ("notes",)}),
    )


@admin.register(CollectionItemAttachment)
class CollectionItemAttachmentAdmin(admin.ModelAdmin):
    list_display = ["item", "file_type", "title", "uploaded_at", "uploaded_by"]
    list_filter = ["file_type", "uploaded_at"]
    search_fields = ["item__name", "title", "description"]
    readonly_fields = ["uploaded_at"]
    date_hierarchy = "uploaded_at"

    fieldsets = (
        (
            "Attachment Information",
            {"fields": ("item", "file", "file_type", "title", "description")},
        ),
        ("Metadata", {"fields": ("uploaded_at", "uploaded_by")}),
    )


@admin.register(CollectionItemRelationship)
class CollectionItemRelationshipAdmin(admin.ModelAdmin):
    list_display = [
        "from_item",
        "relationship_type",
        "to_item",
        "created_at",
        "created_by",
    ]
    list_filter = ["relationship_type", "created_at"]
    search_fields = ["from_item__name", "to_item__name", "notes"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Relationship",
            {"fields": ("from_item", "relationship_type", "to_item", "custom_label")},
        ),
        ("Details", {"fields": ("notes",)}),
        ("Metadata", {"fields": ("created_at", "created_by")}),
    )
