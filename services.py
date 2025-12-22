import requests
from django.conf import settings
from django.db import transaction
from decimal import Decimal
from typing import Dict, Any, Optional

from .models import Vehicle, ServiceRecord, Upgrade, ConditionReport

# Configuration from settings (set via Pixi/env)
FASTAPI_BASE_URL = settings.FASTAPI_BASE_URL
MCP_EXECUTE_URL = f"{FASTAPI_BASE_URL}/mcp/execute"


class VehicleServiceError(Exception):
    """Custom exception for service-level failures."""
    pass


@transaction.atomic
def vehicle_update_market_valuation(vehicle: Vehicle) -> Decimal:
    """
    Triggers the Web MCP agent to find comparable listings and
    updates the vehicle's current_market_value.
    """
    payload = {
        "tool_name": "search_market_listings",
        "arguments": {
            "make": vehicle.make,
            "model": vehicle.model,
            "year_min": vehicle.year - 1,
            "year_max": vehicle.year + 1,
            "trim": vehicle.trim
        }
    }

    try:
        response = requests.post(MCP_EXECUTE_URL, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()

        listings = data.get('results', [])
        if not listings:
            return vehicle.current_market_value

        # Logic: Calculate median price from listings
        prices = [Decimal(str(l['price'])) for l in listings]
        median_price = sorted(prices)[len(prices) // 2]

        # Update and save the vehicle
        vehicle.current_market_value = median_price
        vehicle.save(update_fields=['current_market_value'])

        return median_price

    except requests.RequestException as e:
        raise VehicleServiceError(f"Failed to reach Valuation Engine: {str(e)}")


def service_record_create_from_ocr(vehicle: Vehicle, receipt_image: Any) -> ServiceRecord:
    """
    Initializes a service record and triggers the FastAPI OCR pipeline.
    Note: In production, the heavy lifting should be moved to a Celery task.
    """
    # 1. Create the initial record with the image
    record = ServiceRecord.objects.create(
        vehicle=vehicle,
        vendor="Processing...",
        description="Awaiting AI extraction",
        total_cost=0.00,
        receipt_image=receipt_image,
        is_verified=False
    )

    # 2. Hand off to FastAPI for OCR (Conceptual - usually async)
    # response = requests.post(f"{FASTAPI_BASE_URL}/api/v1/ai/process-document/", ...)

    return record


@transaction.atomic
def condition_report_add_ai_grade(
        vehicle: Vehicle,
        area: str,
        photo: Any,
        grade: float,
        feedback: str,
        impact: Decimal
) -> ConditionReport:
    """
    Saves a new AI-generated condition report and adjusts vehicle value.
    """
    report = ConditionReport.objects.create(
        vehicle=vehicle,
        area=area,
        photo=photo,
        grade=grade,
        ai_feedback=feedback,
        value_adjustment=impact
    )

    # Adjust the vehicle's market value based on the AI's impact assessment
    vehicle.current_market_value += impact
    vehicle.save(update_fields=['current_market_value'])

    return report


def upgrade_install_part(upgrade: Upgrade, cost: Optional[Decimal] = None) -> Upgrade:
    """
    Moves a part from Wishlist/Ordered to Installed and logs final cost.
    """
    upgrade.status = 'INSTALLED'
    if cost:
        upgrade.cost = cost
    upgrade.save()
    return upgrade