"""Unit tests for Story 2.2 estate access services, selectors and backfill."""

from __future__ import annotations

import hashlib
import importlib
from datetime import timedelta

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone

from my_garage.api.selectors import (
    ESTATE_SECURITY_EVENTS,
    ESTATE_VIEW_EVENTS,
    get_executor_access_status,
)
from my_garage.api.services import (
    activate_estate_plan,
    client_ip,
    log_estate_access,
    revoke_executor_access,
    verify_executor_code,
)
from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    EstateAccessLog,
    EstateAccessToken,
)

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def owner():
    return User.objects.create_user(username="acc_owner", password="pass")


def _hash(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def _token(owner, raw="code", **kw):
    return EstateAccessToken.objects.create(owner=owner, token_hash=_hash(raw), **kw)


class TestClientIp:
    def test_none_request(self):
        assert client_ip(None) is None

    def test_cf_header_wins(self):
        r = RequestFactory().get(
            "/", HTTP_CF_CONNECTING_IP="1.2.3.4", REMOTE_ADDR="9.9.9.9"
        )
        assert client_ip(r) == "1.2.3.4"

    def test_malformed_falls_to_xff(self):
        r = RequestFactory().get(
            "/", HTTP_CF_CONNECTING_IP="x", HTTP_X_FORWARDED_FOR="5.6.7.8, 1.1.1.1"
        )
        assert client_ip(r) == "5.6.7.8"

    def test_all_malformed_is_none(self):
        r = RequestFactory().get("/", HTTP_CF_CONNECTING_IP="x", REMOTE_ADDR="y")
        assert client_ip(r) is None

    def test_remote_addr_fallback(self):
        r = RequestFactory().get("/", REMOTE_ADDR="10.0.0.1")
        assert client_ip(r) == "10.0.0.1"


class TestIsUsable:
    def test_states(self, owner):
        now = timezone.now()
        assert _token(owner).is_usable(now)
        assert not _token(owner, "b", is_active=False).is_usable(now)
        assert not _token(owner, "c", expires_at=now - timedelta(seconds=1)).is_usable(
            now
        )
        assert _token(owner, "d", expires_at=now + timedelta(hours=1)).is_usable(now)


class TestVerify:
    def test_valid_code(self, owner):
        t = _token(owner, "abc", expires_at=timezone.now() + timedelta(hours=1))
        result = verify_executor_code("abc")
        assert result.pk == t.pk
        t.refresh_from_db()
        assert t.use_count == 1 and t.last_used_at and t.expires_at is None
        assert (
            EstateAccessLog.objects.filter(event="CODE_ACCEPTED", owner=owner).count()
            == 1
        )

    def test_reuse(self, owner):
        _token(owner, "abc")
        assert verify_executor_code("abc")
        assert verify_executor_code("abc")
        assert EstateAccessToken.objects.get().use_count == 2

    def test_unknown_logs_nothing(self, owner):
        assert verify_executor_code("nope") is None
        assert EstateAccessLog.objects.count() == 0

    def test_revoked_and_expired_logged(self, owner):
        _token(owner, "r", is_active=False)
        _token(owner, "e", expires_at=timezone.now() - timedelta(hours=1))
        assert verify_executor_code("r") is None
        assert verify_executor_code("e") is None
        assert (
            EstateAccessLog.objects.filter(event="CODE_REJECTED", owner=owner).count()
            == 2
        )


class TestActivateAndRevoke:
    def test_activate_sets_expiry_and_logs(self, owner):
        raw = activate_estate_plan(owner)
        t = EstateAccessToken.objects.get(token_hash=_hash(raw))
        assert (
            timedelta(hours=71) < t.expires_at - timezone.now() <= timedelta(hours=72)
        )
        assert EstateAccessLog.objects.filter(event="TOKEN_ISSUED", token=t).exists()

    def test_reissue_revokes_old(self, owner):
        activate_estate_plan(owner)
        activate_estate_plan(owner)
        assert EstateAccessToken.objects.filter(is_active=True).count() == 1
        assert EstateAccessLog.objects.filter(event="TOKEN_REVOKED").count() == 1

    def test_revoke(self, owner):
        assert revoke_executor_access(owner) is False
        activate_estate_plan(owner)
        assert revoke_executor_access(owner) is True
        assert not EstateAccessToken.objects.get().is_active
        assert revoke_executor_access(owner) is False

    def test_log_item_name(self, owner):
        ct = CollectionType.objects.create(owner=owner, name="Cars")
        item = DynamicCollectionItem.objects.create(
            owner=owner, collection_type=ct, name="Mustang"
        )
        log = log_estate_access(owner, "ITEM_VIEW", item=item)
        assert log.item_name == "Mustang"


class TestStatusSelector:
    def test_none(self, owner):
        s = get_executor_access_status(owner)
        assert s["state"] == "none" and s["token"] is None
        assert s["security_events"] == []
        assert s["view_count"] == 0 and s["last_view_at"] is None

    def test_each_state(self, owner):
        now = timezone.now()
        t = _token(owner, expires_at=now + timedelta(hours=1))
        assert get_executor_access_status(owner)["state"] == "unused"
        t.use_count = 1
        t.expires_at = None
        t.save()
        assert get_executor_access_status(owner)["state"] == "in_use"
        t.expires_at = now - timedelta(hours=1)
        t.save()
        assert get_executor_access_status(owner)["state"] == "expired"
        t.is_active = False
        t.save()
        assert get_executor_access_status(owner)["state"] == "revoked"

    def test_prefers_active_and_limits_events(self, owner):
        old = _token(owner, "o", is_active=False)
        new = _token(owner, "n")
        for _ in range(12):
            log_estate_access(owner, "CODE_REJECTED", token=new)
        s = get_executor_access_status(owner)
        assert s["token"].pk == new.pk != old.pk
        events = s["security_events"]
        assert isinstance(events, list) and len(events) == 10

    def test_views_do_not_crowd_out_security_events(self, owner):
        t = _token(owner)
        log_estate_access(owner, "CODE_REJECTED", token=t)
        for _ in range(12):
            log_estate_access(owner, "PORTAL_VIEW", token=t)
        events = get_executor_access_status(owner)["security_events"]
        assert [e.event for e in events] == ["CODE_REJECTED"]


class TestStatusViewSummary:
    def test_event_groups_cover_every_event_type(self):
        # A new event type must be sorted into one group or the other
        security, views = set(ESTATE_SECURITY_EVENTS), set(ESTATE_VIEW_EVENTS)
        assert not security & views
        assert security | views == {key for key, _ in EstateAccessLog.EVENT_CHOICES}

    def test_counts_views_for_current_token(self, owner):
        old = _token(owner, "o", is_active=False)
        cur = _token(owner, "n")
        log_estate_access(owner, "PORTAL_VIEW", token=old)
        log_estate_access(owner, "CODE_ACCEPTED", token=cur)
        log_estate_access(owner, "PORTAL_VIEW", token=cur)
        last = log_estate_access(owner, "ITEM_VIEW", token=cur)
        s = get_executor_access_status(owner)
        assert s["view_count"] == 2
        assert s["last_view_at"] == last.timestamp

    def test_no_views(self, owner):
        t = _token(owner)
        log_estate_access(owner, "CODE_ACCEPTED", token=t)
        s = get_executor_access_status(owner)
        assert s["view_count"] == 0 and s["last_view_at"] is None

    def test_one_aggregate_query(self, owner, django_assert_num_queries):
        t = _token(owner)
        log_estate_access(owner, "PORTAL_VIEW", token=t)
        # active token, security events, view aggregate
        with django_assert_num_queries(3):
            get_executor_access_status(owner)


class TestStatusOrderingAndAtomicity:
    def test_last_ten_newest_first(self, owner):
        t = _token(owner)
        log_estate_access(owner, "TOKEN_ISSUED", token=t)
        for _ in range(9):
            log_estate_access(owner, "CODE_REJECTED", token=t)
        log_estate_access(owner, "CODE_ACCEPTED", token=t)
        events = get_executor_access_status(owner)["security_events"]
        assert len(events) == 10
        assert events[0].event == "CODE_ACCEPTED"
        assert all(e.event != "TOKEN_ISSUED" for e in events)

    def test_failed_snapshot_rolls_back_swap(self, owner):
        from unittest.mock import patch

        from django.db import DatabaseError

        from my_garage.models import ValuationSnapshot

        activate_estate_plan(owner)
        first = EstateAccessToken.objects.get()
        with patch.object(
            ValuationSnapshot.objects, "bulk_create", side_effect=DatabaseError
        ):
            with pytest.raises(DatabaseError):
                activate_estate_plan(owner)
        first.refresh_from_db()
        assert first.is_active
        assert EstateAccessToken.objects.count() == 1
        assert EstateAccessLog.objects.filter(event="TOKEN_ISSUED").count() == 1


class TestBackfill:
    def test_backfill(self, owner):
        mod = importlib.import_module(
            "my_garage.migrations.0021_backfill_estate_token_expiry"
        )
        target = _token(owner, "a")
        used = _token(owner, "b", use_count=2)
        inactive = _token(owner, "c", is_active=False)
        mod.backfill_expires_at(apps, None)
        target.refresh_from_db()
        used.refresh_from_db()
        inactive.refresh_from_db()
        assert target.expires_at == target.issued_at + timedelta(hours=72)
        assert used.expires_at is None and inactive.expires_at is None
