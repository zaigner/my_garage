"""Functional tests for Story 3.3: beneficiary link generation (executor)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.utils import timezone

from my_garage.api.services import activate_estate_plan
from my_garage.models import (
    Beneficiary,
    BeneficiaryAccessLink,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateAccessLog,
)

User = get_user_model()
pytestmark = pytest.mark.django_db

PORTAL = "/estate/portal/"
DASH = "/estate/portal/dashboard/"
ACTIVATE = "/estate/activate/"
ONCE_MSG = "A link can only be shown once. Issue a new link to get one."


def issue_url(pk):
    return f"/estate/portal/beneficiaries/{pk}/link/"


def revoke_url(pk):
    return issue_url(pk) + "revoke/"


def issued_url(pk):
    return issue_url(pk) + "issued/"


@pytest.fixture
def owner():
    return User.objects.create_user(username="estate_3_3", password="pass")


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


def _beneficiary(owner, ct, name, charitable=False):
    b = Beneficiary.objects.create(owner=owner, name=name, relationship="Child")
    item = DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=f"{name} car"
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
    return _beneficiary(owner, cars, "Ann")


def _executor(owner, **kwargs):
    client = Client(**kwargs)
    assert client.post(PORTAL, {"code": activate_estate_plan(owner)}).status_code == 302
    return client


@pytest.fixture
def client(owner, ann):
    return _executor(owner)


def _links(body):
    start = body.index('id="links-heading"')
    return body[start : body.index("</section>", start)]


def _issue(client, pk, follow=False):
    return client.post(issue_url(pk), follow=follow)


class TestDashboardList:
    def test_lists_only_designated(self, owner, cars, client, ann):
        _beneficiary(owner, cars, "Charles", charitable=True)
        gone = CollectionType.objects.create(owner=owner, name="Gone")
        _beneficiary(owner, gone, "Cora")
        gone.is_active = False
        gone.save()
        body = _links(client.get(DASH).content.decode())
        assert "Ann" in body and "1 item" in body
        assert "Charles" not in body and "Cora" not in body
        assert "No link" in body and "Issue link" in body
        assert "Revoke" not in body

    def test_status_variants(self, owner, client, ann):
        revoke_action = f'action="{revoke_url(ann.pk)}"'
        _issue(client, ann.pk)
        body = _links(client.get(DASH).content.decode())
        assert "not yet opened (expires" in body
        assert "Issue new link" in body and revoke_action in body

        BeneficiaryAccessLink.objects.update(claimed_at=timezone.now())
        body = _links(client.get(DASH).content.decode())
        assert "Opened " in body
        assert "Issue new link" in body and revoke_action in body

        BeneficiaryAccessLink.objects.update(claimed_at=None, is_active=False)
        body = _links(client.get(DASH).content.decode())
        assert "Revoked" in body and "Issue link" in body
        assert "Issue new link" not in body and revoke_action not in body

        BeneficiaryAccessLink.objects.update(
            is_active=True, expires_at=timezone.now() - timedelta(minutes=1)
        )
        body = _links(client.get(DASH).content.decode())
        assert "Expired" in body and "Issue link" in body
        assert revoke_action not in body

    def test_activation_change_resets_to_no_link(self, owner, client, ann):
        _issue(client, ann.pk)
        new_client = _executor(owner)
        assert "No link" in _links(new_client.get(DASH).content.decode())


class TestIssue:
    def test_issue_redirects_and_shows_once(self, owner, client, ann):
        response = _issue(client, ann.pk)
        assert response.status_code == 302
        assert response["Location"] == issued_url(ann.pk)
        link = BeneficiaryAccessLink.objects.get()
        assert link.issued_by_token_id == client.session["estate_executor_token_id"]

        page = client.get(issued_url(ann.pk))
        assert page.status_code == 200
        body = page.content.decode()
        assert "This link cannot be recovered. Save it now before closing." in body
        assert "/estate/beneficiary/claim/" in body
        assert "http://testserver/estate/beneficiary/claim/" in body
        raw = body.split("/estate/beneficiary/claim/")[1].split("/")[0]
        assert link.link_token_hash != raw
        assert raw not in str(list(BeneficiaryAccessLink.objects.values()))
        assert raw not in str(list(EstateAccessLog.objects.values()))
        assert "estate_beneficiary_link" in page.cookies
        assert page.cookies["estate_beneficiary_link"].value == ""

        replay = client.get(issued_url(ann.pk), follow=True)
        assert replay.redirect_chain[-1][0] == DASH
        assert ONCE_MSG in replay.content.decode()

    @override_settings(PUBLIC_BASE_URL="https://garage.example.com/")
    def test_public_base_url(self, client, ann):
        _issue(client, ann.pk)
        body = client.get(issued_url(ann.pk)).content.decode()
        assert "https://garage.example.com/estate/beneficiary/claim/" in body

    def test_missing_cookie_redirects(self, client, ann):
        _issue(client, ann.pk)
        client.cookies.pop("estate_beneficiary_link")
        response = client.get(issued_url(ann.pk), follow=True)
        assert ONCE_MSG in response.content.decode()

    def test_tampered_cookie_redirects(self, client, ann):
        _issue(client, ann.pk)
        client.cookies["estate_beneficiary_link"] = "garbage"
        response = client.get(issued_url(ann.pk), follow=True)
        assert ONCE_MSG in response.content.decode()

    def test_replaced_link_not_shown(self, client, ann):
        _issue(client, ann.pk)
        stale_cookie = client.cookies["estate_beneficiary_link"].value
        _issue(client, ann.pk)
        client.cookies["estate_beneficiary_link"] = stale_cookie
        response = client.get(issued_url(ann.pk), follow=True)
        assert ONCE_MSG in response.content.decode()

    def test_reissue_revokes_old(self, client, ann):
        _issue(client, ann.pk)
        _issue(client, ann.pk)
        assert BeneficiaryAccessLink.objects.filter(is_active=True).count() == 1
        assert EstateAccessLog.objects.filter(event="LINK_REVOKED").count() == 1

    def test_ineligible_and_foreign_404(self, owner, cars, client):
        charity = _beneficiary(owner, cars, "Charles", charitable=True)
        other = User.objects.create_user(username="o2", password="x")
        other_ct = CollectionType.objects.create(owner=other, name="X")
        foreign = _beneficiary(other, other_ct, "Foreign")
        for pk in (charity.pk, foreign.pk, 99999):
            assert client.post(issue_url(pk)).status_code == 404
            assert client.post(revoke_url(pk)).status_code == 404
            assert client.get(issued_url(pk)).status_code == 404
        assert not BeneficiaryAccessLink.objects.exists()

    def test_requires_executor_session(self, ann):
        anon = Client()
        for response in (
            anon.post(issue_url(ann.pk)),
            anon.post(revoke_url(ann.pk)),
            anon.get(issued_url(ann.pk)),
        ):
            assert response.status_code == 302 and response["Location"] == PORTAL
        assert not BeneficiaryAccessLink.objects.exists()
        assert not EstateAccessLog.objects.filter(event__startswith="LINK_").exists()

    def test_get_is_405(self, client, ann):
        assert client.get(issue_url(ann.pk)).status_code == 405
        assert client.get(revoke_url(ann.pk)).status_code == 405

    def test_csrf_enforced(self, owner, ann):
        logged_in = _executor(owner)
        strict = Client(enforce_csrf_checks=True)
        strict.cookies = logged_in.cookies
        assert strict.post(issue_url(ann.pk)).status_code == 403
        assert strict.post(revoke_url(ann.pk)).status_code == 403
        assert not BeneficiaryAccessLink.objects.exists()

    def test_changes_no_estate_data(self, client, ann):
        before = list(BeneficiaryAssignment.objects.values())
        _issue(client, ann.pk)
        client.post(revoke_url(ann.pk))
        assert list(BeneficiaryAssignment.objects.values()) == before


class TestLinkCookie:
    def test_issue_cookie_attributes(self, client, ann):
        cookie = _issue(client, ann.pk).cookies["estate_beneficiary_link"]
        assert cookie["httponly"] is True
        assert cookie["samesite"] == "Strict"
        assert cookie["path"] == issued_url(ann.pk)
        assert cookie["max-age"] == "" and cookie["expires"] == ""

    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_cookie_secure_when_session_cookie_is(self, client, ann):
        cookie = _issue(client, ann.pk).cookies["estate_beneficiary_link"]
        assert cookie["secure"] is True

    def test_issued_page_deletes_cookie(self, client, ann):
        _issue(client, ann.pk)
        cookie = client.get(issued_url(ann.pk)).cookies["estate_beneficiary_link"]
        assert cookie.value == "" and int(cookie["max-age"]) == 0
        assert cookie["path"] == issued_url(ann.pk)

    def test_404_path_deletes_cookie(self, client, ann):
        _issue(client, ann.pk)
        BeneficiaryAssignment.objects.update(is_charitable=True)
        # Emptied but still link-holding would show the URL (Epic 3 retro F1);
        # with the link revoked too, Ann is out of the executor's scope
        BeneficiaryAccessLink.objects.update(is_active=False)
        response = client.get(issued_url(ann.pk))
        assert response.status_code == 404
        cookie = response.cookies["estate_beneficiary_link"]
        assert cookie.value == "" and int(cookie["max-age"]) == 0
        assert cookie["path"] == issued_url(ann.pk)

    def test_head_is_405(self, client, ann):
        _issue(client, ann.pk)
        assert client.head(issued_url(ann.pk)).status_code == 405
        # the cookie was not consumed
        assert client.get(issued_url(ann.pk)).status_code == 200


class TestRevoke:
    def test_revoke(self, client, ann):
        _issue(client, ann.pk)
        response = client.post(revoke_url(ann.pk), follow=True)
        assert not BeneficiaryAccessLink.objects.get().is_active
        assert "Link revoked for Ann." in response.content.decode()
        assert EstateAccessLog.objects.filter(event="LINK_REVOKED").count() == 1

    def test_revoke_without_link(self, client, ann):
        response = client.post(revoke_url(ann.pk), follow=True)
        assert "No active link." in response.content.decode()


class TestClaimUrl:
    def test_issued_url_opens_the_claim_page(self, client, ann):
        # Story 3.4 replaced the 404 stub: the URL shown once must be claimable
        _issue(client, ann.pk)
        body = client.get(issued_url(ann.pk)).content.decode()
        raw = body.split("/estate/beneficiary/claim/")[1].split("/")[0]
        assert Client().get(f"/estate/beneficiary/claim/{raw}/").status_code == 200
        assert Client().get("/estate/beneficiary/claim/nope/").status_code == 404


class TestOwnerActivityPanel:
    def test_link_events_listed_with_name(self, owner, client, ann):
        _issue(client, ann.pk)
        client.post(revoke_url(ann.pk))
        owner_client = Client()
        owner_client.force_login(owner)
        body = owner_client.get(ACTIVATE).content.decode()
        assert "Link issued &middot; Ann" in body
        assert "Link revoked &middot; Ann" in body
