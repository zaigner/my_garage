"""DRF ViewSets for my_garage API."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from my_garage.models import Vehicle, ServiceRecord, Upgrade, ConditionReport
from .serializers import (
    VehicleSerializer,
    ServiceRecordSerializer,
    UpgradeSerializer,
    ConditionReportSerializer,
)
from .services import vehicle_update_market_valuation
from .selectors import vehicle_get_build_summary
from ..tasks import task_update_market_valuation


class VehicleViewSet(viewsets.ModelViewSet):
    """ViewSet for Vehicle CRUD operations."""

    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['make', 'model', 'year', 'owner']
    ordering_fields = '__all__'
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter to show only user's own vehicles."""
        return self.queryset.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """Set owner to current user on creation."""
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def refresh_valuation(self, request, pk=None):
        """Refresh market valuation for a vehicle."""
        vehicle = self.get_object()
        try:
            # Trigger background task
            task_update_market_valuation.delay(vehicle.id)
            return Response({
                'message': 'Valuation update queued successfully'
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def build_summary(self, request, pk=None):
        """Get comprehensive build summary."""
        vehicle = self.get_object()
        summary = vehicle_get_build_summary(vehicle.id)
        # Convert Decimal to string for JSON
        summary_json = {k: str(v) if isinstance(v, type(summary['equity'])) else v
                       for k, v in summary.items() if k != 'vehicle'}
        return Response(summary_json)


class ServiceRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for ServiceRecord CRUD operations."""

    queryset = ServiceRecord.objects.all()
    serializer_class = ServiceRecordSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['vehicle', 'category', 'is_verified']
    ordering = ['-date']

    def get_queryset(self):
        """Filter to show only records for user's vehicles."""
        return self.queryset.filter(vehicle__owner=self.request.user)


class UpgradeViewSet(viewsets.ModelViewSet):
    """ViewSet for Upgrade CRUD operations."""

    queryset = Upgrade.objects.all()
    serializer_class = UpgradeSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['vehicle', 'status']
    ordering = ['-installation_date']

    def get_queryset(self):
        """Filter to show only upgrades for user's vehicles."""
        return self.queryset.filter(vehicle__owner=self.request.user)


class ConditionReportViewSet(viewsets.ModelViewSet):
    """ViewSet for ConditionReport CRUD operations."""

    queryset = ConditionReport.objects.all()
    serializer_class = ConditionReportSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['vehicle', 'area']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter to show only reports for user's vehicles."""
        return self.queryset.filter(vehicle__owner=self.request.user)
