"""Main URL Configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API
    path('api/', include('config.api_router')),

    # Timepieces (moved out of garage)
    path('timepieces/', include('my_garage.timepiece_urls', namespace='timepieces')),

    # My Garage App (Vehicles)
    path('garage/', include('my_garage.urls', namespace='my_garage')),

    # Dynamic Collections (separate mount point, shares 'my_garage' namespace)
    path('collections/', include('my_garage.collection_urls')),

    # Home
    path('', views.home, name='home'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
