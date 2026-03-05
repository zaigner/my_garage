from django.urls import path
from . import views

app_name = "my_garage"

# Garage-specific URLs (vehicles)
# Collection URLs are now in collection_urls.py and mounted at /collections/
# Timepiece URLs are now in timepiece_urls.py and mounted at /timepieces/
urlpatterns = [
    # path("", views.garage_dashboard, name="dashboard"),  # Removed as it duplicates home
    path("", views.garage_view, name="garage_view"), # Default to carousel view
    path("view/", views.garage_view, name="garage_view_alias"), # Keep alias for compatibility
    path("add/", views.vehicle_add, name="vehicle_add"),
    path("<int:vehicle_id>/", views.vehicle_detail, name="vehicle_detail"),
    path("<int:vehicle_id>/refresh-valuation/", views.trigger_valuation_refresh, name="refresh_valuation"),
    path("<int:vehicle_id>/enrich-vin/", views.trigger_vin_enrichment, name="enrich_vin"),
    path("<int:vehicle_id>/upload-receipt/", views.upload_service_receipt, name="upload_receipt"),
    path("<int:vehicle_id>/add-service/", views.service_record_add, name="add_service_record"),
    path("<int:vehicle_id>/add-project/", views.upgrade_add, name="add_upgrade_project"),
    path("<int:vehicle_id>/projects/kanban/", views.vehicle_projects_kanban, name="vehicle_projects_kanban"),

    # Service Record CRUD
    path("service/<int:record_id>/edit/", views.service_record_edit, name="edit_service_record"),
    path("service/<int:record_id>/delete/", views.service_record_delete, name="delete_service_record"),
    path("service/<int:record_id>/ocr-debug/", views.view_ocr_debug, name="view_ocr_debug"),

    # Valuation History
    path("valuation/<int:history_id>/debug/", views.view_valuation_debug, name="view_valuation_debug"),

    # Global Search
    path("api/global-search/", views.global_search_view, name="global_search"),
]