import logging

from config.celery_app import app as celery_app
from my_garage.models import DynamicCollectionItem

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
