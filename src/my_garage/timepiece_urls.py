"""Legacy timepiece URL patterns (Phase 5).

The list route (/timepieces/) is redirected in config/urls.py.
The only route that remains here is the smart permalink redirect.
"""

from django.urls import path

from . import views

app_name = "timepieces"

urlpatterns = [
    # Smart permalink redirect for migrated timepieces
    path(
        "<int:timepiece_id>/",
        views.legacy_timepiece_detail_redirect,
        name="timepiece_detail",
    ),
]
