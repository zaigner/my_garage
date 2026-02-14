from django.db.models import Sum, QuerySet, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from typing import Dict, Any
from bson import ObjectId

from my_garage.models import Vehicle, ServiceRecord, Upgrade, ConditionReport, GenericUpgrade
from ..utils.mongo import get_collection


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
    # Sum legacy upgrades
    legacy_total = Upgrade.objects.filter(
        vehicle=vehicle,
        status='INSTALLED'
    ).aggregate(
        total=Coalesce(Sum('cost'), Decimal('0.00'), output_field=DecimalField())
    )['total']

    # Sum generic upgrades
    generic_total = vehicle.projects.filter(
        status='COMPLETED'
    ).aggregate(
        total=Coalesce(Sum('cost'), Decimal('0.00'), output_field=DecimalField())
    )['total']

    return legacy_total + generic_total


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


def vehicle_list_wishlist_items(vehicle: Vehicle) -> list:
    """
    Returns all parts currently in the 'Wishlist' status (Legacy + Generic).
    """
    legacy_wishlist = list(Upgrade.objects.filter(vehicle=vehicle, status='WISHLIST').order_by('part_name'))
    generic_wishlist = list(vehicle.projects.filter(status='WISHLIST').order_by('name'))
    
    # Normalize generic items to match legacy structure for template compatibility
    for item in generic_wishlist:
        item.part_name = item.name
        
    return legacy_wishlist + generic_wishlist


def vehicle_list_service_records(vehicle: Vehicle) -> QuerySet[ServiceRecord]:
    """
    Returns all service records for the vehicle.
    """
    return ServiceRecord.objects.filter(vehicle=vehicle).order_by('-date')


def vehicle_list_upgrades(vehicle: Vehicle) -> list:
    """
    Returns all upgrades (projects) that are not in wishlist (Legacy + Generic).
    """
    legacy_upgrades = list(Upgrade.objects.filter(vehicle=vehicle).exclude(status='WISHLIST').order_by('-installation_date', 'part_name'))
    generic_upgrades = list(vehicle.projects.exclude(status='WISHLIST').order_by('-completion_date', 'name'))
    
    # Normalize generic items to match legacy structure for template compatibility
    for item in generic_upgrades:
        item.part_name = item.name
        # Map generic status to legacy status if needed
        if item.status == 'COMPLETED':
            item.status = 'INSTALLED'
        elif item.status == 'IN_PROGRESS':
            item.status = 'ORDERED' # Approximate mapping
            
    return legacy_upgrades + generic_upgrades


def vehicle_get_pending_service_count(vehicle: Vehicle) -> int:
    """
    Returns count of service records that haven't been verified by AI/User yet.
    """
    return ServiceRecord.objects.filter(vehicle=vehicle, is_verified=False).count()


def service_record_get_ocr_details(record: ServiceRecord) -> Dict[str, Any]:
    """
    Retrieves the full OCR document from MongoDB if available.
    """
    if not record.ocr_raw_data or 'mongo_id' not in record.ocr_raw_data:
        return {}

    try:
        collection = get_collection('ocr_documents')
        doc = collection.find_one({"_id": ObjectId(record.ocr_raw_data['mongo_id'])})
        if doc:
            doc['_id'] = str(doc['_id'])  # Convert ObjectId to string for JSON serialization
            return doc
    except Exception:
        # Log error in production
        pass
        
    return {}
