"""Main URL Configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Authentication
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/register/", views.register, name="register"),
    # API
    path("api/", include("config.api_router")),
    # ── Phase 4 redirects ─────────────────────────────────────────────────────
    # /garage/ list → consolidated automobiles collection
    # /timepieces/ list → consolidated horology-salon collection
    # Sub-routes (e.g. /garage/42/) are still served by the includes below.
    path(
        "garage/",
        RedirectView.as_view(url="/collections/automobiles/items/", permanent=False),
        name="garage_redirect",
    ),
    path(
        "timepieces/",
        RedirectView.as_view(url="/collections/horology-salon/items/", permanent=False),
        name="timepieces_redirect",
    ),
    # ─────────────────────────────────────────────────────────────────────────
    # Timepieces detail/add/winder routes (sub-paths only — list is redirected above)
    path("timepieces/", include("my_garage.timepiece_urls", namespace="timepieces")),
    # Vehicle detail/add/service routes (sub-paths only — list is redirected above)
    path("garage/", include("my_garage.urls", namespace="my_garage")),
    # Dynamic Collections (separate mount point)
    path("collections/", include("my_garage.collection_urls")),
    # Home
    path("", views.home, name="home"),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
