"""
Unit tests for get_estate_dashboard_context selector (Story 1.4).

All tests use in-memory SQLite — no I/O beyond the test DB.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from my_garage.api.selectors import get_estate_dashboard_context
from my_garage.models import (
    Beneficiary,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateChangeLog,
    EstateExecutor,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(username="dashboard_user", password="pass")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="other_dashboard", password="pass")


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Watches",
        slug="watches",
        field_schema=[],
    )


@pytest.fixture
def item(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Rolex Submariner",
    )


@pytest.fixture
def item2(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Omega Speedmaster",
    )


@pytest.fixture
def beneficiary(user):
    return Beneficiary.objects.create(
        owner=user,
        name="Jane Doe",
        relationship="Spouse",
    )


@pytest.fixture
def executor(user):
    return EstateExecutor.objects.create(
        owner=user,
        name="John Smith",
        contact_info="john@example.com",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestEstateDashboardSelectorZeroItems:
    def test_zero_items_returns_zero_totals(self, user):
        ctx = get_estate_dashboard_context(user)
        assert ctx["items_total"] == 0
        assert ctx["items_assigned"] == 0

    def test_zero_items_completeness_pct_is_zero_not_error(self, user):
        ctx = get_estate_dashboard_context(user)
        assert ctx["completeness_pct"] == 0

    def test_zero_items_returns_empty_items_list(self, user):
        ctx = get_estate_dashboard_context(user)
        assert ctx["items"] == []

    def test_zero_items_executor_is_none_when_not_designated(self, user):
        ctx = get_estate_dashboard_context(user)
        assert ctx["executor"] is None

    def test_zero_items_recent_log_is_empty(self, user):
        ctx = get_estate_dashboard_context(user)
        assert ctx["recent_log"] == []


class TestEstateDashboardSelectorUnassigned:
    def test_unassigned_items_have_is_assigned_false(self, user, item, item2):
        ctx = get_estate_dashboard_context(user)
        assert all(not i.is_assigned for i in ctx["items"])

    def test_items_assigned_count_is_zero(self, user, item, item2):
        ctx = get_estate_dashboard_context(user)
        assert ctx["items_assigned"] == 0

    def test_items_total_is_correct(self, user, item, item2):
        ctx = get_estate_dashboard_context(user)
        assert ctx["items_total"] == 2

    def test_completeness_pct_is_zero(self, user, item, item2):
        ctx = get_estate_dashboard_context(user)
        assert ctx["completeness_pct"] == 0


class TestEstateDashboardSelectorPartiallyAssigned:
    def test_assigned_item_has_is_assigned_true(self, user, item, item2, beneficiary):
        BeneficiaryAssignment.objects.create(
            item=item,
            beneficiary=beneficiary,
        )
        ctx = get_estate_dashboard_context(user)
        assigned_items = [i for i in ctx["items"] if i.is_assigned]
        assert len(assigned_items) == 1

    def test_items_assigned_count_correct(self, user, item, item2, beneficiary):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        ctx = get_estate_dashboard_context(user)
        assert ctx["items_assigned"] == 1

    def test_completeness_pct_is_50(self, user, item, item2, beneficiary):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        ctx = get_estate_dashboard_context(user)
        assert ctx["completeness_pct"] == 50


class TestEstateDashboardSelectorAllAssigned:
    def test_all_assigned_completeness_is_100(self, user, item, item2, beneficiary):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        BeneficiaryAssignment.objects.create(item=item2, beneficiary=beneficiary)
        ctx = get_estate_dashboard_context(user)
        assert ctx["completeness_pct"] == 100

    def test_all_items_have_is_assigned_true(self, user, item, item2, beneficiary):
        BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
        BeneficiaryAssignment.objects.create(item=item2, beneficiary=beneficiary)
        ctx = get_estate_dashboard_context(user)
        assert all(i.is_assigned for i in ctx["items"])


class TestEstateDashboardSelectorExecutor:
    def test_executor_returned_when_designated(self, user, executor):
        ctx = get_estate_dashboard_context(user)
        assert ctx["executor"] is not None
        assert ctx["executor"].name == "John Smith"

    def test_executor_is_none_when_not_designated(self, user):
        ctx = get_estate_dashboard_context(user)
        assert ctx["executor"] is None


class TestEstateDashboardSelectorRecentLog:
    def test_recent_log_capped_at_10(self, user):
        for i in range(15):
            EstateChangeLog.objects.create(
                owner=user,
                action="ASSIGNED",
                item_name=f"Item {i}",
                beneficiary_name="Jane",
            )
        ctx = get_estate_dashboard_context(user)
        assert len(ctx["recent_log"]) == 10

    def test_recent_log_is_empty_when_no_entries(self, user):
        ctx = get_estate_dashboard_context(user)
        assert ctx["recent_log"] == []

    def test_recent_log_only_shows_owners_entries(self, user, other_user):
        EstateChangeLog.objects.create(
            owner=other_user,
            action="ASSIGNED",
            item_name="Other Item",
            beneficiary_name="Someone",
        )
        ctx = get_estate_dashboard_context(user)
        assert ctx["recent_log"] == []


class TestEstateDashboardSelectorOwnerIsolation:
    def test_items_from_other_user_not_returned(
        self, user, other_user, collection_type
    ):
        other_ct = CollectionType.objects.create(
            owner=other_user, name="Other", slug="other", field_schema=[]
        )
        DynamicCollectionItem.objects.create(
            owner=other_user,
            collection_type=other_ct,
            name="Not Mine",
        )
        ctx = get_estate_dashboard_context(user)
        assert all(i.owner == user for i in ctx["items"])
