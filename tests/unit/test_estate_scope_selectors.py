"""Unit tests for Story 3.2: soft-deleted collections are out of the estate."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from my_garage.api.estate_selectors import (
    get_estate_assign_items,
    get_estate_dashboard_context,
    get_executor_item,
    get_executor_item_detail_context,
    get_executor_portfolio_context,
)
from my_garage.api.services import (
    activate_estate_plan,
    assign_beneficiary,
    save_executor,
)
from my_garage.forms import EstateExecutorForm
from my_garage.models import (
    Beneficiary,
    CollectionType,
    DynamicCollectionItem,
    EstateAccessLog,
    EstateAccessToken,
    EstateExecutor,
    ValuationSnapshot,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_user(username="scope_owner", password="pass")


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


@pytest.fixture
def wines(owner):
    return CollectionType.objects.create(owner=owner, name="Wines")


def _item(owner, ct, name, value=None):
    return DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name, current_market_value=value
    )


def _soft_delete(ct):
    ct.is_active = False
    ct.save()


def _activate(owner):
    activate_estate_plan(owner)
    return EstateAccessToken.objects.get(owner=owner, is_active=True)


@pytest.fixture
def mixed(owner, cars, wines):
    """One item in an active collection, one in a soft-deleted one."""
    kept = _item(owner, cars, "911", Decimal("100"))
    hidden = _item(owner, wines, "Petrus", Decimal("40"))
    _soft_delete(wines)
    return kept, hidden


class TestActivation:
    def test_snapshots_only_active_collection_items(self, owner, mixed):
        kept, _ = mixed
        token = _activate(owner)
        snaps = ValuationSnapshot.objects.filter(owner=owner, token=token)
        assert [s.item_id for s in snaps] == [kept.pk]


class TestOwnerDashboard:
    def test_list_and_totals_exclude_soft_deleted(self, owner, mixed):
        kept, hidden = mixed
        ben = Beneficiary.objects.create(owner=owner, name="Ann")
        for item in (kept, hidden):
            assign_beneficiary(
                item=item,
                beneficiary=ben,
                note="",
                is_charitable=False,
                charitable_org="",
                user=owner,
            )
        ctx = get_estate_dashboard_context(owner)
        assert [i.pk for i in ctx["items"]] == [kept.pk]
        assert ctx["items_total"] == 1
        assert ctx["items_assigned"] == 1
        assert ctx["completeness_pct"] == 100

    def test_query_count(self, owner, mixed, django_assert_num_queries):
        with django_assert_num_queries(3):
            get_estate_dashboard_context(owner)


class TestAssignOverview:
    def test_lists_only_active_collection_items(self, owner, mixed):
        kept, _ = mixed
        assert [i.pk for i in get_estate_assign_items(owner)] == [kept.pk]


class TestExecutorPortfolio:
    def test_soft_deleted_before_activation_not_listed_or_counted(self, owner, mixed):
        kept, _ = mixed
        token = _activate(owner)
        ctx = get_executor_portfolio_context(owner, token)
        assert [r["item"].pk for r in ctx["rows"]] == [kept.pk]
        assert ctx["items_total"] == 1
        assert ctx["unassigned_count"] == 1
        assert ctx["removed_rows"] == [] and ctx["removed_count"] == 0
        assert ctx["snapshot_total"] == Decimal("100")
        assert ctx["snapshot_count"] == 1
        assert ctx["current_total"] == Decimal("100")

    def test_soft_deleted_after_activation_becomes_removed_row(
        self, owner, cars, wines
    ):
        _item(owner, cars, "911", Decimal("100"))
        _item(owner, wines, "Petrus", Decimal("40"))
        token = _activate(owner)
        before = get_executor_portfolio_context(owner, token)
        _soft_delete(wines)

        ctx = get_executor_portfolio_context(owner, token)
        assert ctx["snapshot_total"] == before["snapshot_total"] == Decimal("140")
        assert ctx["snapshot_count"] == 2
        assert [r["item"].name for r in ctx["rows"]] == ["911"]
        assert ctx["removed_rows"] == [
            {
                "item": None,
                "item_name": "Petrus",
                "snapshot_value": Decimal("40"),
                "removed": True,
            }
        ]
        assert ctx["removed_count"] == 1
        assert ctx["items_total"] == 1
        assert ctx["current_total"] == Decimal("100")
        assert ctx["delta"] == Decimal("0") and ctx["compared_count"] == 1

    def test_removed_rows_mix_deleted_and_soft_deleted(self, owner, cars, wines):
        _item(owner, cars, "911", Decimal("100"))
        gone = _item(owner, cars, "Alfa", Decimal("5"))
        _item(owner, wines, "Petrus", Decimal("40"))
        token = _activate(owner)
        gone.delete()
        _soft_delete(wines)
        ctx = get_executor_portfolio_context(owner, token)
        assert [r["item_name"] for r in ctx["removed_rows"]] == ["Alfa", "Petrus"]
        assert ctx["snapshot_total"] == Decimal("145")

    def test_duplicate_snapshots_of_out_of_scope_item_one_row(self, owner, cars, wines):
        hidden = _item(owner, wines, "Petrus", Decimal("40"))
        token = _activate(owner)
        ValuationSnapshot.objects.create(
            item=hidden,
            item_name="Petrus",
            token=token,
            owner=owner,
            snapshot_date=datetime.date.today(),
            market_value=Decimal("45"),
            snapshot_trigger="ESTATE_ACTIVATION",
        )
        _soft_delete(wines)
        ctx = get_executor_portfolio_context(owner, token)
        assert ctx["removed_count"] == 1
        # Newest row wins, as in the detail selector
        assert ctx["removed_rows"][0]["snapshot_value"] == Decimal("45")

    def test_query_count(self, owner, cars, wines, django_assert_num_queries):
        _item(owner, cars, "911", Decimal("100"))
        _item(owner, wines, "Petrus", Decimal("40"))
        token = _activate(owner)
        _soft_delete(wines)
        with django_assert_num_queries(2):
            get_executor_portfolio_context(owner, token)


class TestExecutorItem:
    def test_soft_deleted_item_is_none(self, owner, mixed):
        kept, hidden = mixed
        token = _activate(owner)
        assert get_executor_item(owner, hidden.pk) is None
        assert get_executor_item(owner, kept.pk) == kept
        assert get_executor_item_detail_context(owner, token, hidden.pk) is None

    def test_soft_deleted_after_activation_detail_is_none(self, owner, wines):
        item = _item(owner, wines, "Petrus", Decimal("40"))
        token = _activate(owner)
        _soft_delete(wines)
        assert get_executor_item_detail_context(owner, token, item.pk) is None

    def test_detail_query_count(self, owner, mixed, django_assert_num_queries):
        kept, _ = mixed
        token = _activate(owner)
        with django_assert_num_queries(4):
            get_executor_item_detail_context(owner, token, kept.pk)


def _form(name, contact="", instance=None):
    form = EstateExecutorForm(
        {"name": name, "contact_info": contact}, instance=instance
    )
    assert form.is_valid()
    return form


class TestSaveExecutor:
    @pytest.fixture
    def executor(self, owner):
        return EstateExecutor.objects.create(
            owner=owner, name="Jo Smith", contact_info="jo@x.com"
        )

    def test_name_change_revokes_and_logs(self, owner, executor):
        token = _activate(owner)
        assert save_executor(owner, _form("Sam Lee", instance=executor)) is True
        token.refresh_from_db()
        assert not token.is_active
        assert EstateExecutor.objects.get(owner=owner).name == "Sam Lee"
        assert EstateAccessLog.objects.filter(
            owner=owner, event="TOKEN_REVOKED", token=token
        ).exists()

    @pytest.mark.parametrize("name", ["jo  smith", "  JO SMITH ", "Jo\tSmith"])
    def test_case_and_spacing_keep_code(self, owner, executor, name):
        token = _activate(owner)
        assert save_executor(owner, _form(name, instance=executor)) is False
        token.refresh_from_db()
        assert token.is_active
        assert EstateExecutor.objects.get(owner=owner).name == name.strip()

    def test_contact_only_edit_keeps_code(self, owner, executor):
        token = _activate(owner)
        form = _form("Jo Smith", "new@x.com", instance=executor)
        assert save_executor(owner, form) is False
        token.refresh_from_db()
        assert token.is_active
        assert EstateExecutor.objects.get(owner=owner).contact_info == "new@x.com"

    def test_name_change_without_active_code(self, owner, executor):
        assert save_executor(owner, _form("Sam Lee", instance=executor)) is False
        assert EstateExecutor.objects.get(owner=owner).name == "Sam Lee"
        assert not EstateAccessLog.objects.filter(event="TOKEN_REVOKED").exists()

    def test_first_designation_revokes_nothing(self, owner):
        assert save_executor(owner, _form("Sam Lee")) is False
        assert EstateExecutor.objects.get(owner=owner).name == "Sam Lee"
