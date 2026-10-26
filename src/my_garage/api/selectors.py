from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.contenttypes.models import ContentType
from django.db.models import Exists, OuterRef, Q, Sum
from django.utils import timezone

from my_garage.models import (
    BeneficiaryAssignment,
    CollectionItemAttachment,
    DynamicCollectionItem,
    EstateAccessLog,
    EstateAccessToken,
    EstateChangeLog,
    EstateExecutor,
    GenericServiceRecord,
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


def get_estate_dashboard_context(user) -> Dict[str, Any]:
    """
    Assemble all data needed for the estate dashboard in exactly 3 ORM queries.

    Returns:
        executor         — EstateExecutor instance or None
        items            — list of DynamicCollectionItem annotated with `is_assigned`
        items_total      — int
        items_assigned   — int
        completeness_pct — int 0-100 (0 when items_total == 0)
        recent_log       — list of up to 10 EstateChangeLog entries (newest first)
    """
    executor = EstateExecutor.objects.filter(owner=user).first()  # Q1

    items = list(
        DynamicCollectionItem.objects.filter(owner=user)
        .select_related("collection_type", "estate_assignment__beneficiary")
        .annotate(
            is_assigned=Exists(
                BeneficiaryAssignment.objects.filter(item_id=OuterRef("pk"))
            )
        )
        .order_by("collection_type__name", "name")
    )  # Q2

    items_total = len(items)
    items_assigned = sum(1 for item in items if item.is_assigned)
    completeness_pct = int(items_assigned / items_total * 100) if items_total > 0 else 0

    recent_log = list(EstateChangeLog.objects.filter(owner=user)[:10])  # Q3

    return {
        "executor": executor,
        "items": items,
        "items_total": items_total,
        "items_assigned": items_assigned,
        "completeness_pct": completeness_pct,
        "recent_log": recent_log,
    }


def get_executor_access_status(user) -> Dict[str, Any]:
    """
    Executor access status for the owner's activate page.

    Returns token (active one, else latest, else None), state
    (none/revoked/expired/unused/in_use) and recent_events (last 10 log rows).
    """
    tokens = EstateAccessToken.objects.filter(owner=user)
    token = (
        tokens.filter(is_active=True).order_by("-issued_at", "-pk").first()
        or tokens.order_by("-issued_at", "-pk").first()
    )
    now = timezone.now()
    if token is None:
        state = "none"
    elif not token.is_active:
        state = "revoked"
    elif token.expires_at is not None and token.expires_at <= now:
        state = "expired"
    elif token.use_count == 0:
        state = "unused"
    else:
        state = "in_use"
    recent_events = list(EstateAccessLog.objects.filter(owner=user)[:10])
    return {"token": token, "state": state, "recent_events": recent_events}


def media_file_owner_id(path: str) -> Optional[int]:
    """
    Return the id of the user who owns the uploaded file stored at `path`
    (relative to MEDIA_ROOT), or None if no record references it.

    Every upload belongs to a DynamicCollectionItem: its photo, a service
    record's receipt, or an attachment.
    """
    owner_id = (
        DynamicCollectionItem.objects.filter(photo=path)
        .values_list("owner_id", flat=True)
        .first()
    )
    if owner_id is None:
        owner_id = (
            GenericServiceRecord.objects.filter(receipt_image=path)
            .values_list("item__owner_id", flat=True)
            .first()
        )
    if owner_id is None:
        owner_id = (
            CollectionItemAttachment.objects.filter(file=path)
            .values_list("item__owner_id", flat=True)
            .first()
        )
    return owner_id
