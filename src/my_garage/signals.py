"""
Signal handlers for NFP cache invalidation.

DynamicCollectionItem, GenericServiceRecord, and GenericUpgrade post_save/post_delete
signals call refresh_item_nfp so net_financial_position and total_cost_basis stay
current within the HTTP request/response cycle.
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from my_garage.models import DynamicCollectionItem, GenericServiceRecord, GenericUpgrade

_NFP_FIELDS = frozenset({"net_financial_position", "total_cost_basis"})


@receiver(post_save, sender=DynamicCollectionItem, dispatch_uid="nfp_item_save")
def handle_item_change(sender, instance, **kwargs):
    """Refresh NFP when purchase_price or current_market_value changes on the item.

    The loop guard skips re-entry when refresh_item_nfp itself calls save().
    """
    update_fields = kwargs.get("update_fields")
    if update_fields is not None and set(update_fields) <= _NFP_FIELDS:
        return
    from my_garage.api.services import refresh_item_nfp

    refresh_item_nfp(instance)


@receiver(
    post_save, sender=GenericServiceRecord, dispatch_uid="nfp_service_record_save"
)
@receiver(
    post_delete, sender=GenericServiceRecord, dispatch_uid="nfp_service_record_delete"
)
def handle_service_record_change(sender, instance, **kwargs):
    from my_garage.api.services import refresh_item_nfp

    if not instance.item_id:
        return
    item = DynamicCollectionItem.objects.filter(pk=instance.item_id).first()
    if item is not None:
        refresh_item_nfp(item)


@receiver(post_save, sender=GenericUpgrade, dispatch_uid="nfp_upgrade_save")
@receiver(post_delete, sender=GenericUpgrade, dispatch_uid="nfp_upgrade_delete")
def handle_upgrade_change(sender, instance, **kwargs):
    from my_garage.api.services import refresh_item_nfp

    item = None

    # Direct FK path (most common)
    if instance.item_id:
        item = DynamicCollectionItem.objects.filter(pk=instance.item_id).first()

    # GenericForeignKey path
    elif instance.content_type_id and instance.object_id:
        item = DynamicCollectionItem.objects.filter(pk=instance.object_id).first()

    if item is not None:
        refresh_item_nfp(item)
