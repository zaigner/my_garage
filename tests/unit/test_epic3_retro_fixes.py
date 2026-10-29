"""Unit tests for the Epic 3 retrospective fixes (F1, F2, F5)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone

from my_garage.api.estate_selectors import (
    get_executor_beneficiary,
    get_executor_beneficiary_links,
    get_executor_link_beneficiary,
)
from my_garage.api.services import (
    activate_estate_plan,
    issue_beneficiary_link,
    revoke_beneficiary_link,
)
from my_garage.models import (
    Beneficiary,
    BeneficiaryAccessLink,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateAccessLog,
    EstateAccessToken,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_user(username="retro3_owner", password="pass")


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


@pytest.fixture
def token(owner):
    activate_estate_plan(owner)
    return EstateAccessToken.objects.get(owner=owner, is_active=True)


def _beneficiary(owner, name, ct=None, items=1):
    b = Beneficiary.objects.create(owner=owner, name=name, relationship="Child")
    for i in range(items if ct is not None else 0):
        item = DynamicCollectionItem.objects.create(
            owner=owner, collection_type=ct, name=f"{name} item {i}"
        )
        BeneficiaryAssignment.objects.create(item=item, beneficiary=b)
    return b


def _empty(beneficiary):
    """Make every one of the beneficiary's items charitable."""
    BeneficiaryAssignment.objects.filter(beneficiary=beneficiary).update(
        is_charitable=True, charitable_org="Org"
    )


def _claim_all():
    BeneficiaryAccessLink.objects.filter(is_active=True).update(
        claimed_at=timezone.now()
    )


@pytest.fixture
def ann(owner, cars):
    return _beneficiary(owner, "Ann", cars)


class TestLinkHoldingSelector:
    def test_emptied_claimed_is_link_holding(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        _claim_all()
        _empty(ann)
        assert get_executor_link_beneficiary(owner, token, ann.pk) == ann
        # Issuing still needs a designated item
        assert get_executor_beneficiary(owner, ann.pk) is None

    def test_claimed_after_expiry_is_link_holding(self, owner, ann, token):
        # A claimed session outlives the 7-day unclaimed expiry
        issue_beneficiary_link(ann, token)
        _claim_all()
        BeneficiaryAccessLink.objects.update(
            expires_at=timezone.now() - timedelta(days=1)
        )
        _empty(ann)
        assert get_executor_link_beneficiary(owner, token, ann.pk) == ann
        (row,) = get_executor_beneficiary_links(owner, token)
        assert row["beneficiary"] == ann and row["status"] == "opened"
        assert not row["can_issue"]

    def test_emptied_unclaimed_is_link_holding(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        BeneficiaryAssignment.objects.all().delete()
        assert get_executor_link_beneficiary(owner, token, ann.pk) == ann

    def test_designated_without_link(self, owner, ann, token):
        assert get_executor_link_beneficiary(owner, token, ann.pk) == ann

    def test_never_eligible(self, owner, token):
        b = _beneficiary(owner, "Bob")
        assert get_executor_link_beneficiary(owner, token, b.pk) is None

    def test_old_token_link_only(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        _claim_all()
        _empty(ann)
        activate_estate_plan(owner)
        new = EstateAccessToken.objects.get(owner=owner, is_active=True)
        assert get_executor_link_beneficiary(owner, new, ann.pk) is None

    def test_revoked_link_not_holding(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        revoke_beneficiary_link(ann, token)
        _empty(ann)
        assert get_executor_link_beneficiary(owner, token, ann.pk) is None

    def test_expired_unclaimed_not_holding(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        BeneficiaryAccessLink.objects.update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        _empty(ann)
        assert get_executor_link_beneficiary(owner, token, ann.pk) is None

    def test_other_owner(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        other = User.objects.create_user(username="retro3_other", password="pass")
        assert get_executor_link_beneficiary(other, token, ann.pk) is None


class TestLinkList:
    def test_rows_and_can_issue(self, owner, cars, ann, token):
        bob = _beneficiary(owner, "Bob", cars, items=2)
        _beneficiary(owner, "Cy")  # nothing designated, no link
        issue_beneficiary_link(ann, token)
        _claim_all()
        _empty(ann)
        rows = get_executor_beneficiary_links(owner, token)
        assert [r["beneficiary"] for r in rows] == [ann, bob]
        assert [(r["item_count"], r["can_issue"]) for r in rows] == [
            (0, False),
            (2, True),
        ]
        assert rows[0]["status"] == "opened"
        assert rows[1]["status"] == "none"

    def test_links_do_not_inflate_item_count(self, owner, cars, token):
        b = _beneficiary(owner, "Bea", cars, items=2)
        for _ in range(3):
            issue_beneficiary_link(b, token)
        _claim_all()
        (row,) = get_executor_beneficiary_links(owner, token)
        assert row["item_count"] == 2 and row["can_issue"]

    def test_query_count(self, owner, cars, token, django_assert_num_queries):
        for name in ("A", "B", "C"):
            issue_beneficiary_link(_beneficiary(owner, name, cars), token)
        _claim_all()
        _empty(Beneficiary.objects.get(name="B"))
        with django_assert_num_queries(2):
            rows = get_executor_beneficiary_links(owner, token)
            assert [r["can_issue"] for r in rows] == [True, False, True]


class TestActivationLock:
    def test_owner_lock_comes_first(self, owner):
        calls = []
        user_locks = []
        user_sfu = User.objects.select_for_update
        token_sfu = EstateAccessToken.objects.select_for_update
        token_create = EstateAccessToken.objects.create

        def record(name, real):
            def wrapper(*args, **kwargs):
                calls.append(name)
                return real(*args, **kwargs)

            return wrapper

        def user_lock(*args, **kwargs):
            calls.append("user_lock")
            user_locks.append((connection.in_atomic_block, kwargs))
            return user_sfu(*args, **kwargs)

        with (
            patch.object(User.objects, "select_for_update", user_lock),
            patch.object(
                EstateAccessToken.objects,
                "select_for_update",
                record("token_lock", token_sfu),
            ),
            patch.object(
                EstateAccessToken.objects, "create", record("create", token_create)
            ),
        ):
            activate_estate_plan(owner)
            activate_estate_plan(owner)
        assert calls == ["user_lock", "token_lock", "create"] * 2
        # Held inside the token-swap transaction, as NO KEY UPDATE
        assert user_locks == [(True, {"no_key": True})] * 2
        assert EstateAccessToken.objects.filter(is_active=True).count() == 1


class TestRevokedLogToken:
    def test_reissue_logs_old_links_token(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        activate_estate_plan(owner)
        new = EstateAccessToken.objects.get(owner=owner, is_active=True)
        issue_beneficiary_link(ann, new)
        revoked = EstateAccessLog.objects.get(event="LINK_REVOKED")
        assert revoked.token == token
        issued = EstateAccessLog.objects.filter(event="LINK_ISSUED").order_by("pk")
        assert [log.token for log in issued] == [token, new]

    def test_one_row_per_link_each_with_its_token(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        activate_estate_plan(owner)
        new = EstateAccessToken.objects.get(owner=owner, is_active=True)
        # A second active link (e.g. left over from a race) under the new token
        BeneficiaryAccessLink.objects.create(
            beneficiary=ann,
            owner=owner,
            issued_by_token=new,
            link_token_hash="x" * 64,
            expires_at=timezone.now() + timedelta(days=7),
        )
        assert revoke_beneficiary_link(ann, new) is True
        tokens = {
            log.token for log in EstateAccessLog.objects.filter(event="LINK_REVOKED")
        }
        assert tokens == {token, new}
