"""Estate & Legacy views."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from my_garage.api.selectors import (
    get_estate_dashboard_context,
    get_item_estate_assignment,
)
from my_garage.api.services import (
    activate_estate_plan,
    assign_beneficiary,
    remove_beneficiary_assignment,
)
from my_garage.forms import (
    BeneficiaryAssignmentForm,
    BeneficiaryForm,
    EstateActivateForm,
    EstateExecutorForm,
)
from my_garage.models import (
    Beneficiary,
    DynamicCollectionItem,
    EstateExecutor,
)


@login_required
def estate_dashboard(request: HttpRequest) -> HttpResponse:
    context = get_estate_dashboard_context(request.user)
    return render(request, "my_garage/estate/dashboard.html", context)


@login_required
def beneficiary_list(request: HttpRequest) -> HttpResponse:
    beneficiaries = Beneficiary.objects.filter(owner=request.user)
    form = BeneficiaryForm()
    return render(
        request,
        "my_garage/estate/beneficiary_list.html",
        {"beneficiaries": beneficiaries, "form": form},
    )


@login_required
def beneficiary_create(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("estate:beneficiary_list")
    form = BeneficiaryForm(request.POST)
    if form.is_valid():
        beneficiary = form.save(commit=False)
        beneficiary.owner = request.user
        beneficiary.save()
        messages.success(request, f'Beneficiary "{beneficiary.name}" added.')
        return redirect("estate:beneficiary_list")
    beneficiaries = Beneficiary.objects.filter(owner=request.user)
    return render(
        request,
        "my_garage/estate/beneficiary_list.html",
        {"beneficiaries": beneficiaries, "form": form},
    )


@login_required
def beneficiary_delete(request: HttpRequest, pk: int) -> HttpResponse:
    beneficiary = get_object_or_404(Beneficiary, pk=pk)
    if beneficiary.owner != request.user:
        raise Http404
    if request.method == "POST":
        name = beneficiary.name
        beneficiary.delete()
        messages.success(request, f'Beneficiary "{name}" removed.')
        return redirect("estate:beneficiary_list")
    return render(
        request,
        "my_garage/estate/beneficiary_confirm_delete.html",
        {"beneficiary": beneficiary},
    )


@login_required
def executor_view(request: HttpRequest) -> HttpResponse:
    executor = EstateExecutor.objects.filter(owner=request.user).first()

    if request.method == "POST":
        form = EstateExecutorForm(request.POST, instance=executor)
        if form.is_valid():
            exec_obj = form.save(commit=False)
            exec_obj.owner = request.user
            exec_obj.save()
            messages.success(request, "Executor designated successfully.")
            return redirect("estate:executor")
    else:
        form = EstateExecutorForm(instance=executor)

    return render(
        request,
        "my_garage/estate/executor.html",
        {"executor": executor, "form": form},
    )


@login_required
def executor_remove(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("estate:executor")
    executor = EstateExecutor.objects.filter(owner=request.user).first()
    if executor:
        executor.delete()
        messages.success(request, "Executor removed.")
    return redirect("estate:executor")


@login_required
def item_assign(
    request: HttpRequest, collection_slug: str, item_id: int
) -> HttpResponse:
    """Create or update the estate assignment for a collection item."""
    from my_garage.models import CollectionType

    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )
    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )

    if request.method != "POST":
        return redirect(
            "collections:collection_item_detail",
            collection_slug=collection_slug,
            item_id=item_id,
        )

    existing = get_item_estate_assignment(item, request.user)
    form = BeneficiaryAssignmentForm(
        request.POST, instance=existing, owner=request.user
    )
    if form.is_valid():
        assign_beneficiary(
            item=item,
            beneficiary=form.cleaned_data["beneficiary"],
            note=form.cleaned_data["conditional_note"],
            is_charitable=form.cleaned_data["is_charitable"],
            charitable_org=form.cleaned_data["charitable_org"],
            user=request.user,
        )
        messages.success(request, "Estate assignment saved.")
    else:
        messages.error(request, "Could not save assignment — please check the form.")

    return redirect(
        "collections:collection_item_detail",
        collection_slug=collection_slug,
        item_id=item_id,
    )


@login_required
def item_assign_remove(
    request: HttpRequest, collection_slug: str, item_id: int
) -> HttpResponse:
    """Remove the estate assignment for a collection item."""
    from my_garage.models import CollectionType

    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user
    )
    item = get_object_or_404(
        DynamicCollectionItem,
        id=item_id,
        collection_type=collection_type,
        owner=request.user,
    )

    if request.method == "POST":
        remove_beneficiary_assignment(item, request.user)
        messages.success(request, "Estate assignment removed.")

    return redirect(
        "collections:collection_item_detail",
        collection_slug=collection_slug,
        item_id=item_id,
    )


@login_required
def estate_activate(request: HttpRequest) -> HttpResponse:
    executor = EstateExecutor.objects.filter(owner=request.user).first()
    can_activate = executor is not None

    if request.method == "POST" and can_activate:
        form = EstateActivateForm(request.POST)
        if form.is_valid():
            raw_token = activate_estate_plan(request.user)
            request.session["estate_activation_token"] = raw_token
            return redirect("estate:activate_success")
    else:
        form = EstateActivateForm()

    return render(
        request,
        "my_garage/estate/activate.html",
        {"form": form, "executor": executor, "can_activate": can_activate},
    )


@login_required
def estate_activate_success(request: HttpRequest) -> HttpResponse:
    raw_token = request.session.pop("estate_activation_token", None)
    if raw_token is None:
        return redirect("estate:activate")
    return render(
        request,
        "my_garage/estate/activate_success.html",
        {"raw_token": raw_token},
    )


@login_required
def assign_overview(request: HttpRequest) -> HttpResponse:
    """List all collection items with their current estate assignment status."""
    items = (
        DynamicCollectionItem.objects.filter(owner=request.user)
        .select_related("collection_type", "estate_assignment__beneficiary")
        .order_by("collection_type__name", "name")
    )
    return render(
        request,
        "my_garage/estate/assign_overview.html",
        {"items": items},
    )
