"""API Router configuration."""
from rest_framework.routers import DefaultRouter, SimpleRouter
from django.conf import settings

from my_garage.api.views import (
    VehicleViewSet,
    ServiceRecordViewSet,
    UpgradeViewSet,
    ConditionReportViewSet,
)

# Use DefaultRouter for development (browsable API), SimpleRouter for production
router = DefaultRouter() if settings.DEBUG else SimpleRouter()

# Register ViewSets
router.register("vehicles", VehicleViewSet)
router.register("service-records", ServiceRecordViewSet)
router.register("upgrades", UpgradeViewSet)
router.register("condition-reports", ConditionReportViewSet)

urlpatterns = router.urls
