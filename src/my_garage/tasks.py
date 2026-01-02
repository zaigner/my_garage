import logging
from config.celery_app import app as celery_app
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from decimal import Decimal

# Import the service layer logic
from .api.services import (
    vehicle_update_market_valuation,
    VehicleServiceError,
    service_record_process_ocr_data
)
from my_garage.models import Vehicle, ServiceRecord

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# We define retry settings for AI/External API tasks
RETRY_KWARGS = {
    'max_retries': 5,
    'default_retry_delay': 60,  # 1 minute
    'backoff': True,
}


@celery_app.task(bind=True, **RETRY_KWARGS)
def task_process_receipt_ocr(self, record_id: int):
    """
    Background task to process a receipt via the FastAPI AI engine.
    Uses the service layer to handle the specific logic.
    """
    try:
        record = ServiceRecord.objects.select_related('vehicle').get(pk=record_id)
        logger.info(f"Processing OCR for Record #{record_id}...")

        # Delegate to Service Layer
        success = service_record_process_ocr_data(record)

        if not success:
            logger.warning(f"OCR failed for record {record_id}, no data extracted.")
            return False

        logger.info(f"Successfully processed Record #{record_id}")
        return True

    except ServiceRecord.DoesNotExist:
        logger.error(f"ServiceRecord {record_id} not found.")
    except Exception as exc:
        logger.error(f"Transient error in OCR for {record_id}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(bind=True, name="my_garage.update_valuation", **RETRY_KWARGS)
def task_update_market_valuation(self, vehicle_id: int):
    """
    Updates the current market value of a vehicle using the Web MCP agent.
    """
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)

        # Trigger Service Layer
        new_value = vehicle_update_market_valuation(vehicle)

        logger.info(f"Valuation updated for {vehicle}: {new_value}")
        return str(new_value)

    except Vehicle.DoesNotExist:
        logger.error(f"Vehicle {vehicle_id} not found.")
    except VehicleServiceError as e:
        logger.warning(f"Valuation failed for vehicle {vehicle_id}: {e}")
        raise self.retry(exc=e)


@celery_app.task(name="my_garage.bulk_refresh")
def task_bulk_valuation_refresh():
    """
    Daily/Weekly periodic task to refresh all vehicle values.
    Designed to be run by Celery Beat.
    """
    # Use .iterator() to keep memory usage low for large garages
    vehicle_ids = Vehicle.objects.values_list('id', flat=True).iterator()
    count = 0

    for v_id in vehicle_ids:
        # IMPORTANT: Use delay_on_commit if calling from inside a transaction
        # Otherwise, standard .delay() is fine for a background manager.
        task_update_market_valuation.delay(v_id)
        count += 1

    return f"Queued refresh for {count} vehicles."
