from django.urls import path
from . import views

app_name = "my_garage"
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
]