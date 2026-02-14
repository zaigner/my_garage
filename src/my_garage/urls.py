from django.urls import path
from . import views

app_name = "my_garage"

# Garage-specific URLs (vehicles)
# Collection URLs are now in collection_urls.py and mounted at /collections/
# Timepiece URLs are now in timepiece_urls.py and mounted at /timepieces/
urlpatterns = [
    path("", views.garage_dashboard, name="dashboard"),
    path("view/", views.garage_view, name="garage_view"),
    path("add/", views.vehicle_add, name="vehicle_add"),
    path("<int:vehicle_id>/", views.vehicle_detail, name="vehicle_detail"),
    path("<int:vehicle_id>/refresh-valuation/", views.trigger_valuation_refresh, name="refresh_valuation"),
    path("<int:vehicle_id>/enrich-vin/", views.trigger_vin_enrichment, name="enrich_vin"),
    path("<int:vehicle_id>/upload-receipt/", views.upload_service_receipt, name="upload_receipt"),
    path("<int:vehicle_id>/add-service/", views.add_service_record, name="add_service_record"),
    path("<int:vehicle_id>/add-project/", views.add_upgrade_project, name="add_upgrade_project"),
    path("<int:vehicle_id>/projects/kanban/", views.vehicle_projects_kanban, name="vehicle_projects_kanban"),

    # Service Record CRUD
    path("service/<int:record_id>/edit/", views.edit_service_record, name="edit_service_record"),
    path("service/<int:record_id>/delete/", views.delete_service_record, name="delete_service_record"),
    path("service/<int:record_id>/ocr-debug/", views.view_ocr_debug, name="view_ocr_debug"),

    # Valuation History
    path("valuation/<int:history_id>/debug/", views.view_valuation_debug, name="view_valuation_debug"),
]