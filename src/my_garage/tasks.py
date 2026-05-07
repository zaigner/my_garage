import logging
from datetime import date
from decimal import Decimal

from config.celery_app import app as celery_app
from my_garage.models import DynamicCollectionItem, PortfolioSnapshot

from .services.collection_services import get_collection_services

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
RETRY_KWARGS = {
    "max_retries": 5,
    "default_retry_delay": 60,  # 1 minute
    "backoff": True,
}


@celery_app.task(bind=True, name="my_garage.collection_item_refresh_valuation", **RETRY_KWARGS)
def task_collection_item_refresh_valuation(self, item_id: int):
    """
    Background task: refresh market valuation for a DynamicCollectionItem
    using the service provider registered for its CollectionType.
    """
    try:
        item = DynamicCollectionItem.objects.select_related("collection_type").get(pk=item_id)
        provider = get_collection_services(item.collection_type.service_provider_key)
        if provider.supports_valuation_refresh():
            new_value = provider.run_valuation(item)
            logger.info("Valuation updated for item %s: %s", item, new_value)
            return str(new_value)
        logger.warning("Item %s provider does not support valuation refresh", item)
        return None
    except DynamicCollectionItem.DoesNotExist:
        logger.error("DynamicCollectionItem %s not found.", item_id)
    except Exception as exc:
        logger.error("Valuation failed for item %s: %s", item_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(bind=True, name="my_garage.collection_item_enrich", **RETRY_KWARGS)
def task_collection_item_enrich(self, item_id: int):
    """
    Background task: run provider enrichment (e.g. VIN decode) for a
    DynamicCollectionItem.
    """
    try:
        item = DynamicCollectionItem.objects.select_related("collection_type").get(pk=item_id)
        provider = get_collection_services(item.collection_type.service_provider_key)
        if provider.supports_enrichment():
            data = provider.run_enrichment(item)
            logger.info("Enrichment complete for item %s", item)
            return bool(data)
        logger.warning("Item %s provider does not support enrichment", item)
        return False
    except DynamicCollectionItem.DoesNotExist:
        logger.error("DynamicCollectionItem %s not found.", item_id)
    except Exception as exc:
        logger.error("Enrichment failed for item %s: %s", item_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(name="my_garage.tasks.task_refresh_bmad_context")
def task_refresh_bmad_context():
    """
    Daily periodic task to refresh the BMAD project context file
    with live portfolio statistics.
    """
    from django.core.management import call_command

    try:
        call_command("refresh_bmad_context")
        return "BMAD context refreshed."
    except Exception as e:
        logger.error(f"Failed to refresh BMAD context: {e}")
        return f"Failed: {e}"


@celery_app.task(name="my_garage.tasks.task_take_portfolio_snapshot")
def task_take_portfolio_snapshot():
    """
    Daily periodic task: snapshot total portfolio value for every user with assets.
    Creates or updates one PortfolioSnapshot row per (user, today).
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    today = date.today()
    snapped = 0

    for user in User.objects.all():
        items = DynamicCollectionItem.objects.filter(owner=user)
        total = sum(i.current_market_value for i in items if i.current_market_value) or Decimal("0")
        PortfolioSnapshot.objects.update_or_create(
            user=user,
            date=today,
            defaults={"total_value": total},
        )
        snapped += 1

    logger.info("Portfolio snapshots taken for %d users on %s", snapped, today)
    return f"Snapped {snapped} portfolios."


@celery_app.task(bind=True, name="my_garage.process_generic_service_record_ocr", **RETRY_KWARGS)
def task_process_generic_service_record_ocr(self, record_id: int):
    """Background task: run OCR on a GenericServiceRecord's receipt image."""
    from my_garage.api.services import process_generic_service_record_ocr

    try:
        from my_garage.models import GenericServiceRecord

        record = GenericServiceRecord.objects.get(pk=record_id)
        process_generic_service_record_ocr(record)
        logger.info("OCR complete for GenericServiceRecord pk=%s", record_id)
    except Exception as exc:
        logger.error("OCR task failed for record %s: %s", record_id, exc)
        raise self.retry(exc=exc)


@celery_app.task(name="my_garage.tasks.task_bulk_valuation_refresh")
def task_bulk_valuation_refresh():
    """
    Daily/Weekly periodic task to refresh all collection item values.
    Designed to be run by Celery Beat.
    """
    item_ids = DynamicCollectionItem.objects.values_list("id", flat=True).iterator()
    count = 0
    for item_id in item_ids:
        task_collection_item_refresh_valuation.delay(item_id)
        count += 1
    return f"Queued refresh for {count} collection items."
