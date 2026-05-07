"""URL Configuration for Dynamic Collections (mounted at /collections/)."""
from django.urls import path
from . import views

app_name = "collections"

urlpatterns = [
    # Dynamic Collections - Collection Type Management
    path("", views.collection_type_list, name="collection_type_list"),
    path("create/", views.collection_type_create, name="collection_type_create"),
    path("<slug:slug>/edit/", views.collection_type_edit, name="collection_type_edit"),
    
    # API for AI Schema Generation
    path("api/generate-schema/", views.generate_collection_schema, name="generate_collection_schema"),
    path("api/generate-ui/", views.generate_collection_ui, name="generate_collection_ui"),
    path("api/preview-ui/", views.preview_collection_ui, name="preview_collection_ui"),

    # Debug views
    path("debug/button-test/", views.button_test_view, name="button_test"),

    # Dynamic Collections - Collection Items
    path("<slug:collection_slug>/items/", views.collection_list, name="collection_list"),
    path("<slug:collection_slug>/items/add/", views.collection_item_add, name="collection_item_add"),
    path("<slug:collection_slug>/items/<int:item_id>/", views.collection_item_detail, name="collection_item_detail"),
    path("<slug:collection_slug>/items/<int:item_id>/delete/", views.collection_item_delete, name="collection_item_delete"),
    path("<slug:collection_slug>/items/<int:item_id>/refresh-valuation/", views.collection_item_trigger_valuation, name="collection_item_trigger_valuation"),
    path("<slug:collection_slug>/items/<int:item_id>/enrich/", views.collection_item_trigger_enrich, name="collection_item_trigger_enrich"),

    # Dynamic Collections - Service Records
    path("<slug:collection_slug>/items/<int:item_id>/ocr-receipt/", views.collection_item_ocr_receipt, name="collection_item_ocr_receipt"),
    path("<slug:collection_slug>/items/<int:item_id>/add-service/", views.collection_item_add_service, name="collection_item_add_service"),
    path("<slug:collection_slug>/items/<int:item_id>/service/<int:record_id>/edit/", views.collection_item_edit_service, name="collection_item_edit_service"),
    path("<slug:collection_slug>/items/<int:item_id>/service/<int:record_id>/delete/", views.collection_item_delete_service, name="collection_item_delete_service"),

    # Dynamic Collections - Upgrades/Projects
    path("<slug:collection_slug>/items/<int:item_id>/add-upgrade/", views.collection_item_add_upgrade, name="collection_item_add_upgrade"),
    path("<slug:collection_slug>/items/<int:item_id>/upgrade/<int:upgrade_id>/edit/", views.collection_item_edit_upgrade, name="collection_item_edit_upgrade"),
    path("<slug:collection_slug>/items/<int:item_id>/upgrade/<int:upgrade_id>/delete/", views.collection_item_delete_upgrade, name="collection_item_delete_upgrade"),
    path("<slug:collection_slug>/upgrades/kanban/", views.collection_upgrades_kanban, name="collection_upgrades_kanban"),

    # API endpoint for kanban status updates
    path("api/upgrade/<int:upgrade_id>/update-status/", views.collection_upgrade_update_status, name="upgrade_update_status"),

    # Dynamic Collections - Unified Views
    path("all-services/", views.all_services_view, name="all_services"),
    path("all-upgrades/", views.all_upgrades_view, name="all_upgrades"),
]
