"""Legacy garage URL patterns (Phase 5).

The list route (/garage/) is redirected in config/urls.py.
The only routes that remain here are:
  - /garage/<id>/  → smart redirect to the migrated DynamicCollectionItem
  - /garage/api/global-search/  → AJAX search endpoint (used by base.html)
"""
from django.urls import path
from . import views

app_name = "my_garage"

urlpatterns = [
    # Smart permalink redirect for migrated vehicles
    path("<int:vehicle_id>/", views.legacy_vehicle_detail_redirect, name="vehicle_detail"),

    # Global Search (AJAX — still referenced by base.html JS)
    path("api/global-search/", views.global_search_view, name="global_search"),
]
