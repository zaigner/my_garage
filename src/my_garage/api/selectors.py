from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Sum

from my_garage.models import (
    BeneficiaryAssignment,
    DynamicCollectionItem,
    GenericUpgrade,
    PortfolioSnapshot,
)


def get_item_nfp_breakdown(item: DynamicCollectionItem) -> Dict[str, Any]:
    """
    Calculate the full NFP cost breakdown for a DynamicCollectionItem.

    Returns a dict with:
      purchase_price, service_total, upgrade_total,
      cost_basis, market_value, net_position

    net_position is None when current_market_value is None.
    purchase_price is allowed to be None; cost_basis treats it as zero.

    Upgrades are resolved from both the direct FK (item=) and the
    GenericForeignKey (content_type/object_id) paths to handle all
    linking conventions in use.
    """
    purchase_price = item.purchase_price
    market_value = item.current_market_value

    service_agg = item.service_records.aggregate(total=Sum("total_cost"))
    service_total = service_agg["total"] or Decimal("0.00")

    ct = ContentType.objects.get_for_model(DynamicCollectionItem)
    upgrade_agg = GenericUpgrade.objects.filter(
        Q(item=item) | Q(content_type=ct, object_id=item.pk),
        status="COMPLETED",
    ).aggregate(total=Sum("cost"))
    upgrade_total = upgrade_agg["total"] or Decimal("0.00")

    cost_basis = (purchase_price or Decimal("0.00")) + service_total + upgrade_total

    if market_value is None:
        net_position = None
    else:
        net_position = market_value - cost_basis

    return {
        "purchase_price": purchase_price,
        "service_total": service_total,
        "upgrade_total": upgrade_total,
        "cost_basis": cost_basis,
        "market_value": market_value,
        "net_position": net_position,
    }


def get_item_estate_assignment(
    item: DynamicCollectionItem, user
) -> Optional[BeneficiaryAssignment]:
    """Return the BeneficiaryAssignment for this item, or None if unassigned."""
    try:
        assignment = item.estate_assignment
        if assignment.item.collection_type.owner != user:
            return None
        return assignment
    except BeneficiaryAssignment.DoesNotExist:
        return None


def get_portfolio_nfp_summary(user) -> Optional[Decimal]:
    """
    Return the aggregate net_financial_position across all DynamicCollectionItem
    owned by this user. Single aggregate query — no per-item iteration.
    Returns None when no items have NFP set.
    """
    result = DynamicCollectionItem.objects.filter(owner=user).aggregate(
        total=Sum("net_financial_position")
    )
    return result["total"]


def get_portfolio_nfp_by_collection(user) -> Dict[str, Optional[Decimal]]:
    """
    Return per-collection-type NFP totals for a user.
    Single aggregate query grouped by collection_type name.
    Returns a dict: {collection_type_name: nfp_total_or_None}
    """
    rows = (
        DynamicCollectionItem.objects.filter(owner=user)
        .values("collection_type__name")
        .annotate(nfp=Sum("net_financial_position"))
    )
    return {row["collection_type__name"]: row["nfp"] for row in rows}


def global_search(user, query: str) -> List[Dict[str, Any]]:
    """
    Performs a global search across DynamicCollectionItems.
    Returns a list of results with type, name, url, and icon.
    """
    if not query:
        return []

    items = DynamicCollectionItem.objects.filter(
        Q(owner=user)
        & (
            Q(name__icontains=query)
            | Q(collection_type__name__icontains=query)
            | Q(notes__icontains=query)
        )
    ).select_related("collection_type")[:10]

    results = []
    for item in items:
        results.append(
            {
                "type": item.collection_type.name,
                "name": item.name,
                "subtext": item.collection_type.name,
                "url": f"/collections/{item.collection_type.slug}/items/{item.id}/",
                "icon": item.collection_type.icon or "fa-box",
                "category": item.collection_type.name,
            }
        )
    return results


def portfolio_get_yoy_change(
    user,
    today: Optional[date] = None,
) -> Tuple[Optional[Decimal], str]:
    """
    Compute the year-over-year portfolio value change for a user.

    Returns (pct_change, source) where source is one of:
      "snapshot"      — compared against a real PortfolioSnapshot from ~1 year ago
      "purchase_price" — no snapshot yet; baseline is cost of items bought >365 days ago
      "none"          — not enough data to compute a meaningful figure

    pct_change is None when source is "none".
    """
    if today is None:
        today = date.today()

    # Current total value
    items = DynamicCollectionItem.objects.filter(owner=user)
    current_total = sum(
        i.current_market_value for i in items if i.current_market_value
    ) or Decimal("0")

    # --- Try a real snapshot from ±30 days around one year ago ---
    one_year_ago = today - timedelta(days=365)
    window_start = one_year_ago - timedelta(days=30)
    window_end = one_year_ago + timedelta(days=30)

    snapshot = (
        PortfolioSnapshot.objects.filter(
            user=user,
            date__gte=window_start,
            date__lte=window_end,
        )
        .order_by("date")  # closest to one_year_ago from below; good enough
        .last()  # latest within window ≈ closest to target date
    )

    if snapshot is not None and snapshot.total_value:
        past_value = snapshot.total_value
        source = "snapshot"
    else:
        # Fallback: sum purchase_price of items acquired before the window
        cutoff = today - timedelta(days=365)
        old_items = [
            i
            for i in items
            if (i.purchase_date and i.purchase_date < cutoff)
            or (not i.purchase_date and i.created_at and i.created_at.date() < cutoff)
        ]
        if not old_items:
            return None, "none"
        past_value = sum(
            i.purchase_price for i in old_items if i.purchase_price
        ) or Decimal("0")
        if not past_value:
            return None, "none"
        source = "purchase_price"

    if past_value == 0:
        return None, "none"

    pct_change = ((current_total - past_value) / past_value) * Decimal("100")
    return pct_change.quantize(Decimal("0.1")), source
