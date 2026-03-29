"""DRF ViewSets for my_garage API."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    GenericServiceRecord,
    GenericValuationHistory,
    GenericUpgrade,
)
from .serializers import (
    CollectionTypeSerializer,
    DynamicCollectionItemSerializer,
    GenericServiceRecordSerializer,
    GenericValuationHistorySerializer,
    GenericUpgradeSerializer,
)
from ..tasks import task_collection_item_refresh_valuation, task_collection_item_enrich
from ..services.collection_services import get_collection_services


class CollectionTypeViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CollectionType.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class DynamicCollectionItemViewSet(viewsets.ModelViewSet):
    serializer_class = DynamicCollectionItemSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['collection_type']
    ordering = ['-created_at']

    def get_queryset(self):
        return DynamicCollectionItem.objects.filter(owner=self.request.user).select_related('collection_type')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def refresh_valuation(self, request, pk=None):
        item = self.get_object()
        provider = get_collection_services(item.collection_type.service_provider_key)
        if not provider.supports_valuation_refresh():
            return Response({'error': 'Valuation refresh not supported for this collection type.'},
                            status=status.HTTP_400_BAD_REQUEST)
        task_collection_item_refresh_valuation.delay(item.id)
        return Response({'message': 'Valuation refresh queued.'})

    @action(detail=True, methods=['post'])
    def enrich(self, request, pk=None):
        item = self.get_object()
        provider = get_collection_services(item.collection_type.service_provider_key)
        if not provider.supports_enrichment():
            return Response({'error': 'Enrichment not supported for this collection type.'},
                            status=status.HTTP_400_BAD_REQUEST)
        task_collection_item_enrich.delay(item.id)
        return Response({'message': 'Enrichment queued.'})


class GenericServiceRecordViewSet(viewsets.ModelViewSet):
    serializer_class = GenericServiceRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['item', 'category', 'is_verified']
    ordering = ['-date']

    def get_queryset(self):
        return GenericServiceRecord.objects.filter(item__owner=self.request.user)


class GenericValuationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GenericValuationHistorySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['item']
    ordering = ['-date']

    def get_queryset(self):
        return GenericValuationHistory.objects.filter(item__owner=self.request.user)


class GenericUpgradeViewSet(viewsets.ModelViewSet):
    serializer_class = GenericUpgradeSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status']
    ordering = ['-completion_date']

    def get_queryset(self):
        return GenericUpgrade.objects.filter(item__owner=self.request.user)
