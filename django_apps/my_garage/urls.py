from django.urls import path
from . import views

app_name = "my_garage"
urlpatterns = [
    path("", views.garage_dashboard, name="dashboard"),
    path("<int:vehicle_id>/", views.vehicle_detail, name="vehicle_detail"),
    path("<int:vehicle_id>/refresh-valuation/", views.trigger_valuation_refresh, name="refresh_valuation"),
    path("<int:vehicle_id>/upload-receipt/", views.upload_service_receipt, name="upload_receipt"),
]