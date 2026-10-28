"""Unit tests for Story 3.3: beneficiary link services and selectors."""

from __future__ import annotations

import hashlib
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from my_garage.api.selectors import (
    get_executor_beneficiary,
    get_executor_beneficiary_links,
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
    return User.objects.create_user(username="link_owner", password="pass")


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


@pytest.fixture
def token(owner):
    activate_estate_plan(owner)
    return EstateAccessToken.objects.get(owner=owner, is_active=True)


def _beneficiary(owner, name, ct=None, charitable=False, items=1):
    b = Beneficiary.objects.create(owner=owner, name=name, relationship="Child")
    for i in range(items if ct is not None else 0):
        item = DynamicCollectionItem.objects.create(
            owner=owner, collection_type=ct, name=f"{name} item {i}"
        )
        BeneficiaryAssignment.objects.create(
            item=item,
            beneficiary=b,
            is_charitable=charitable,
            charitable_org="Org" if charitable else "",
        )
    return b


@pytest.fixture
def ann(owner, cars):
    return _beneficiary(owner, "Ann", cars, items=2)


class TestIssueRevoke:
    def test_issue_stores_only_hash(self, ann, token):
        raw = issue_beneficiary_link(ann, token)
        link = BeneficiaryAccessLink.objects.get()
        assert link.link_token_hash == hashlib.sha256(raw.encode()).hexdigest()
        assert raw not in link.link_token_hash
        assert link.is_active and link.claimed_at is None
        assert link.issued_by_token == token and link.owner == ann.owner
        delta = link.expires_at - timezone.now()
        assert timedelta(days=6, hours=23) < delta <= timedelta(days=7)
        log = EstateAccessLog.objects.get(event="LINK_ISSUED")
        assert log.beneficiary_name == "Ann"

    def test_reissue_deactivates_previous(self, ann, token):
        first = issue_beneficiary_link(ann, token)
        second = issue_beneficiary_link(ann, token)
        assert first != second
        links = BeneficiaryAccessLink.objects.order_by("pk")
        assert [link.is_active for link in links] == [False, True]
        assert EstateAccessLog.objects.filter(event="LINK_REVOKED").count() == 1
        assert EstateAccessLog.objects.filter(event="LINK_ISSUED").count() == 2

    def test_revoke(self, ann, token):
        issue_beneficiary_link(ann, token)
        assert revoke_beneficiary_link(ann, token) is True
        assert not BeneficiaryAccessLink.objects.get().is_active
        log = EstateAccessLog.objects.get(event="LINK_REVOKED")
        assert log.beneficiary_name == "Ann"
        assert revoke_beneficiary_link(ann, token) is False
        assert EstateAccessLog.objects.filter(event="LINK_REVOKED").count() == 1

    def test_log_keeps_name_after_beneficiary_deleted(self, ann, token):
        issue_beneficiary_link(ann, token)
        ann.delete()
        assert (
            EstateAccessLog.objects.get(event="LINK_ISSUED").beneficiary_name == "Ann"
        )


class TestEligibility:
    def test_only_designated_non_charitable_active(self, owner, cars, token):
        a = _beneficiary(owner, "A", cars, items=2)
        b = _beneficiary(owner, "B", cars, charitable=True)
        gone = CollectionType.objects.create(owner=owner, name="Gone")
        c = _beneficiary(owner, "C", gone)
        gone.is_active = False
        gone.save()
        rows = get_executor_beneficiary_links(owner, token)
        assert [r["beneficiary"] for r in rows] == [a]
        assert rows[0]["item_count"] == 2
        assert get_executor_beneficiary(owner, a.pk) == a
        assert get_executor_beneficiary(owner, b.pk) is None
        assert get_executor_beneficiary(owner, c.pk) is None

    def test_other_owner_is_none(self, owner, ann):
        other = User.objects.create_user(username="other", password="pass")
        assert get_executor_beneficiary(other, ann.pk) is None


class TestStatus:
    def _status(self, owner, token):
        return get_executor_beneficiary_links(owner, token)[0]["status"]

    def test_none(self, owner, ann, token):
        assert self._status(owner, token) == "none"

    def test_issued(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        assert self._status(owner, token) == "issued"

    def test_opened(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        BeneficiaryAccessLink.objects.update(claimed_at=timezone.now())
        assert self._status(owner, token) == "opened"

    def test_revoked(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        revoke_beneficiary_link(ann, token)
        assert self._status(owner, token) == "revoked"

    def test_expired(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        BeneficiaryAccessLink.objects.update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        assert self._status(owner, token) == "expired"

    def test_inactive_beats_claimed(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        BeneficiaryAccessLink.objects.update(claimed_at=timezone.now(), is_active=False)
        assert self._status(owner, token) == "revoked"

    def test_earlier_activation_ignored(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        activate_estate_plan(owner)
        new = EstateAccessToken.objects.get(owner=owner, is_active=True)
        assert self._status(owner, new) == "none"

    def test_newest_link_wins(self, owner, ann, token):
        issue_beneficiary_link(ann, token)
        issue_beneficiary_link(ann, token)
        revoke_beneficiary_link(ann, token)
        issue_beneficiary_link(ann, token)
        assert self._status(owner, token) == "issued"

    def test_query_count(self, owner, cars, token, django_assert_num_queries):
        for name in ("A", "B", "C"):
            issue_beneficiary_link(_beneficiary(owner, name, cars), token)
        with django_assert_num_queries(2):
            rows = get_executor_beneficiary_links(owner, token)
            assert [r["status"] for r in rows] == ["issued"] * 3
