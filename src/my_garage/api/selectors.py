from django.db.models import Sum, QuerySet, DecimalField, Q
from django.db.models.functions import Coalesce, Cast
from django.db.models import CharField
from decimal import Decimal
from typing import Dict, Any, List
from bson import ObjectId

from my_garage.models import Vehicle, ServiceRecord, Upgrade, ConditionReport, GenericUpgrade, Timepiece, DynamicCollectionItem
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


def vehicle_get_build_summary(vehicle: Vehicle) -> Dict[str, Any]:
    """
    Aggregates all financial and condition data for a specific vehicle dashboard.
    This is a primary 'Application Layer' selector.
    """
    maintenance = vehicle_get_total_maintenance_cost(vehicle)
    upgrades = vehicle_get_total_upgrade_cost(vehicle)
    total_investment = maintenance + upgrades + (vehicle.purchase_price or Decimal('0.00'))

    # Calculate Equity (Market Value - Total Investment)
    equity = vehicle.current_market_value - total_investment

    # Get latest condition grade
    latest_condition = ConditionReport.objects.filter(vehicle=vehicle).order_by('-created_at').first()

    return {
        "vehicle": vehicle,
        "purchase_price": vehicle.purchase_price,
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

def global_search(user, query: str) -> List[Dict[str, Any]]:
    """
    Performs a global search across Vehicles, Timepieces, and Collection Items.
    Returns a list of results with type, name, url, and icon.
    """
    results = []
    
    if not query:
        return results

    # Search Vehicles
    # Cast year to CharField to allow string searching
    vehicles = Vehicle.objects.annotate(
        year_str=Cast('year', CharField())
    ).filter(
        Q(owner=user) & (
            Q(make__icontains=query) | 
            Q(model__icontains=query) | 
            Q(year_str__icontains=query) |
            Q(trim__icontains=query) |
            Q(vin__icontains=query)
        )
    )[:5]
    
    for v in vehicles:
        results.append({
            'type': 'Vehicle',
            'name': f"{v.year} {v.make} {v.model}",
            'subtext': v.trim,
            'url': f"/garage/{v.id}/",
            'icon': 'fa-car',
            'category': 'Garage'
        })

    # Search Timepieces
    timepieces = Timepiece.objects.filter(
        Q(owner=user) & (
            Q(brand__icontains=query) | 
            Q(model__icontains=query) | 
            Q(reference_number__icontains=query)
        )
    )[:5]
    
    for t in timepieces:
        results.append({
            'type': 'Timepiece',
            'name': f"{t.brand} {t.model}",
            'subtext': t.reference_number,
            'url': f"/timepieces/{t.id}/",
            'icon': 'fa-clock',
            'category': 'Timepieces'
        })

    # Search Collection Items
    items = DynamicCollectionItem.objects.filter(
        Q(owner=user) & (
            Q(name__icontains=query) |
            Q(collection_type__name__icontains=query)
        )
    ).select_related('collection_type')[:5]
    
    for item in items:
        results.append({
            'type': item.collection_type.name,
            'name': item.name,
            'subtext': item.collection_type.name,
            'url': f"/collections/{item.collection_type.slug}/items/{item.id}/",
            'icon': item.collection_type.icon or 'fa-box',
            'category': 'Collections'
        })

    return results
