"""
Service layer for my_garage.

Vehicle-specific functions were retired in Phase 5. New functions follow
the collection services pattern.
"""

import hashlib
import logging
import os
import secrets
from datetime import date

import requests
from django.conf import settings

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


def activate_estate_plan(user) -> str:
    """
    Generate an executor access token and lock a valuation snapshot for all
    portfolio items. Returns the raw token once — it is never persisted.

    On reactivation, the existing active token is deactivated (not deleted)
    to preserve the audit trail.
    """
    from my_garage.models import (
        DynamicCollectionItem,
        EstateAccessToken,
        ValuationSnapshot,
    )

    # Deactivate any existing active token (OneToOne — at most one row)
    EstateAccessToken.objects.filter(owner=user, is_active=True).update(is_active=False)

    # Generate and hash new token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    EstateAccessToken.objects.create(owner=user, token_hash=token_hash, is_active=True)

    # Bulk-create valuation snapshots for all items — single query
    today = date.today()
    items = DynamicCollectionItem.objects.filter(owner=user)
    snapshots = []
    for item in items:
        mv = item.current_market_value
        cb = item.purchase_price  # raw purchase cost; None when unknown (per spec)
        eq = (mv - cb) if (mv is not None and cb is not None) else None
        snapshots.append(
            ValuationSnapshot(
                item=item,
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
            timeout=30,
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
