"""Functional tests for Story 3.4: beneficiary claim and portal session."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from my_garage.api.services import (
    activate_estate_plan,
    issue_beneficiary_link,
    log_estate_access,
    revoke_beneficiary_link,
    revoke_executor_access,
)
from my_garage.models import (
    Beneficiary,
    BeneficiaryAccessLink,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateAccessLog,
    EstateAccessToken,
    EstateExecutor,
)

User = get_user_model()
pytestmark = pytest.mark.django_db

PORTAL = "/estate/portal/"
DASH = "/estate/portal/dashboard/"
ACTIVATE = "/estate/activate/"
HOME = "/estate/beneficiary/"
EMPTY_MSG = "No items have been designated for you yet."
BUTTON = "View my designated items"
LINK_KEY = "estate_beneficiary_link_id"
OWNER_KEY = "estate_beneficiary_owner_id"
EXECUTOR_KEYS = ("estate_executor_owner_id", "estate_executor_token_id")


def claim_url(raw):
    return f"/estate/beneficiary/claim/{raw}/"


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="estate_3_4", password="pass", first_name="Pat", last_name="Owner"
    )


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


def _assign(owner, ct, beneficiary, name, charitable=False, value=None):
    item = DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name, current_market_value=value
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
    b = Beneficiary.objects.create(owner=owner, name="Ann", relationship="Spouse")
    _assign(owner, cars, b, "Ann Porsche", value=12500)
    return b


@pytest.fixture
def token(owner):
    activate_estate_plan(owner)
    return EstateAccessToken.objects.get(owner=owner, is_active=True)


@pytest.fixture
def raw(ann, token):
    return issue_beneficiary_link(ann, token)


def _claim(client, raw):
    return client.post(claim_url(raw))


@pytest.fixture
def ben(raw):
    """A browser holding a claimed beneficiary session."""
    client = Client()
    assert _claim(client, raw).status_code == 302
    return client


def _logs(event):
    return EstateAccessLog.objects.filter(event=event).count()


def _not_found_body():
    return Client().get(claim_url("never-issued")).content


class TestOpenLink:
    def test_get_shows_confirm_and_changes_nothing(self, raw):
        client = Client()
        r = client.get(claim_url(raw))
        body = r.content.decode()
        assert r.status_code == 200 and BUTTON in body
        assert "Pat Owner" in body and "Ann" not in body
        assert "no-cache" in r["Cache-Control"]
        assert BeneficiaryAccessLink.objects.get().claimed_at is None
        assert LINK_KEY not in client.session
        assert _logs("LINK_CLAIMED") == 0

    def test_preview_fetch_does_not_burn_link(self, raw):
        Client().get(claim_url(raw))
        Client().head(claim_url(raw))
        assert _claim(Client(), raw).status_code == 302

    def test_confirm_form_posts_to_claim_url(self, raw):
        # No action attribute: the button posts back to this same claim URL
        body = Client().get(claim_url(raw)).content.decode()
        start = body.index("<form")
        form_tag = body[start : body.index(">", start)]
        assert 'method="post"' in form_tag and "action=" not in form_tag
        assert "csrfmiddlewaretoken" in body


class TestClaim:
    def test_claim_starts_session(self, owner, raw):
        client = Client()
        r = _claim(client, raw)
        assert r.status_code == 302 and r.url == HOME
        link = BeneficiaryAccessLink.objects.get()
        assert link.claimed_at is not None
        assert client.session[LINK_KEY] == link.pk
        assert client.session[OWNER_KEY] == owner.pk
        assert client.session.get_expiry_age() > timedelta(days=29).total_seconds()
        entry = EstateAccessLog.objects.get(event="LINK_CLAIMED")
        assert entry.beneficiary_name == "Ann"
        assert raw not in str(dict(client.session))

    def test_csrf_enforced(self, raw):
        client = Client(enforce_csrf_checks=True)
        assert client.post(claim_url(raw)).status_code == 403
        client.get(claim_url(raw))
        csrf = client.cookies["csrftoken"].value
        r = client.post(claim_url(raw), {"csrfmiddlewaretoken": csrf})
        assert r.status_code == 302

    def test_reuse_is_404(self, raw, ben):
        client = Client()
        assert client.get(claim_url(raw)).status_code == 404
        assert _claim(client, raw).status_code == 404
        assert _logs("LINK_CLAIMED") == 1

    def test_reopen_own_link_goes_to_portal(self, raw, ben):
        claimed_at = BeneficiaryAccessLink.objects.get().claimed_at
        for r in (ben.get(claim_url(raw)), _claim(ben, raw)):
            assert r.status_code == 302 and r.url == HOME
        assert BeneficiaryAccessLink.objects.get().claimed_at == claimed_at
        assert _logs("LINK_CLAIMED") == 1

    def test_reopen_after_session_dies_is_404(self, ann, token, raw, ben):
        revoke_beneficiary_link(ann, token)
        assert ben.get(claim_url(raw)).status_code == 404

    def test_other_beneficiarys_used_link_is_404(self, owner, cars, token, raw, ben):
        bob = Beneficiary.objects.create(owner=owner, name="Bob", relationship="Child")
        _assign(owner, cars, bob, "Bob Ferrari")
        bob_raw = issue_beneficiary_link(bob, token)
        assert _claim(Client(), bob_raw).status_code == 302
        # Ann's live session does not open Bob's spent link
        r = ben.get(claim_url(bob_raw))
        assert r.status_code == 404 and r.content == _not_found_body()

    def test_other_methods(self, raw):
        assert Client().put(claim_url(raw)).status_code == 405


class TestDeadLinks:
    @pytest.mark.parametrize(
        "kill",
        ["unknown", "revoked", "expired", "token_revoked", "token_expired", "old"],
    )
    def test_identical_404(self, owner, ann, token, raw, kill):
        url_raw = raw
        if kill == "unknown":
            url_raw = "never-issued"
        elif kill == "revoked":
            revoke_beneficiary_link(ann, token)
        elif kill == "expired":
            BeneficiaryAccessLink.objects.update(expires_at=timezone.now())
        elif kill == "token_revoked":
            revoke_executor_access(owner)
        elif kill == "token_expired":
            EstateAccessToken.objects.update(
                expires_at=timezone.now() - timedelta(seconds=1)
            )
        elif kill == "old":
            activate_estate_plan(owner)
        expected = _not_found_body()
        for r in (Client().get(claim_url(url_raw)), _claim(Client(), url_raw)):
            assert r.status_code == 404 and r.content == expected
        assert _logs("LINK_CLAIMED") == 0


class TestPortal:
    def test_lists_only_designated_items(self, owner, cars, ann, ben):
        bob = Beneficiary.objects.create(owner=owner, name="Bob", relationship="Child")
        _assign(owner, cars, bob, "Bob Ferrari")
        DynamicCollectionItem.objects.create(
            owner=owner, collection_type=cars, name="Spare Mini"
        )
        _assign(owner, cars, ann, "Ann Bentley")
        _assign(owner, cars, ann, "Charity Jaguar", charitable=True)
        gone = CollectionType.objects.create(owner=owner, name="Gone")
        _assign(owner, gone, ann, "Hidden Lotus")
        gone.is_active = False
        gone.save()

        r = ben.get(HOME)
        body = r.content.decode()
        assert r.status_code == 200
        assert "Hello, Ann" in body and "Spouse" in body and "Pat Owner" in body
        assert "Ann Porsche" in body and "Ann Bentley" in body and "$12,500" in body
        for hidden in ("Bob Ferrari", "Spare Mini", "Charity Jaguar", "Hidden Lotus"):
            assert hidden not in body
        assert EMPTY_MSG not in body
        assert "no-cache" in r["Cache-Control"]
        entry = EstateAccessLog.objects.get(event="BENEFICIARY_VIEW")
        assert entry.beneficiary_name == "Ann"

    def test_empty_state(self, ben):
        BeneficiaryAssignment.objects.all().delete()
        body = ben.get(HOME).content.decode()
        assert EMPTY_MSG in body

    def test_head_logs_nothing(self, ben):
        assert ben.head(HOME).status_code == 200
        assert _logs("BENEFICIARY_VIEW") == 0

    def test_post_not_allowed(self, ben):
        assert ben.post(HOME).status_code == 405

    def test_no_session_404(self):
        r = Client().get(HOME)
        assert r.status_code == 404 and r.content == _not_found_body()
        assert "no-cache" in r["Cache-Control"]

    def test_session_slides(self, ben):
        session = ben.session
        session.set_expiry(timedelta(days=1))
        session.save()
        ben.get(HOME)
        assert ben.session.get_expiry_age() > timedelta(days=29).total_seconds()


class TestMidSessionRevoke:
    @pytest.mark.parametrize(
        "kill", ["link_revoked", "reissued", "owner_revoked", "reactivated"]
    )
    def test_keys_cleared_and_404(self, owner, ann, token, ben, kill):
        if kill == "link_revoked":
            revoke_beneficiary_link(ann, token)
        elif kill == "reissued":
            issue_beneficiary_link(ann, token)
        elif kill == "owner_revoked":
            revoke_executor_access(owner)
        else:
            activate_estate_plan(owner)
        assert ben.get(HOME).status_code == 404
        assert LINK_KEY not in ben.session and OWNER_KEY not in ben.session
        # No executor session here, so the 30-day expiry goes too
        assert "_session_expiry" not in ben.session

    def test_executor_replaced(self, owner, ben):
        EstateExecutor.objects.create(owner=owner, name="Jo Smith")
        owner_client = Client()
        owner_client.force_login(owner)
        owner_client.post("/estate/executor/", {"name": "Sam Lee", "contact_info": ""})
        assert ben.get(HOME).status_code == 404
        assert LINK_KEY not in ben.session


class TestSharedSession:
    def test_executor_and_beneficiary_coexist(self, owner, ann, raw):
        client = Client()
        assert (
            client.post(PORTAL, {"code": activate_estate_plan(owner)}).status_code
            == 302
        )
        executor_keys = {k: client.session[k] for k in EXECUTOR_KEYS}
        # The new activation killed `raw`; issue under the current token
        token = EstateAccessToken.objects.get(owner=owner, is_active=True)
        assert _claim(client, issue_beneficiary_link(ann, token)).status_code == 302
        assert {k: client.session[k] for k in EXECUTOR_KEYS} == executor_keys
        assert client.get(HOME).status_code == 200
        assert client.get(DASH).status_code == 200

        # Revoking the link ends only the beneficiary session
        revoke_beneficiary_link(ann, token)
        assert client.get(HOME).status_code == 404
        assert {k: client.session[k] for k in EXECUTOR_KEYS} == executor_keys
        assert client.session.get_expiry_age() > timedelta(days=29).total_seconds()
        assert client.get(DASH).status_code == 200

    def test_auth_session_untouched(self, owner, raw):
        client = Client()
        client.force_login(owner)
        user_id = client.session["_auth_user_id"]
        assert _claim(client, raw).status_code == 302
        assert client.session["_auth_user_id"] == user_id
        assert client.get(ACTIVATE).status_code == 200


class TestOwnerPanel:
    def test_claim_listed_and_views_not_counted(self, owner, token, raw, ben):
        ben.get(HOME)
        ben.get(HOME)
        log_estate_access(owner, "PORTAL_VIEW", token=token)
        owner_client = Client()
        owner_client.force_login(owner)
        body = owner_client.get(ACTIVATE).content.decode()
        assert "Link claimed &middot; Ann" in body
        assert "Portal views with this code: 1 " in body
