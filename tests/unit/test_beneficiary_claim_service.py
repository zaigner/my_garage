"""Unit tests for Story 3.4: beneficiary link claim, session link and isolation."""

from __future__ import annotations

import hashlib
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from my_garage.api.selectors import (
    get_beneficiary_assignments,
    get_beneficiary_session_link,
    get_claimable_beneficiary_link,
    get_executor_access_status,
)
from my_garage.api.services import (
    activate_estate_plan,
    claim_beneficiary_link,
    issue_beneficiary_link,
    log_estate_access,
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
    return User.objects.create_user(username="claim_owner", password="pass")


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


@pytest.fixture
def token(owner):
    activate_estate_plan(owner)
    return EstateAccessToken.objects.get(owner=owner, is_active=True)


def _beneficiary(owner, name):
    return Beneficiary.objects.create(owner=owner, name=name, relationship="Child")


def _assign(owner, ct, beneficiary, name, charitable=False):
    item = DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name
    )
    BeneficiaryAssignment.objects.create(
        item=item,
        beneficiary=beneficiary,
        is_charitable=charitable,
        charitable_org="Org" if charitable else "",
    )
    return item


@pytest.fixture
def ann(owner, cars):
    b = _beneficiary(owner, "Ann")
    _assign(owner, cars, b, "Ann car")
    return b


@pytest.fixture
def raw(ann, token):
    return issue_beneficiary_link(ann, token)


def _hash(raw_token):
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _claims():
    return EstateAccessLog.objects.filter(event="LINK_CLAIMED").count()


class TestClaim:
    def test_claim_sets_claimed_at_and_logs(self, ann, token, raw):
        link = claim_beneficiary_link(raw)
        assert link is not None and link.beneficiary == ann
        stored = BeneficiaryAccessLink.objects.get()
        assert stored.claimed_at is not None
        entry = EstateAccessLog.objects.get(event="LINK_CLAIMED")
        assert entry.beneficiary_name == "Ann" and entry.token == token
        assert raw not in entry.beneficiary_name

    def test_single_use(self, raw):
        assert claim_beneficiary_link(raw) is not None
        assert claim_beneficiary_link(raw) is None
        assert _claims() == 1

    def test_stale_read_cannot_double_claim(self, raw, monkeypatch):
        # A claim that read the link before another claim won still loses at
        # the conditional UPDATE
        stale = get_claimable_beneficiary_link(_hash(raw), timezone.now())
        first = claim_beneficiary_link(raw)
        monkeypatch.setattr(
            "my_garage.api.selectors.get_claimable_beneficiary_link",
            lambda *args: stale,
        )
        assert claim_beneficiary_link(raw) is None
        assert BeneficiaryAccessLink.objects.get().claimed_at == first.claimed_at
        assert _claims() == 1

    def test_beneficiary_deleted_mid_claim(self, ann, raw, monkeypatch):
        stale = get_claimable_beneficiary_link(_hash(raw), timezone.now())
        ann.delete()
        monkeypatch.setattr(
            "my_garage.api.selectors.get_claimable_beneficiary_link",
            lambda *args: stale,
        )
        assert claim_beneficiary_link(raw) is None

    @pytest.mark.parametrize("bad", ["", "nope", "x" * 43])
    def test_unknown_token(self, raw, bad):
        assert claim_beneficiary_link(bad) is None
        assert _claims() == 0
        assert BeneficiaryAccessLink.objects.get().claimed_at is None

    def test_revoked_link(self, ann, token, raw):
        revoke_beneficiary_link(ann, token)
        assert claim_beneficiary_link(raw) is None

    def test_reissued_link_kills_old_one(self, ann, token, raw):
        new_raw = issue_beneficiary_link(ann, token)
        assert claim_beneficiary_link(raw) is None
        assert claim_beneficiary_link(new_raw) is not None

    def test_expired_link(self, raw):
        BeneficiaryAccessLink.objects.update(expires_at=timezone.now())
        assert claim_beneficiary_link(raw) is None

    def test_token_revoked(self, token, raw):
        EstateAccessToken.objects.filter(pk=token.pk).update(is_active=False)
        assert claim_beneficiary_link(raw) is None

    def test_token_expired(self, token, raw):
        EstateAccessToken.objects.filter(pk=token.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        assert claim_beneficiary_link(raw) is None

    def test_token_deleted(self, token, raw):
        token.delete()
        assert BeneficiaryAccessLink.objects.get().issued_by_token is None
        assert claim_beneficiary_link(raw) is None

    def test_link_from_earlier_activation(self, owner, raw):
        activate_estate_plan(owner)  # deactivates the issuing token
        assert claim_beneficiary_link(raw) is None
        assert _claims() == 0


class TestClaimableSelector:
    def test_read_only(self, raw):
        link = get_claimable_beneficiary_link(_hash(raw), timezone.now())
        assert link is not None
        assert BeneficiaryAccessLink.objects.get().claimed_at is None
        assert _claims() == 0

    def test_claimed_is_not_claimable(self, raw):
        claim_beneficiary_link(raw)
        assert get_claimable_beneficiary_link(_hash(raw), timezone.now()) is None


class TestSessionLink:
    def test_claimed_link_grants_access(self, owner, raw):
        link = claim_beneficiary_link(raw)
        assert get_beneficiary_session_link(link.pk, owner.pk) == link

    def test_unexpired_window_no_longer_applies_after_claim(self, owner, raw):
        link = claim_beneficiary_link(raw)
        BeneficiaryAccessLink.objects.update(expires_at=timezone.now())
        assert get_beneficiary_session_link(link.pk, owner.pk) is not None

    def test_unclaimed_link_grants_nothing(self, owner, raw):
        link = BeneficiaryAccessLink.objects.get()
        assert get_beneficiary_session_link(link.pk, owner.pk) is None

    def test_wrong_owner(self, raw):
        link = claim_beneficiary_link(raw)
        other = User.objects.create_user(username="other", password="pass")
        assert get_beneficiary_session_link(link.pk, other.pk) is None

    def test_revoked_after_claim(self, owner, ann, token, raw):
        link = claim_beneficiary_link(raw)
        revoke_beneficiary_link(ann, token)
        assert get_beneficiary_session_link(link.pk, owner.pk) is None

    def test_token_revoked_after_claim(self, owner, token, raw):
        link = claim_beneficiary_link(raw)
        EstateAccessToken.objects.filter(pk=token.pk).update(is_active=False)
        assert get_beneficiary_session_link(link.pk, owner.pk) is None


class TestIsolation:
    def test_only_this_beneficiarys_designated_items(self, owner, cars, ann, raw):
        _assign(owner, cars, ann, "Ann watch")
        bob = _beneficiary(owner, "Bob")
        _assign(owner, cars, bob, "Bob car")
        DynamicCollectionItem.objects.create(
            owner=owner, collection_type=cars, name="Unassigned car"
        )
        _assign(owner, cars, ann, "Charity car", charitable=True)
        gone = CollectionType.objects.create(owner=owner, name="Gone")
        _assign(owner, gone, ann, "Hidden car")
        gone.is_active = False
        gone.save()
        stranger = User.objects.create_user(username="stranger", password="pass")
        their_ct = CollectionType.objects.create(owner=stranger, name="Theirs")
        _assign(stranger, their_ct, ann, "Foreign car")

        link = claim_beneficiary_link(raw)
        names = [a.item.name for a in get_beneficiary_assignments(link)]
        assert names == ["Ann car", "Ann watch"]

    def test_empty(self, owner, ann, raw):
        BeneficiaryAssignment.objects.all().delete()
        assert get_beneficiary_assignments(claim_beneficiary_link(raw)) == []

    @pytest.mark.parametrize("extra", [0, 5])
    def test_fixed_query_count(
        self, owner, cars, ann, raw, extra, django_assert_num_queries
    ):
        for i in range(extra):
            _assign(owner, cars, ann, f"Extra {i}")
        link = claim_beneficiary_link(raw)
        with django_assert_num_queries(1):
            rows = get_beneficiary_assignments(link)
            for a in rows:
                assert a.item.collection_type.name == "Cars"
        assert len(rows) == 1 + extra


class TestExecutorViewCount:
    def test_beneficiary_views_not_counted(self, owner, token):
        log_estate_access(owner, "PORTAL_VIEW", token=token)
        log_estate_access(owner, "BENEFICIARY_VIEW", token=token)
        assert get_executor_access_status(owner)["view_count"] == 1
