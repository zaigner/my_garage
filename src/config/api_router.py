"""API Router configuration."""
from rest_framework.routers import DefaultRouter, SimpleRouter
from django.conf import settings

from my_garage.api.views import (
    CollectionTypeViewSet,
    DynamicCollectionItemViewSet,
    GenericServiceRecordViewSet,
    GenericValuationHistoryViewSet,
    GenericUpgradeViewSet,
)

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("collection-types", CollectionTypeViewSet, basename="collectiontype")
router.register("items", DynamicCollectionItemViewSet, basename="collectionitem")
router.register("service-records", GenericServiceRecordViewSet, basename="servicerecord")
router.register("valuation-history", GenericValuationHistoryViewSet, basename="valuationhistory")
router.register("upgrades", GenericUpgradeViewSet, basename="upgrade")

urlpatterns = router.urls
