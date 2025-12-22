from django.db.models import Sum, QuerySet, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from typing import Dict, Any

from .models import Vehicle, ServiceRecord, Upgrade, ConditionReport


def vehicle_get_total_maintenance_cost(vehicle: Vehicle) -> Decimal:
    """
    Calculates the sum of all verified service records.
    """
    return ServiceRecord.objects.filter(
        vehicle=vehicle,
        is_verified=True
    ).aggregate(
        total=Coalesce(Sum('total_cost'), Decimal('0.00'), output_field=DecimalField())
    )['total']


def vehicle_get_total_upgrade_cost(vehicle: Vehicle) -> Decimal:
    """
    Calculates the sum of all installed upgrades.
    """
    return Upgrade.objects.filter(
        vehicle=vehicle,
        status='INSTALLED'
    ).aggregate(
        total=Coalesce(Sum('cost'), Decimal('0.00'), output_field=DecimalField())
    )['total']


def vehicle_get_build_summary(vehicle_id: int) -> Dict[str, Any]:
    """
    Aggregates all financial and condition data for a specific vehicle dashboard.
    This is a primary 'Application Layer' selector.
    """
    vehicle = Vehicle.objects.get(pk=vehicle_id)

    maintenance = vehicle_get_total_maintenance_cost(vehicle)
    upgrades = vehicle_get_total_upgrade_cost(vehicle)
    total_investment = maintenance + upgrades + (vehicle.purchase_price or Decimal('0.00'))

    # Calculate Equity (Market Value - Total Investment)
    equity = vehicle.current_market_value - total_investment

    # Get latest condition grade
    latest_condition = ConditionReport.objects.filter(vehicle=vehicle).order_by('-created_at').first()

    return {
        "vehicle": vehicle,
        "maintenance_total": maintenance,
        "upgrade_total": upgrades,
        "total_investment": total_investment,
        "current_market_value": vehicle.current_market_value,
        "equity": equity,
        "latest_grade": latest_condition.grade if latest_condition else None,
        "is_profitable": equity > 0
    }


def vehicle_list_wishlist_items(vehicle: Vehicle) -> QuerySet[Upgrade]:
    """
    Returns all parts currently in the 'Wishlist' status.
    """
    return Upgrade.objects.filter(vehicle=vehicle, status='WISHLIST').order_by('part_name')


def vehicle_get_pending_service_count(vehicle: Vehicle) -> int:
    """
    Returns count of service records that haven't been verified by AI/User yet.
    """
    return ServiceRecord.objects.filter(vehicle=vehicle, is_verified=False).count()