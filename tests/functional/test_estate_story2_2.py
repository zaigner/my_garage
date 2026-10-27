"""Functional tests for Story 2.2: executor code entry, session, revoke, access log."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from my_garage.api.services import activate_estate_plan
from my_garage.models import EstateAccessLog, EstateAccessToken, EstateExecutor

User = get_user_model()
pytestmark = pytest.mark.django_db

PORTAL = "/estate/portal/"
DASH = "/estate/portal/dashboard/"
GENERIC = "Invalid access code. Please contact the estate owner."


@pytest.fixture
def owner():
    return User.objects.create_user(username="portal_owner", password="pass")


@pytest.fixture
def executor(owner):
    return EstateExecutor.objects.create(
        owner=owner, name="Jo", contact_info="jo@x.com"
    )


@pytest.fixture
def raw(owner):
    return activate_estate_plan(owner)


@pytest.fixture
def owner_client(owner):
    c = Client()
    c.force_login(owner)
    return c


def _enter(client, code):
    return client.post(PORTAL, {"code": code})


class TestCodeEntry:
    def test_anonymous_get(self, client):
        r = client.get(PORTAL)
        assert r.status_code == 200
        assert b"Access Estate" in r.content and b"Access code" in r.content

    def test_valid_code(self, client, owner, raw):
        r = _enter(client, raw)
        assert r.status_code == 302 and r["Location"] == DASH
        assert client.session["estate_executor_owner_id"] == owner.pk
        t = EstateAccessToken.objects.get()
        assert client.session["estate_executor_token_id"] == t.pk
        assert t.use_count == 1 and t.last_used_at and t.expires_at is None
        assert EstateAccessLog.objects.filter(event="CODE_ACCEPTED").count() == 1
        page = client.get(DASH)
        assert page.status_code == 200 and b"Estate of" in page.content
        assert b"portal_owner" in page.content

    def test_session_key_cycled(self, client, raw):
        client.get(PORTAL)
        client.session.save()
        before = client.session.session_key
        _enter(client, raw)
        assert client.session.session_key != before

    def test_reuse(self, owner, raw):
        for _ in range(2):
            c = Client()
            assert _enter(c, raw).status_code == 302
        assert EstateAccessToken.objects.get().use_count == 2

    def test_unknown_code(self, client, raw):
        r = _enter(client, "wrong")
        assert r.status_code == 200 and GENERIC in r.content.decode()
        assert "estate_executor_owner_id" not in client.session
        assert EstateAccessLog.objects.filter(event="CODE_REJECTED").count() == 0

    def test_blank_code(self, client):
        r = _enter(client, "")
        assert r.status_code == 200
        assert EstateAccessLog.objects.count() == 0

    def test_revoked_code(self, client, owner, raw, owner_client):
        owner_client.post("/estate/activate/revoke/")
        r = _enter(client, raw)
        assert GENERIC in r.content.decode()
        assert "estate_executor_owner_id" not in client.session
        assert (
            EstateAccessLog.objects.filter(event="CODE_REJECTED", owner=owner).count()
            == 1
        )

    def test_expired_code(self, client, owner, raw):
        EstateAccessToken.objects.update(expires_at=timezone.now() - timedelta(hours=1))
        assert GENERIC in _enter(client, raw).content.decode()
        assert EstateAccessLog.objects.filter(event="CODE_REJECTED").count() == 1

    def test_malformed_ip_header(self, client, raw):
        r = client.post(
            PORTAL, {"code": raw}, HTTP_CF_CONNECTING_IP="x", REMOTE_ADDR="1.2.3.4"
        )
        assert r.status_code == 302
        assert (
            EstateAccessLog.objects.get(event="CODE_ACCEPTED").ip_address == "1.2.3.4"
        )


class TestSessionGuard:
    def test_no_session(self, client):
        r = client.get(DASH)
        assert r.status_code == 302 and r["Location"] == PORTAL
        # A first-time visitor never entered a code, so no error is shown
        assert GENERIC not in client.get(PORTAL).content.decode()

    def test_post_405(self, client):
        assert client.post(DASH).status_code == 405

    def test_revoked_mid_session(self, client, owner_client, raw):
        _enter(client, raw)
        owner_client.post("/estate/activate/revoke/")
        r = client.get(DASH)
        assert r.status_code == 302 and r["Location"] == PORTAL
        assert "estate_executor_owner_id" not in client.session
        assert "_session_expiry" not in client.session
        assert GENERIC in client.get(PORTAL).content.decode()

    def test_owner_deleted(self, client, owner, raw):
        _enter(client, raw)
        owner.delete()
        r = client.get(DASH)
        assert r.status_code == 302 and r["Location"] == PORTAL

    def test_sliding_expiry(self, client, raw):
        _enter(client, raw)
        s = client.session
        s.set_expiry(60)
        s.save()
        client.get(DASH)
        assert client.session.get_expiry_age() > 29 * 86400


def _section(body, marker, end):
    start = body.index(marker)
    return body[start : body.index(end, start)]


def _status_line(owner_client):
    body = owner_client.get("/estate/activate/").content.decode()
    return _section(body, 'id="access-status-heading"', "</p>")


class TestOwnerPanel:
    def test_unused_panel(self, owner_client, executor, raw):
        body = owner_client.get("/estate/activate/").content.decode()
        assert "Not yet used" in body and "Revoke access" in body
        assert "an access code" in body and "Token issued" in body

    def test_in_use_panel(self, owner_client, client, executor, raw):
        _enter(client, raw)
        body = owner_client.get("/estate/activate/").content.decode()
        assert "In use" in body and "Code accepted" in body

    def test_unused_panel_expiry_has_zone_label(self, owner_client, executor, raw):
        body = owner_client.get("/estate/activate/").content.decode()
        assert "Not yet used" in body
        start = body.index("Not yet used")
        assert " UTC" in body[start : body.index("</p>", start)]

    def test_in_use_status_shows_code_entry_and_last_visit(
        self, owner_client, client, executor, raw
    ):
        _enter(client, raw)
        status = _status_line(owner_client)
        assert "code entered" in status and "last portal visit" not in status
        client.get(DASH)
        status = _status_line(owner_client)
        assert "code entered" in status and "last portal visit" in status
        assert status.count(" UTC") == 2

    def test_views_do_not_hide_security_events(self, owner_client, executor, raw):
        token = EstateAccessToken.objects.get()
        for _ in range(12):
            EstateAccessLog.objects.create(
                owner=token.owner, token=token, event="PORTAL_VIEW"
            )
        EstateAccessLog.objects.create(
            owner=token.owner, token=token, event="CODE_REJECTED"
        )
        body = owner_client.get("/estate/activate/").content.decode()
        events = _section(body, 'data-testid="security-events"', "</ul>")
        assert "Code rejected" in events and "Portal viewed" not in events
        summary = _section(body, 'data-testid="portal-view-summary"', "</p>")
        assert "Portal views with this code: 12" in summary and " UTC" in summary

    def test_no_views_no_summary_line(self, owner_client, executor, raw):
        body = owner_client.get("/estate/activate/").content.decode()
        assert 'data-testid="portal-view-summary"' not in body

    def test_expired_panel(self, owner_client, executor, raw):
        EstateAccessToken.objects.update(expires_at=timezone.now() - timedelta(hours=1))
        body = owner_client.get("/estate/activate/").content.decode()
        assert (
            "Expired" in body and "Revoke access" in body and "Issue new code" in body
        )

    def test_revoked_panel(self, owner_client, executor, raw):
        owner_client.post("/estate/activate/revoke/")
        body = owner_client.get("/estate/activate/").content.decode()
        assert "Revoked" in body and "Revoke access" not in body
        assert "Issue new code" in body


class TestRevoke:
    def test_revoke(self, owner_client, raw):
        r = owner_client.post("/estate/activate/revoke/", follow=True)
        assert "Executor access revoked." in r.content.decode()
        assert not EstateAccessToken.objects.get().is_active
        assert EstateAccessLog.objects.filter(event="TOKEN_REVOKED").count() == 1

    def test_no_active(self, owner_client):
        r = owner_client.post("/estate/activate/revoke/", follow=True)
        assert "No active access code." in r.content.decode()

    def test_get_redirects(self, owner_client):
        assert (
            owner_client.get("/estate/activate/revoke/")["Location"]
            == "/estate/activate/"
        )

    def test_anonymous_redirects_to_login(self, client):
        assert "/accounts/login/" in client.post("/estate/activate/revoke/")["Location"]

    def test_executor_remove_revokes(self, owner_client, executor, raw):
        r = owner_client.post("/estate/executor/remove/", follow=True)
        assert "Executor removed" in r.content.decode()
        assert not EstateAccessToken.objects.get().is_active
        assert not EstateExecutor.objects.exists()

    def test_executor_update_keeps_token(self, owner_client, executor, raw):
        owner_client.post(
            "/estate/executor/", {"name": "New", "contact_info": "n@x.com"}
        )
        assert EstateAccessToken.objects.get().is_active


class TestSuccessPage:
    def test_shows_url_and_expiry(self, owner_client, executor):
        r = owner_client.post("/estate/activate/", {"confirmed": "on"}, follow=True)
        body = r.content.decode()
        assert "http://testserver/estate/portal/" in body
        assert "if unused" in body

    def test_prefers_public_base_url(self, owner_client, executor, settings):
        settings.PUBLIC_BASE_URL = "https://garage.example.com/"
        r = owner_client.post("/estate/activate/", {"confirmed": "on"}, follow=True)
        body = r.content.decode()
        assert "https://garage.example.com/estate/portal/" in body
        assert "testserver" not in body


class TestSessionHardening:
    def test_csrf_rotated(self, client, raw):
        client.get(PORTAL)
        before = client.cookies["csrftoken"].value
        _enter(client, raw)
        assert client.cookies["csrftoken"].value != before

    def test_owner_stays_logged_in(self, owner_client, raw):
        _enter(owner_client, raw)
        assert owner_client.get("/estate/activate/").status_code == 200

    def test_head_dashboard(self, client, raw):
        _enter(client, raw)
        assert client.head(DASH).status_code == 200

    def test_cache_headers(self, client, raw):
        cc = client.get(PORTAL)["Cache-Control"]
        assert "no-store" in cc or "max-age=0" in cc
        _enter(client, raw)
        cc = client.get(DASH)["Cache-Control"]
        assert "no-store" in cc or "max-age=0" in cc

    def test_portal_templates_have_no_local_assets(self):
        from pathlib import Path

        import my_garage

        root = Path(my_garage.__file__).parent / "templates/my_garage/estate/portal"
        files = list(root.glob("*.html"))
        assert files
        for f in files:
            text = f.read_text()
            for bad in ("{% static", "/static/", "/media/"):
                assert bad not in text, f"{f.name} contains {bad}"
