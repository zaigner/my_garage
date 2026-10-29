"""Estate & Legacy views."""

import secrets
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseNotFound
from django.middleware.csrf import rotate_token
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import add_never_cache_headers
from django.views.decorators.cache import never_cache
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
    require_safe,
)
from django.views.static import serve as static_serve

from my_garage.api.selectors import (
    get_beneficiary_assignment,
    get_beneficiary_assignments,
    get_beneficiary_item_detail_context,
    get_beneficiary_session_link,
    get_claimable_beneficiary_link,
    get_estate_assign_items,
    get_estate_dashboard_context,
    get_executor_access_status,
    get_executor_beneficiary,
    get_executor_beneficiary_links,
    get_executor_item,
    get_executor_item_detail_context,
    get_executor_link_beneficiary,
    get_executor_portfolio_context,
    get_item_estate_assignment,
)
from my_garage.api.services import (
    activate_estate_plan,
    assign_beneficiary,
    claim_beneficiary_link,
    hash_executor_code,
    issue_beneficiary_link,
    log_estate_access,
    remove_beneficiary_assignment,
    revoke_beneficiary_link,
    revoke_executor_access,
    save_executor,
    verify_executor_code,
)
from my_garage.forms import (
    BeneficiaryAssignmentForm,
    BeneficiaryForm,
    EstateActivateForm,
    EstateExecutorForm,
    ExecutorCodeForm,
)
from my_garage.models import (
    Beneficiary,
    BeneficiaryAccessLink,
    DynamicCollectionItem,
    EstateAccessToken,
    EstateExecutor,
)

EXECUTOR_OWNER_KEY = "estate_executor_owner_id"
EXECUTOR_TOKEN_KEY = "estate_executor_token_id"
EXECUTOR_SESSION_DAYS = 30
GENERIC_CODE_ERROR = "Invalid access code. Please contact the estate owner."
# The raw code rides to the success page in a signed cookie, never the session
ACTIVATION_COOKIE = "estate_activation_code"
ACTIVATION_COOKIE_SALT = "my_garage.estate.activate_success"
ACTIVATION_COOKIE_MAX_AGE = 600  # seconds
LINK_COOKIE = "estate_beneficiary_link"
LINK_COOKIE_SALT = "my_garage.estate.beneficiary_link_issued"
LINK_COOKIE_MAX_AGE = 600  # seconds
# Beneficiary session keys; executor and Django auth keys are never touched
BENEFICIARY_LINK_KEY = "estate_beneficiary_link_id"
BENEFICIARY_OWNER_KEY = "estate_beneficiary_owner_id"
BENEFICIARY_SESSION_DAYS = 30


def executor_required(view):
    """Require a valid executor session; the token is re-checked every request."""

    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs):
        owner_id = request.session.get(EXECUTOR_OWNER_KEY)
        token_id = request.session.get(EXECUTOR_TOKEN_KEY)
        token = None
        if owner_id is not None and token_id is not None:
            token = (
                EstateAccessToken.objects.filter(pk=token_id, owner_id=owner_id)
                .select_related("owner")
                .first()
            )
        if token is None or not token.is_usable(timezone.now()):
            request.session.pop(EXECUTOR_OWNER_KEY, None)
            request.session.pop(EXECUTOR_TOKEN_KEY, None)
            # Leave a live beneficiary session's 30-day expiry alone
            if BENEFICIARY_LINK_KEY not in request.session:
                request.session.set_expiry(None)
            if owner_id is not None or token_id is not None:
                messages.error(request, GENERIC_CODE_ERROR)
            return redirect("estate:portal_code_entry")
        request.estate_owner = token.owner
        request.estate_token = token
        request.session.set_expiry(timedelta(days=EXECUTOR_SESSION_DAYS))
        return never_cache(view)(request, *args, **kwargs)

    return wrapper


@never_cache
def portal_code_entry(request: HttpRequest) -> HttpResponse:
    """Public executor code-entry page."""
    if request.method == "POST":
        form = ExecutorCodeForm(request.POST)
        if form.is_valid():
            token = verify_executor_code(form.cleaned_data["code"], request=request)
            if token is not None:
                request.session.cycle_key()
                rotate_token(request)
                request.session[EXECUTOR_OWNER_KEY] = token.owner_id
                request.session[EXECUTOR_TOKEN_KEY] = token.pk
                request.session.set_expiry(timedelta(days=EXECUTOR_SESSION_DAYS))
                return redirect("estate:portal_dashboard")
            form.add_error("code", GENERIC_CODE_ERROR)
    else:
        form = ExecutorCodeForm()
    return render(request, "my_garage/estate/portal/code_entry.html", {"form": form})


@require_safe
@executor_required
def portal_dashboard(request: HttpRequest) -> HttpResponse:
    """Read-only portfolio overview for the executor."""
    owner = request.estate_owner
    token = request.estate_token
    context = get_executor_portfolio_context(owner, token)
    context["owner"] = owner
    context["activated_at"] = token.issued_at
    context["beneficiary_links"] = get_executor_beneficiary_links(owner, token)
    response = render(request, "my_garage/estate/portal/dashboard.html", context)
    # Log only a page the executor actually received; HEAD carries no page
    if request.method == "GET":
        log_estate_access(owner, "PORTAL_VIEW", token=token, request=request)
    return response


def _eligible_beneficiary_or_404(request: HttpRequest, pk: int) -> Beneficiary:
    beneficiary = get_executor_beneficiary(request.estate_owner, pk)
    if beneficiary is None:
        raise Http404
    return beneficiary


def _link_beneficiary_or_404(request: HttpRequest, pk: int) -> Beneficiary:
    """A designated or link-holding beneficiary, so an emptied one's link can
    still be revoked or shown once."""
    beneficiary = get_executor_link_beneficiary(
        request.estate_owner, request.estate_token, pk
    )
    if beneficiary is None:
        raise Http404
    return beneficiary


@require_POST
@executor_required
def portal_link_issue(request: HttpRequest, pk: int) -> HttpResponse:
    """Issue a beneficiary claim link; the raw URL rides in a one-shot cookie."""
    beneficiary = _eligible_beneficiary_or_404(request, pk)
    raw = issue_beneficiary_link(beneficiary, request.estate_token, request=request)
    issued_path = reverse("estate:portal_link_issued", args=[beneficiary.pk])
    response = redirect(issued_path)
    response.set_signed_cookie(
        LINK_COOKIE,
        raw,
        salt=LINK_COOKIE_SALT,
        # No max_age: a browser-session cookie never written to disk.
        # get_signed_cookie enforces the 10-minute lifetime instead.
        httponly=True,
        secure=settings.SESSION_COOKIE_SECURE,
        samesite="Strict",
        path=issued_path,
    )
    return response


@require_POST
@executor_required
def portal_link_revoke(request: HttpRequest, pk: int) -> HttpResponse:
    """Revoke a beneficiary's active link."""
    beneficiary = _link_beneficiary_or_404(request, pk)
    if revoke_beneficiary_link(beneficiary, request.estate_token, request=request):
        messages.success(request, f"Link revoked for {beneficiary.name}.")
    else:
        messages.info(request, "No active link.")
    return redirect("estate:portal_dashboard")


@require_GET
@executor_required
def portal_link_issued(request: HttpRequest, pk: int) -> HttpResponse:
    """Show a freshly issued claim URL at most once."""
    issued_path = reverse("estate:portal_link_issued", args=[pk])
    try:
        response = _link_issued_response(request, pk)
    except Http404:
        response = HttpResponseNotFound()
    response.delete_cookie(LINK_COOKIE, path=issued_path, samesite="Strict")
    return response


def _link_issued_response(request: HttpRequest, pk: int) -> HttpResponse:
    beneficiary = _link_beneficiary_or_404(request, pk)
    raw = request.get_signed_cookie(
        LINK_COOKIE, default=None, salt=LINK_COOKIE_SALT, max_age=LINK_COOKIE_MAX_AGE
    )
    link = None
    if raw is not None:
        link = BeneficiaryAccessLink.objects.filter(
            beneficiary=beneficiary,
            is_active=True,
            issued_by_token=request.estate_token,
        ).first()
    if link is None or not secrets.compare_digest(
        hash_executor_code(raw), link.link_token_hash
    ):
        messages.info(
            request,
            "A link can only be shown once. Issue a new link to get one.",
        )
        return redirect("estate:portal_dashboard")
    claim_path = reverse("estate:beneficiary_claim", args=[raw])
    if settings.PUBLIC_BASE_URL:
        claim_url = settings.PUBLIC_BASE_URL.rstrip("/") + claim_path
    else:
        claim_url = request.build_absolute_uri(claim_path)
    return render(
        request,
        "my_garage/estate/portal/link_issued.html",
        {"beneficiary": beneficiary, "claim_url": claim_url, "link": link},
    )


def _beneficiary_not_found(request: HttpRequest) -> HttpResponse:
    """The same uncached 404 for every dead link or session: no hints."""
    response = render(
        request, "my_garage/estate/beneficiary/not_found.html", status=404
    )
    add_never_cache_headers(response)
    return response


def beneficiary_required(view):
    """Require a claimed, still-valid beneficiary link; re-checked every request."""

    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs):
        link_id = request.session.get(BENEFICIARY_LINK_KEY)
        owner_id = request.session.get(BENEFICIARY_OWNER_KEY)
        link = None
        if link_id is not None and owner_id is not None:
            link = get_beneficiary_session_link(link_id, owner_id)
        if link is None:
            had_session = link_id is not None or owner_id is not None
            request.session.pop(BENEFICIARY_LINK_KEY, None)
            request.session.pop(BENEFICIARY_OWNER_KEY, None)
            # Leave a live executor session's 30-day expiry alone
            if had_session and EXECUTOR_TOKEN_KEY not in request.session:
                request.session.set_expiry(None)
            return _beneficiary_not_found(request)
        request.beneficiary_link = link
        request.session.set_expiry(timedelta(days=BENEFICIARY_SESSION_DAYS))
        return never_cache(view)(request, *args, **kwargs)

    return wrapper


@never_cache
@require_http_methods(["GET", "HEAD", "POST"])
def beneficiary_claim(request: HttpRequest, token: str) -> HttpResponse:
    """
    GET shows a confirm page and changes nothing, so link previews can't use
    the link up. The POST claims it once and starts the beneficiary session.
    """
    link_hash = hash_executor_code(token)
    # Reopening your own claimed link (e.g. from the email) goes to the portal;
    # any other reuse stays the same 404
    session_link_id = request.session.get(BENEFICIARY_LINK_KEY)
    session_owner_id = request.session.get(BENEFICIARY_OWNER_KEY)
    if session_link_id is not None and session_owner_id is not None:
        own = get_beneficiary_session_link(session_link_id, session_owner_id)
        if own is not None and secrets.compare_digest(own.link_token_hash, link_hash):
            return redirect("estate:beneficiary_portal")
    if request.method != "POST":
        link = get_claimable_beneficiary_link(link_hash, timezone.now())
        if link is None:
            return _beneficiary_not_found(request)
        return render(
            request, "my_garage/estate/beneficiary/claim.html", {"owner": link.owner}
        )
    link = claim_beneficiary_link(token, request=request)
    if link is None:
        return _beneficiary_not_found(request)
    request.session.cycle_key()
    rotate_token(request)
    request.session[BENEFICIARY_LINK_KEY] = link.pk
    request.session[BENEFICIARY_OWNER_KEY] = link.owner_id
    request.session.set_expiry(timedelta(days=BENEFICIARY_SESSION_DAYS))
    return redirect("estate:beneficiary_portal")


@require_safe
@beneficiary_required
def beneficiary_portal(request: HttpRequest) -> HttpResponse:
    """The beneficiary's designated items, and nothing else of the estate."""
    link = request.beneficiary_link
    response = render(
        request,
        "my_garage/estate/beneficiary/portal.html",
        {
            "beneficiary": link.beneficiary,
            "owner": link.owner,
            "assignments": get_beneficiary_assignments(link),
        },
    )
    # Log only a page the beneficiary actually received; HEAD carries no page
    if request.method == "GET":
        log_estate_access(
            link.owner,
            "BENEFICIARY_VIEW",
            token=link.issued_by_token,
            request=request,
            beneficiary=link.beneficiary,
        )
    return response


@require_safe
@beneficiary_required
def beneficiary_item_detail(request: HttpRequest, item_id: int) -> HttpResponse:
    """Read-only detail of one item designated to the session beneficiary."""
    link = request.beneficiary_link
    context = get_beneficiary_item_detail_context(link, item_id)
    if context is None:
        return _beneficiary_not_found(request)
    response = render(request, "my_garage/estate/beneficiary/item_detail.html", context)
    if request.method == "GET":
        log_estate_access(
            link.owner,
            "BENEFICIARY_VIEW",
            token=link.issued_by_token,
            item=context["item"],
            request=request,
            beneficiary=link.beneficiary,
        )
    return response


@require_safe
@beneficiary_required
def beneficiary_item_photo(request: HttpRequest, item_id: int) -> HttpResponse:
    """Serve a designated item's photo to its beneficiary (serve_media: owner-only)."""
    assignment = get_beneficiary_assignment(request.beneficiary_link, item_id)
    if assignment is None or not assignment.item.photo:
        return _beneficiary_not_found(request)
    try:
        response = static_serve(
            request, assignment.item.photo.name, document_root=settings.MEDIA_ROOT
        )
    except Http404:
        return _beneficiary_not_found(request)
    response["Cache-Control"] = "private, no-store"
    return response


@require_safe
@executor_required
def portal_item_detail(request: HttpRequest, item_id: int) -> HttpResponse:
    """Read-only detail of one item in the executor's estate."""
    owner = request.estate_owner
    token = request.estate_token
    context = get_executor_item_detail_context(owner, token, item_id)
    if context is None:
        raise Http404
    response = render(request, "my_garage/estate/portal/item_detail.html", context)
    if request.method == "GET":
        log_estate_access(
            owner, "ITEM_VIEW", token=token, item=context["item"], request=request
        )
    return response


@require_safe
@executor_required
def portal_item_photo(request: HttpRequest, item_id: int) -> HttpResponse:
    """Serve an owned item's photo to the executor (serve_media is owner-only)."""
    item = get_executor_item(request.estate_owner, item_id)
    if item is None or not item.photo:
        raise Http404
    response = static_serve(request, item.photo.name, document_root=settings.MEDIA_ROOT)
    response["Cache-Control"] = "private, no-store"
    return response


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
            if save_executor(request.user, form, request=request):
                messages.success(
                    request,
                    "Executor updated. Their previous access code has been "
                    "revoked, and beneficiary links issued under it no longer "
                    "work — issue a new code from Activate Estate Access.",
                )
            else:
                messages.success(request, "Executor designated successfully.")
            return redirect("estate:executor")
    else:
        form = EstateExecutorForm(instance=executor)

    # The Update form warns before a name change revokes this code. It matches
    # what save_executor revokes: any token still flagged active.
    token = get_executor_access_status(request.user)["token"] if executor else None
    has_active_code = token is not None and token.is_active
    if has_active_code:
        form.fields["name"].widget.attrs["aria-describedby"] = "executor-name-hint"
    return render(
        request,
        "my_garage/estate/executor.html",
        {"executor": executor, "form": form, "has_active_code": has_active_code},
    )


@login_required
def executor_remove(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("estate:executor")
    revoked = revoke_executor_access(request.user, request=request)
    executor = EstateExecutor.objects.filter(owner=request.user).first()
    if executor:
        executor.delete()
        messages.success(
            request,
            "Executor removed. Their access code has been revoked, and "
            "beneficiary links issued under it no longer work."
            if revoked
            else "Executor removed.",
        )
    return redirect("estate:executor")


@login_required
def item_assign(
    request: HttpRequest, collection_slug: str, item_id: int
) -> HttpResponse:
    """Create or update the estate assignment for a collection item."""
    from my_garage.models import CollectionType

    # Soft-deleted collections are out of the estate
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user, is_active=True
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

    # Soft-deleted collections are out of the estate
    collection_type = get_object_or_404(
        CollectionType, slug=collection_slug, owner=request.user, is_active=True
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
            raw_token = activate_estate_plan(request.user, request=request)
            response = redirect("estate:activate_success")
            response.set_signed_cookie(
                ACTIVATION_COOKIE,
                raw_token,
                salt=ACTIVATION_COOKIE_SALT,
                # No max_age: a browser-session cookie never written to disk.
                # get_signed_cookie enforces the 10-minute lifetime instead.
                httponly=True,
                secure=settings.SESSION_COOKIE_SECURE,
                samesite="Strict",
                path=reverse("estate:activate_success"),
            )
            return response
    else:
        form = EstateActivateForm()

    return render(
        request,
        "my_garage/estate/activate.html",
        {
            "form": form,
            "executor": executor,
            "can_activate": can_activate,
            "access": get_executor_access_status(request.user),
        },
    )


@login_required
def estate_revoke_access(request: HttpRequest) -> HttpResponse:
    if request.method != "POST":
        return redirect("estate:activate")
    if revoke_executor_access(request.user, request=request):
        messages.success(
            request,
            "Executor access revoked. Beneficiary links issued under the code "
            "no longer work.",
        )
    else:
        messages.info(request, "No active access code.")
    return redirect("estate:activate")


@never_cache
@login_required
def estate_activate_success(request: HttpRequest) -> HttpResponse:
    response = _activate_success_response(request)
    # Show the code at most once: the cookie goes on every response
    response.delete_cookie(
        ACTIVATION_COOKIE,
        path=reverse("estate:activate_success"),
        samesite="Strict",
    )
    return response


def _activate_success_response(request: HttpRequest) -> HttpResponse:
    # A bad signature or a cookie older than max_age reads as missing
    raw_token = request.get_signed_cookie(
        ACTIVATION_COOKIE,
        default=None,
        salt=ACTIVATION_COOKIE_SALT,
        max_age=ACTIVATION_COOKIE_MAX_AGE,
    )
    if raw_token is None:
        messages.info(
            request,
            "An access code can only be shown once. Issue a new code to get one.",
        )
        return redirect("estate:activate")
    token = get_executor_access_status(request.user)["token"]
    if token is None or not token.is_active:
        messages.info(request, "That access code is no longer active.")
        return redirect("estate:activate")
    if not secrets.compare_digest(hash_executor_code(raw_token), token.token_hash):
        # e.g. a double submit: never show a code that was already replaced
        messages.info(
            request,
            "A newer access code was issued, so that one is no longer valid. "
            "Issue a new code to see one.",
        )
        return redirect("estate:activate")
    # The executor is outside the LAN, so prefer the public URL over the request host
    portal_path = reverse("estate:portal_code_entry")
    if settings.PUBLIC_BASE_URL:
        portal_url = settings.PUBLIC_BASE_URL.rstrip("/") + portal_path
    else:
        portal_url = request.build_absolute_uri(portal_path)
    return render(
        request,
        "my_garage/estate/activate_success.html",
        {
            "raw_token": raw_token,
            "expires_at": token.expires_at,
            "portal_url": portal_url,
        },
    )


@login_required
def assign_overview(request: HttpRequest) -> HttpResponse:
    """List all collection items with their current estate assignment status."""
    return render(
        request,
        "my_garage/estate/assign_overview.html",
        {"items": get_estate_assign_items(request.user)},
    )
