"""
Service layer for my_garage.

Vehicle-specific functions were retired in Phase 5. New functions follow
the collection services pattern.
"""

import hashlib
import ipaddress
import logging
import os
import secrets
from datetime import date, timedelta
from typing import Optional

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)


class VehicleServiceError(Exception):
    """Kept for backwards-compatibility; new code should use the collection
    services provider pattern instead."""


def refresh_item_nfp(item) -> None:
    """
    Recalculate and persist net_financial_position and total_cost_basis
    for a DynamicCollectionItem.

    Called synchronously from signal handlers — completes within the
    HTTP request/response cycle. Uses update_fields to avoid a full save.
    """
    from my_garage.api.selectors import get_item_nfp_breakdown

    breakdown = get_item_nfp_breakdown(item)
    item.net_financial_position = breakdown["net_position"]
    item.total_cost_basis = breakdown["cost_basis"]
    item.save(update_fields=["net_financial_position", "total_cost_basis"])


def assign_beneficiary(
    item,
    beneficiary,
    note: str,
    is_charitable: bool,
    charitable_org: str,
    user,
) -> None:
    """
    Create or update the BeneficiaryAssignment for an item and append an
    EstateChangeLog entry. beneficiary may be None when is_charitable=True.
    """
    from my_garage.models import BeneficiaryAssignment, EstateChangeLog

    existing = BeneficiaryAssignment.objects.filter(item=item).first()
    action = "CHANGED" if existing else "ASSIGNED"

    assignment, _ = BeneficiaryAssignment.objects.update_or_create(
        item=item,
        defaults={
            "beneficiary": beneficiary,
            "conditional_note": note,
            "is_charitable": is_charitable,
            "charitable_org": charitable_org,
        },
    )

    if is_charitable:
        beneficiary_name = charitable_org or "Charitable org"
    elif beneficiary:
        beneficiary_name = beneficiary.name
    else:
        beneficiary_name = ""

    EstateChangeLog.objects.create(
        owner=user,
        action=action,
        item_name=item.name,
        beneficiary_name=beneficiary_name,
    )


def client_ip(request) -> Optional[str]:
    """
    Best-effort client IP for the access log. Informational only — never use
    it for an access decision (headers are spoofable on the LAN path).
    """
    if request is None:
        return None
    meta = request.META
    candidates = [meta.get("HTTP_CF_CONNECTING_IP", "")]
    xff = meta.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        candidates.append(xff.split(",")[0])
    candidates.append(meta.get("REMOTE_ADDR", ""))
    for value in candidates:
        value = (value or "").strip()
        if not value:
            continue
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            continue
    return None


def log_estate_access(
    owner, event, token=None, item=None, request=None, beneficiary=None
):
    """Append an EstateAccessLog row."""
    from my_garage.models import EstateAccessLog

    return EstateAccessLog.objects.create(
        owner=owner,
        token=token,
        event=event,
        item=item,
        item_name=item.name if item is not None else "",
        beneficiary_name=beneficiary.name if beneficiary is not None else "",
        ip_address=client_ip(request),
    )


def hash_executor_code(raw_code: str) -> str:
    """SHA-256 hex digest of a raw executor code, as stored in token_hash."""
    return hashlib.sha256(raw_code.encode()).hexdigest()


def verify_executor_code(raw_code: str, request=None):
    """
    Validate a raw executor code. Returns the (updated) token on success, or
    None. A match against a revoked/expired token logs CODE_REJECTED; an
    unknown code logs nothing.
    """
    from my_garage.models import EstateAccessToken

    code_hash = hash_executor_code((raw_code or "").strip())
    with transaction.atomic():
        candidate = EstateAccessToken.objects.filter(token_hash=code_hash).first()
        if candidate is None:
            return None
        # Lock all of the owner's tokens, then re-read the candidate.
        list(
            EstateAccessToken.objects.select_for_update().filter(
                owner_id=candidate.owner_id
            )
        )
        token = EstateAccessToken.objects.filter(pk=candidate.pk).first()
        if token is None:
            return None
        now = timezone.now()
        if not secrets.compare_digest(token.token_hash, code_hash):
            return None
        if not token.is_usable(now):
            log_estate_access(
                token.owner, "CODE_REJECTED", token=token, request=request
            )
            return None
        EstateAccessToken.objects.filter(pk=token.pk).update(
            use_count=F("use_count") + 1, last_used_at=now, expires_at=None
        )
        token.refresh_from_db()
        log_estate_access(token.owner, "CODE_ACCEPTED", token=token, request=request)
        return token


def _deactivate_active_tokens(user, request=None) -> int:
    """Deactivate the owner's active tokens, logging each. Call inside atomic."""
    from my_garage.models import EstateAccessToken

    active = list(
        EstateAccessToken.objects.select_for_update().filter(owner=user, is_active=True)
    )
    ids = [t.pk for t in active]
    if ids:
        EstateAccessToken.objects.filter(pk__in=ids).update(is_active=False)
        for t in active:
            log_estate_access(user, "TOKEN_REVOKED", token=t, request=request)
    return len(ids)


def revoke_executor_access(user, request=None) -> bool:
    """Revoke the owner's active executor code. True if one was active."""
    with transaction.atomic():
        return _deactivate_active_tokens(user, request=request) > 0


BENEFICIARY_LINK_DAYS = 7


def _deactivate_active_links(beneficiary, request=None) -> int:
    """
    Deactivate the beneficiary's active links, logging each under the token
    that issued it. Call inside atomic.
    """
    from my_garage.models import BeneficiaryAccessLink

    active = list(
        BeneficiaryAccessLink.objects.select_for_update().filter(
            beneficiary=beneficiary, is_active=True
        )
    )
    ids = [link.pk for link in active]
    if ids:
        BeneficiaryAccessLink.objects.filter(pk__in=ids).update(is_active=False)
        for link in active:
            log_estate_access(
                beneficiary.owner,
                "LINK_REVOKED",
                token=link.issued_by_token,
                request=request,
                beneficiary=beneficiary,
            )
    return len(ids)


def issue_beneficiary_link(beneficiary, token, request=None) -> str:
    """
    Issue a claim link for a beneficiary. Returns the raw link token once; only
    its SHA-256 hash is stored. Any previous active link is deactivated in the
    same transaction (LINK_REVOKED logged). Expires after 7 days if unopened.
    """
    from my_garage.models import Beneficiary, BeneficiaryAccessLink

    raw = secrets.token_urlsafe(32)
    with transaction.atomic():
        # Lock the beneficiary row: locking zero active links locks nothing
        Beneficiary.objects.select_for_update().get(pk=beneficiary.pk)
        _deactivate_active_links(beneficiary, request=request)
        BeneficiaryAccessLink.objects.create(
            beneficiary=beneficiary,
            owner=beneficiary.owner,
            issued_by_token=token,
            link_token_hash=hash_executor_code(raw),
            expires_at=timezone.now() + timedelta(days=BENEFICIARY_LINK_DAYS),
        )
        log_estate_access(
            beneficiary.owner,
            "LINK_ISSUED",
            token=token,
            request=request,
            beneficiary=beneficiary,
        )
    return raw


def revoke_beneficiary_link(beneficiary, token, request=None) -> bool:
    """Revoke the beneficiary's active link. True if one was active."""
    from my_garage.models import Beneficiary

    with transaction.atomic():
        Beneficiary.objects.select_for_update().get(pk=beneficiary.pk)
        return _deactivate_active_links(beneficiary, request=request) > 0


def claim_beneficiary_link(raw_token: str, request=None):
    """
    Claim a beneficiary link once. Returns the claimed link, or None when it is
    unknown, already claimed, revoked, expired, or its executor token is no
    longer usable. Failed claims log nothing; a claim logs LINK_CLAIMED.
    """
    from my_garage.api.selectors import get_claimable_beneficiary_link
    from my_garage.models import Beneficiary, BeneficiaryAccessLink

    link_hash = hash_executor_code(raw_token or "")
    candidate = get_claimable_beneficiary_link(link_hash, timezone.now())
    if candidate is None:
        return None
    with transaction.atomic():
        # Same lock as issue/revoke, then re-check: two claims can't both win
        locked = (
            Beneficiary.objects.select_for_update()
            .filter(pk=candidate.beneficiary_id)
            .first()
        )
        if locked is None:  # deleted mid-claim
            return None
        now = timezone.now()
        link = get_claimable_beneficiary_link(link_hash, now)
        if link is None:
            return None
        claimed = BeneficiaryAccessLink.objects.filter(
            pk=link.pk, claimed_at__isnull=True
        ).update(claimed_at=now)
        if not claimed:
            return None
        link.claimed_at = now
        log_estate_access(
            link.owner,
            "LINK_CLAIMED",
            token=link.issued_by_token,
            request=request,
            beneficiary=link.beneficiary,
        )
        return link


def _person_name_key(name: str) -> str:
    """Compare names ignoring case and spacing: "jo  smith" == "Jo Smith"."""
    return " ".join((name or "").split()).casefold()


def save_executor(user, form, request=None) -> bool:
    """
    Save a valid EstateExecutorForm as the owner's executor.

    A different person (name changed, ignoring case and spacing) must not keep
    the previous executor's access code, so it is revoked (TOKEN_REVOKED is
    logged). A contact-only edit or a first designation revokes nothing.
    Returns True if an active code was revoked.
    """
    from my_garage.models import EstateExecutor

    with transaction.atomic():
        previous_name = (
            EstateExecutor.objects.filter(owner=user)
            .values_list("name", flat=True)
            .first()
        )
        executor = form.save(commit=False)
        executor.owner = user
        executor.save()
        replaced = previous_name is not None and (
            _person_name_key(previous_name) != _person_name_key(executor.name)
        )
        return replaced and revoke_executor_access(user, request=request)


def activate_estate_plan(user, request=None) -> str:
    """
    Generate an executor access token and lock a valuation snapshot for all
    portfolio items. Returns the raw token once; only its SHA-256 hash is
    stored (EstateAccessToken.token_hash). The caller must not store it
    server-side (session, database, cache or logs).

    On reactivation, the existing active token is deactivated (not deleted)
    to preserve the audit trail. The new token expires after 72 hours if unused.
    """
    from my_garage.models import (
        DynamicCollectionItem,
        EstateAccessToken,
        ValuationSnapshot,
    )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_executor_code(raw_token)

    # Token swap and snapshots succeed or fail together. Items are read inside
    # the transaction so each snapshot's item still exists at bulk_create.
    today = date.today()
    with transaction.atomic():
        # Lock the owner row first: a first activation has no token rows to
        # lock, so two concurrent ones could both create an active token.
        # NO KEY UPDATE still serialises activations but doesn't block the FK
        # KEY SHARE locks that log/link inserts (e.g. code entry) take on it
        get_user_model().objects.select_for_update(no_key=True).get(pk=user.pk)
        _deactivate_active_tokens(user, request=request)
        new_token = EstateAccessToken.objects.create(
            owner=user,
            token_hash=token_hash,
            is_active=True,
            expires_at=timezone.now() + timedelta(hours=72),
        )
        log_estate_access(user, "TOKEN_ISSUED", token=new_token, request=request)
        snapshots = []
        # Soft-deleted collections are out of the estate
        for item in DynamicCollectionItem.objects.filter(
            owner=user, collection_type__is_active=True
        ):
            mv = item.current_market_value
            cb = item.purchase_price  # raw purchase cost; None when unknown
            eq = (mv - cb) if (mv is not None and cb is not None) else None
            snapshots.append(
                ValuationSnapshot(
                    item=item,
                    item_name=item.name,
                    token=new_token,
                    owner=user,
                    snapshot_date=today,
                    market_value=mv,
                    cost_basis=cb,
                    equity=eq,
                    snapshot_trigger="ESTATE_ACTIVATION",
                )
            )
        ValuationSnapshot.objects.bulk_create(snapshots)

    return raw_token


def remove_beneficiary_assignment(item, user) -> None:
    """Delete the BeneficiaryAssignment for an item and log the removal."""
    from my_garage.models import BeneficiaryAssignment, EstateChangeLog

    assignment = BeneficiaryAssignment.objects.filter(item=item).first()
    if not assignment:
        return

    EstateChangeLog.objects.create(
        owner=user,
        action="REMOVED",
        item_name=item.name,
        beneficiary_name="",
    )
    assignment.delete()


def process_generic_service_record_ocr(record) -> dict:
    """
    Call the FastAPI OCR service for a GenericServiceRecord's receipt image.

    Pre-fills vendor/description/total_cost only when those fields are blank
    so manual edits are never silently overwritten. Sets is_verified=False to
    flag the result for human review.

    Returns the raw OCR dict on success, empty dict on failure.
    """
    if not record.receipt_image:
        return {}

    try:
        image_file = record.receipt_image
        filename = os.path.basename(image_file.name)

        image_file.open("rb")
        image_bytes = image_file.read()
        image_file.close()

        ocr_url = f"{settings.FASTAPI_BASE_URL}/ocr/process"
        response = requests.post(
            ocr_url,
            files={"file": (filename, image_bytes, "image/jpeg")},
            # Gemini (up to 20s) plus a tesseract fallback on a Pi.
            timeout=60,
        )
        response.raise_for_status()
        ocr_data: dict = response.json()

        record.ocr_raw_data = ocr_data

        if not record.vendor and ocr_data.get("vendor"):
            record.vendor = ocr_data["vendor"]
        if not record.description and ocr_data.get("description"):
            record.description = ocr_data["description"]
        if not record.total_cost and ocr_data.get("total_cost"):
            record.total_cost = ocr_data["total_cost"]

        record.is_verified = False
        record.save()

        return ocr_data

    except Exception:
        logger.exception(
            "OCR processing failed for GenericServiceRecord pk=%s", record.pk
        )
        return {}
