import secrets
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Exists, Max, OuterRef, Q, Sum
from django.utils import timezone

from my_garage.models import (
    Beneficiary,
    BeneficiaryAccessLink,
    BeneficiaryAssignment,
    CollectionItemAttachment,
    DynamicCollectionItem,
    EstateAccessLog,
    EstateAccessToken,
    EstateChangeLog,
    EstateExecutor,
    GenericServiceRecord,
    GenericUpgrade,
    GenericValuationHistory,
    PortfolioSnapshot,
    ValuationSnapshot,
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

    Items in soft-deleted collections (CollectionType.is_active=False) are
    left out of the list and every total.
    """
    executor = EstateExecutor.objects.filter(owner=user).first()  # Q1

    items = list(
        DynamicCollectionItem.objects.filter(
            owner=user, collection_type__is_active=True
        )
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


def get_estate_assign_items(user) -> List[DynamicCollectionItem]:
    """
    The owner's items for the estate assign overview, with their designation,
    ordered by collection then name. Soft-deleted collections are left out.
    """
    return list(
        DynamicCollectionItem.objects.filter(
            owner=user, collection_type__is_active=True
        )
        .select_related("collection_type", "estate_assignment__beneficiary")
        .order_by("collection_type__name", "name")
    )


ESTATE_SECURITY_EVENTS = (
    "TOKEN_ISSUED",
    "TOKEN_REVOKED",
    "CODE_ACCEPTED",
    "CODE_REJECTED",
    "LINK_ISSUED",
    "LINK_REVOKED",
    "LINK_CLAIMED",
)
ESTATE_VIEW_EVENTS = ("PORTAL_VIEW", "ITEM_VIEW", "BENEFICIARY_VIEW")
# Beneficiary views share the executor's token, so the owner's
# "Portal views with this code" count leaves them out
EXECUTOR_VIEW_EVENTS = ("PORTAL_VIEW", "ITEM_VIEW")


def get_executor_access_status(user) -> Dict[str, Any]:
    """
    Executor access status for the owner's activate page.

    Returns:
      token           active token, else latest, else None
      state           none/revoked/expired/unused/in_use
      security_events last 10 TOKEN_*/CODE_* log rows, newest first; page
                      views are left out so they can't crowd these off
      view_count      PORTAL_VIEW + ITEM_VIEW rows for the returned token
      last_view_at    newest of those rows' timestamps, or None
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
    logs = EstateAccessLog.objects.filter(owner=user)
    security_events = list(logs.filter(event__in=ESTATE_SECURITY_EVENTS)[:10])
    views = {"n": 0, "last": None}
    if token is not None:
        views = logs.filter(token=token, event__in=EXECUTOR_VIEW_EVENTS).aggregate(
            n=Count("pk"), last=Max("timestamp")
        )
    return {
        "token": token,
        "state": state,
        "security_events": security_events,
        "view_count": views["n"],
        "last_view_at": views["last"],
    }


def _designated_beneficiaries(owner):
    """Owner's beneficiaries with at least one designated item, item-counted."""
    designated = Q(
        assignments__is_charitable=False,
        assignments__item__collection_type__is_active=True,
    )
    return (
        Beneficiary.objects.filter(owner=owner)
        .annotate(item_count=Count("assignments", filter=designated, distinct=True))
        .filter(item_count__gt=0)
        .order_by("name", "pk")
    )


def get_executor_beneficiary(owner, beneficiary_id) -> Optional[Beneficiary]:
    """The owner's eligible beneficiary (>= 1 designated item), or None."""
    return _designated_beneficiaries(owner).filter(pk=beneficiary_id).first()


def beneficiary_link_status(link, now) -> str:
    """none / revoked / opened / expired / issued for a link (or None)."""
    if link is None:
        return "none"
    if not link.is_active:
        return "revoked"
    if link.claimed_at is not None:
        return "opened"
    if link.expires_at <= now:
        return "expired"
    return "issued"


def get_executor_beneficiary_links(owner, token) -> List[Dict[str, Any]]:
    """
    Designated beneficiaries with their link status, in 2 queries.

    Status comes from the newest link issued under `token`; links from an
    earlier activation are ignored. Each dict: beneficiary, item_count, link,
    status (none/issued/opened/revoked/expired).
    """
    beneficiaries = list(_designated_beneficiaries(owner))
    newest: Dict[int, BeneficiaryAccessLink] = {}
    if beneficiaries:
        links = BeneficiaryAccessLink.objects.filter(
            beneficiary__in=beneficiaries, issued_by_token=token
        ).order_by("-issued_at", "-pk")
        for link in links:
            newest.setdefault(link.beneficiary_id, link)
    now = timezone.now()
    return [
        {
            "beneficiary": b,
            "item_count": b.item_count,
            "link": newest.get(b.pk),
            "status": beneficiary_link_status(newest.get(b.pk), now),
        }
        for b in beneficiaries
    ]


def get_claimable_beneficiary_link(
    link_hash: str, now
) -> Optional[BeneficiaryAccessLink]:
    """
    The link with this SHA-256 hash if it can be claimed now, else None:
    active, unclaimed, unexpired, and its issuing executor token usable.
    Read-only; claim_beneficiary_link re-runs it under a lock.
    """
    link = (
        BeneficiaryAccessLink.objects.filter(link_token_hash=link_hash)
        .select_related("beneficiary", "owner", "issued_by_token")
        .first()
    )
    if link is None or not secrets.compare_digest(link.link_token_hash, link_hash):
        return None
    if not link.is_active or link.claimed_at is not None or link.expires_at <= now:
        return None
    token = link.issued_by_token
    if token is None or not token.is_usable(now):
        return None
    return link


def get_beneficiary_session_link(link_id, owner_id) -> Optional[BeneficiaryAccessLink]:
    """
    The claimed link behind a beneficiary session if it still grants access:
    active, claimed, and its issuing executor token usable. Else None.
    """
    link = (
        BeneficiaryAccessLink.objects.filter(pk=link_id, owner_id=owner_id)
        .select_related("beneficiary", "owner", "issued_by_token")
        .first()
    )
    if link is None or not link.is_active or link.claimed_at is None:
        return None
    token = link.issued_by_token
    if token is None or not token.is_usable(timezone.now()):
        return None
    return link


def get_beneficiary_assignments(link) -> List[BeneficiaryAssignment]:
    """
    The items designated to the link's beneficiary, in one query. Isolation
    is enforced here: only this beneficiary's non-charitable assignments on
    the owner's items in active collections.
    """
    return list(
        BeneficiaryAssignment.objects.filter(
            beneficiary=link.beneficiary,
            is_charitable=False,
            item__owner=link.owner,
            item__collection_type__is_active=True,
        )
        .select_related("item__collection_type")
        .order_by("item__collection_type__name", "item__name", "item__pk")
    )


def _sum_or_none(values) -> Optional[Decimal]:
    present = [v for v in values if v is not None]
    return sum(present, Decimal("0")) if present else None


# Keys injected by enrichment/migration scripts: rendered in their own panels
# or internal flags, so never listed as plain custom fields.
_ENRICHMENT_KEYS = {"specs", "features", "migrated"}


def get_system_field_names(collection_type) -> set:
    """Form field names (`custom_<name>`) of system-managed schema fields."""
    schema = collection_type.field_schema or {}
    return {
        f"custom_{field['name']}"
        for field in schema.get("fields", [])
        if field.get("system") or field.get("type") == "system_json"
    }


def get_item_display_custom_fields(
    item: DynamicCollectionItem, collection_type=None
) -> List[Tuple[str, Any]]:
    """
    Custom fields formatted for read-only display as (label, value) pairs.

    Skips system-managed schema fields, enrichment keys and empty values.
    Shared by the owner item page and the executor portal. Pass an
    already-loaded `collection_type` to avoid an extra query.
    """
    system_field_names = get_system_field_names(collection_type or item.collection_type)
    return [
        (key.replace("_", " ").title(), value)
        for key, value in (item.custom_fields or {}).items()
        if f"custom_{key}" not in system_field_names
        and key not in _ENRICHMENT_KEYS
        and value not in (None, "", [], {})
    ]


def get_executor_item(owner, item_id) -> Optional[DynamicCollectionItem]:
    """
    The owner's item, or None (the executor portal answers 404). Items in
    soft-deleted collections are out of the estate, so they read as None.
    """
    return (
        DynamicCollectionItem.objects.filter(
            pk=item_id, owner=owner, collection_type__is_active=True
        )
        .select_related("collection_type", "estate_assignment__beneficiary")
        .first()
    )


def _designation_fields(item: DynamicCollectionItem) -> Dict[str, Any]:
    """Beneficiary designation of an item, shared by the portal's list and detail."""
    try:
        assignment = item.estate_assignment
    except BeneficiaryAssignment.DoesNotExist:
        assignment = None
    is_charitable = bool(assignment and assignment.is_charitable)
    beneficiary = assignment.beneficiary if assignment else None
    return {
        "beneficiary_name": beneficiary.name if beneficiary else "",
        "charitable_org": assignment.charitable_org if is_charitable else "",
        "is_charitable": is_charitable,
        # A deleted beneficiary leaves the assignment with a null FK
        "is_unassigned": not is_charitable and beneficiary is None,
        "conditional_note": (assignment.conditional_note or "").strip()
        if assignment
        else "",
    }


def get_executor_portfolio_context(owner, token) -> Dict[str, Any]:
    """
    Read-only portfolio for the executor portal, in 2 ORM queries.

    `token` is the executor's EstateAccessToken; "value at activation" comes
    only from the ESTATE_ACTIVATION snapshots bound to it (activate_estate_plan
    sets ValuationSnapshot.token). Snapshots of other tokens are ignored.

    Returns:
        rows             — one dict per current item: item, in_snapshot (item
                           existed at activation), snapshot_value,
                           current_value, beneficiary_name, charitable_org,
                           is_charitable, is_unassigned
        removed_rows     — one dict per snapshotted item no longer in the
                           estate: deleted after activation (its snapshot
                           row remains with item=None) or in a collection
                           soft-deleted after activation. item (None),
                           item_name (stored at activation), snapshot_value,
                           removed (True); ordered by name
        removed_count    — int, len(removed_rows)
        items_total      — int, current items only
        unassigned_count — int, current items only
        snapshot_total   — Decimal or None (sum of known snapshot values,
                           removed items included)
        snapshot_count   — int, items with a known snapshot value (removed
                           items included)
        current_total    — Decimal or None (sum of known current values)
        current_count    — int, items with a known current value
        delta            — Decimal or None (current − snapshot, summed over
                           current items valued at both)
        compared_count   — int, items included in delta

    Items in soft-deleted collections (CollectionType.is_active=False) are not
    current items.
    """
    items = list(
        DynamicCollectionItem.objects.filter(
            owner=owner, collection_type__is_active=True
        )
        .select_related("collection_type", "estate_assignment__beneficiary")
        .order_by("collection_type__name", "name")
    )  # Q1

    snapshots = list(
        ValuationSnapshot.objects.filter(
            owner=owner, snapshot_trigger="ESTATE_ACTIVATION", token=token
        )
        .order_by("-created_at", "-pk")
        .values_list("item_id", "item_name", "market_value")
    )  # Q2
    # Newest row first, as the detail selector's .first() picks.
    # A snapshot whose item is not a current item (deleted, or its collection
    # soft-deleted after activation) becomes a removed row.
    current_ids = {item.pk for item in items}
    activation_values: Dict[int, Any] = {}
    out_of_scope_ids = set()
    removed_rows = []
    for item_id, name, value in snapshots:
        if item_id in current_ids:
            activation_values.setdefault(item_id, value)
            continue
        if item_id is not None:
            if item_id in out_of_scope_ids:
                continue
            out_of_scope_ids.add(item_id)
        removed_rows.append(
            {
                "item": None,
                "item_name": name,
                "snapshot_value": value,
                "removed": True,
            }
        )
    removed_rows.sort(key=lambda r: r["item_name"].lower())

    rows = []
    for item in items:
        designation = _designation_fields(item)
        rows.append(
            {
                "item": item,
                "in_snapshot": item.pk in activation_values,
                "snapshot_value": activation_values.get(item.pk),
                "current_value": item.current_market_value,
                **{k: v for k, v in designation.items() if k != "conditional_note"},
            }
        )

    compared = [
        r
        for r in rows
        if r["snapshot_value"] is not None and r["current_value"] is not None
    ]
    delta = (
        sum((r["current_value"] - r["snapshot_value"] for r in compared), Decimal("0"))
        if compared
        else None
    )

    activation_rows = rows + removed_rows
    return {
        "rows": rows,
        "removed_rows": removed_rows,
        "removed_count": len(removed_rows),
        "items_total": len(rows),
        "unassigned_count": sum(1 for r in rows if r["is_unassigned"]),
        "snapshot_total": _sum_or_none(r["snapshot_value"] for r in activation_rows),
        "snapshot_count": sum(
            1 for r in activation_rows if r["snapshot_value"] is not None
        ),
        "current_total": _sum_or_none(r["current_value"] for r in rows),
        "current_count": sum(1 for r in rows if r["current_value"] is not None),
        "delta": delta,
        "compared_count": len(compared),
    }


def get_executor_item_detail_context(owner, token, item_id) -> Optional[Dict[str, Any]]:
    """
    Read-only detail of one item for the executor portal, in 4 ORM queries.

    Returns None when the item does not belong to `owner` (callers answer 404).

    Returns:
        item, row            — row carries the designation fields shared with
                               the portfolio rows (plus conditional_note)
        snapshot             — the ValuationSnapshot bound to `token`, or
                               None when the item was added after activation
        conditional_note     — str, blank when none
        custom_fields        — list of (label, value)
        service_records      — list, newest first
        valuation_history    — list, newest first
    """
    item = get_executor_item(owner, item_id)  # Q1
    if item is None:
        return None

    snapshot = (
        ValuationSnapshot.objects.filter(
            item=item,
            owner=owner,
            snapshot_trigger="ESTATE_ACTIVATION",
            token=token,
        )
        .order_by("-created_at", "-pk")
        .first()
    )  # Q2

    designation = _designation_fields(item)
    row = {
        "item": item,
        "in_snapshot": snapshot is not None,
        "snapshot_value": snapshot.market_value if snapshot else None,
        "current_value": item.current_market_value,
        **designation,
    }
    return {
        "item": item,
        "row": row,
        "snapshot": snapshot,
        "conditional_note": designation["conditional_note"],
        "custom_fields": get_item_display_custom_fields(item),
        "service_records": list(
            GenericServiceRecord.objects.filter(item=item).order_by("-date", "-pk")
        ),  # Q3
        "valuation_history": list(
            GenericValuationHistory.objects.filter(item=item).order_by("-date", "-pk")
        ),  # Q4
    }


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
