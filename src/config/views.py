from datetime import datetime

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from my_garage.api.selectors import portfolio_get_yoy_change
from my_garage.forms import RegistrationForm
from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    GenericServiceRecord,
    GenericValuationHistory,
)


def get_sort_date(item):
    if hasattr(item, "created_at") and item.created_at:
        if isinstance(item.created_at, datetime):
            return item.created_at.date()
        return item.created_at
    if hasattr(item, "purchase_date") and item.purchase_date:
        return item.purchase_date
    return datetime(1900, 1, 1).date()


def home(request: HttpRequest) -> HttpResponse:
    """
    Home page view. Automobile/timepiece counts and values come exclusively
    from DynamicCollectionItem (legacy Vehicle/Timepiece models retired in Phase 5).
    """
    context = {}
    if request.user.is_authenticated:
        all_collection_items = DynamicCollectionItem.objects.filter(owner=request.user)

        # ── System collection stats ──────────────────────────────────────────
        automobiles_items = all_collection_items.filter(
            collection_type__slug="automobiles"
        )
        horology_items = all_collection_items.filter(
            collection_type__slug="horology-salon"
        )

        automobiles_count = automobiles_items.count()
        timepieces_count = horology_items.count()

        total_automobiles_value = sum(
            i.current_market_value for i in automobiles_items if i.current_market_value
        )
        total_timepieces_value = sum(
            i.current_market_value for i in horology_items if i.current_market_value
        )

        # ── Custom (non-system) collections ─────────────────────────────────
        system_slugs = {"automobiles", "horology-salon"}
        collection_types = CollectionType.objects.filter(
            owner=request.user, is_active=True
        )
        custom_collections = []
        for c_type in collection_types:
            if c_type.slug in system_slugs:
                continue
            items = all_collection_items.filter(collection_type=c_type)
            c_type.item_count = items.count()
            c_type.total_value = sum(item.current_market_value or 0 for item in items)
            custom_collections.append(c_type)

        # ── Total portfolio value ────────────────────────────────────────────
        non_system_items = all_collection_items.exclude(
            collection_type__slug__in=system_slugs
        )
        total_collections_value = sum(
            i.current_market_value for i in non_system_items if i.current_market_value
        )

        # ── Recent acquisitions (collection items only) ───────────────────────
        recent_acquisitions = sorted(
            all_collection_items.select_related("collection_type"),
            key=get_sort_date,
            reverse=True,
        )[:3]

        yoy_pct_change, yoy_source = portfolio_get_yoy_change(request.user)

        context.update(
            {
                "automobiles_count": automobiles_count,
                "timepieces_count": timepieces_count,
                "total_automobiles_value": total_automobiles_value,
                "total_timepieces_value": total_timepieces_value,
                "total_collections_value": total_collections_value,
                "custom_collections": custom_collections,
                "recent_acquisitions": recent_acquisitions,
                "yoy_pct_change": yoy_pct_change,
                "yoy_source": yoy_source,
            }
        )

    return render(request, "pages/home.html", context)


def register(request: HttpRequest) -> HttpResponse:
    """
    Register a new user.
    """
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request, "Registration successful. Welcome to The Collection."
            )
            return redirect("onboarding")
    else:
        form = RegistrationForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
def onboarding(request: HttpRequest) -> HttpResponse:
    """
    First-time user onboarding checklist. Shown after registration.
    """
    user = request.user
    has_items = DynamicCollectionItem.objects.filter(owner=user).exists()
    has_valuation = GenericValuationHistory.objects.filter(item__owner=user).exists()
    has_service = GenericServiceRecord.objects.filter(item__owner=user).exists()
    return render(
        request,
        "pages/onboarding.html",
        {
            "has_items": has_items,
            "has_valuation": has_valuation,
            "has_service": has_service,
        },
    )
