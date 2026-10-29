"""Functional tests for the Epic 3 retrospective fixes (F1-F5, F8)."""

from __future__ import annotations

import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from my_garage.api.services import activate_estate_plan, issue_beneficiary_link
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
LINK_KEY = "estate_beneficiary_link_id"
OWNER_KEY = "estate_beneficiary_owner_id"
EXECUTOR_OWNER_KEY = "estate_executor_owner_id"
EXECUTOR_TOKEN_KEY = "estate_executor_token_id"
GENERIC_CODE_ERROR = "Invalid access code. Please contact the estate owner."
NF_HEADING = "This link is no longer active"
NF_BODY = (
    "Please contact the estate's executor for a new link to view the items "
    "designated to you."
)
ONCE_MSG = "A link can only be shown once. Issue a new link to get one."


def claim_url(raw):
    return f"/estate/beneficiary/claim/{raw}/"


def issue_url(pk):
    return f"/estate/portal/beneficiaries/{pk}/link/"


def revoke_url(pk):
    return issue_url(pk) + "revoke/"


def issued_url(pk):
    return issue_url(pk) + "issued/"


def detail(item_id):
    return f"/estate/beneficiary/items/{item_id}/"


def photo(item_id):
    return detail(item_id) + "photo/"


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="retro3_fn", password="pass", first_name="Pat", last_name="Owner"
    )


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


def _assign(owner, ct, beneficiary, name):
    item = DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name
    )
    BeneficiaryAssignment.objects.create(item=item, beneficiary=beneficiary)
    return item


@pytest.fixture
def ann(owner, cars):
    b = Beneficiary.objects.create(owner=owner, name="Ann", relationship="Spouse")
    _assign(owner, cars, b, "Ann Porsche")
    return b


def _empty(beneficiary):
    BeneficiaryAssignment.objects.filter(beneficiary=beneficiary).update(
        is_charitable=True, charitable_org="Org"
    )


def _executor(owner):
    """An executor browser; activates a fresh code (ending older links)."""
    client = Client()
    assert client.post(PORTAL, {"code": activate_estate_plan(owner)}).status_code == 302
    return client


def _token(owner):
    return EstateAccessToken.objects.get(owner=owner, is_active=True)


def _claimed(raw):
    client = Client()
    assert client.post(claim_url(raw)).status_code == 302
    return client


@pytest.fixture
def executor(owner, ann):
    return _executor(owner)


@pytest.fixture
def ben(owner, ann, executor):
    """Ann's claimed session under the executor's current token."""
    return _claimed(issue_beneficiary_link(ann, _token(owner)))


def _links_section(body):
    start = body.index('aria-labelledby="links-heading"')
    return body[start : body.index("</section>", start)]


def _not_found_body():
    return Client().get(claim_url("never-issued")).content


class TestEmptiedLinkHolding:
    def test_dashboard_row(self, ann, executor, ben):
        _empty(ann)
        section = _links_section(executor.get(DASH).content.decode())
        assert "Ann" in section and "0 items" in section
        assert "Opened " in section
        assert f'action="{revoke_url(ann.pk)}"' in section
        assert f'action="{issue_url(ann.pk)}"' not in section

    def test_rendered_revoke_form_reaches_revoke(self, ann, executor, ben):
        _empty(ann)
        section = _links_section(executor.get(DASH).content.decode())
        (action,) = re.findall(r'action="([^"]*/revoke/)"', section)
        r = executor.post(action, follow=True)
        assert r.redirect_chain == [(DASH, 302)]
        assert "Link revoked for Ann." in r.content.decode()
        assert not BeneficiaryAccessLink.objects.filter(is_active=True).exists()
        assert ben.get(HOME).status_code == 404
        assert LINK_KEY not in ben.session

    def test_claimed_after_expiry_still_revocable(self, ann, executor, ben):
        BeneficiaryAccessLink.objects.update(
            expires_at=timezone.now() - timedelta(days=1)
        )
        _empty(ann)
        section = _links_section(executor.get(DASH).content.decode())
        assert "Opened " in section
        assert f'action="{revoke_url(ann.pk)}"' in section
        assert executor.post(revoke_url(ann.pk)).status_code == 302
        assert ben.get(HOME).status_code == 404

    def test_issue_is_404(self, ann, executor, ben):
        _empty(ann)
        assert executor.post(issue_url(ann.pk)).status_code == 404
        assert BeneficiaryAccessLink.objects.filter(is_active=True).count() == 1

    def test_designated_row_keeps_issue(self, ann, executor, ben):
        section = _links_section(executor.get(DASH).content.decode())
        assert "1 item" in section
        assert f'action="{issue_url(ann.pk)}"' in section


class TestIssuedPageAfterDesignationRemoved:
    def test_shown_once(self, ann, executor):
        assert executor.post(issue_url(ann.pk)).status_code == 302
        BeneficiaryAssignment.objects.all().delete()
        r = executor.get(issued_url(ann.pk))
        assert r.status_code == 200
        assert "/estate/beneficiary/claim/" in r.content.decode()
        r = executor.get(issued_url(ann.pk), follow=True)
        assert ONCE_MSG in r.content.decode()


class TestNeverEligible:
    def test_not_listed_and_404(self, owner, executor):
        bob = Beneficiary.objects.create(owner=owner, name="Bob", relationship="Child")
        section = _links_section(executor.get(DASH).content.decode())
        assert "Bob" not in section
        assert executor.post(revoke_url(bob.pk)).status_code == 404
        assert executor.post(issue_url(bob.pk)).status_code == 404
        assert executor.get(issued_url(bob.pk)).status_code == 404


class TestOldTokenLink:
    def test_not_listed_and_revoke_404(self, owner, ann):
        activate_estate_plan(owner)
        _claimed(issue_beneficiary_link(ann, _token(owner)))
        BeneficiaryAssignment.objects.all().delete()
        executor = _executor(owner)  # new activation: Ann's link is old-token
        section = _links_section(executor.get(DASH).content.decode())
        assert "Ann" not in section
        assert executor.post(revoke_url(ann.pk)).status_code == 404


class TestDoubleActivation:
    def test_reactivation_leaves_one_active_token(self, owner):
        # Sequential only; the concurrency proof is the unit call-order test
        EstateExecutor.objects.create(owner=owner, name="Jo Smith")
        client = Client()
        client.force_login(owner)
        for _ in range(2):
            assert client.post(ACTIVATE, {"confirmed": "on"}).status_code == 302
        assert (
            EstateAccessToken.objects.filter(owner=owner, is_active=True).count() == 1
        )


class TestBeneficiaryNotFound:
    def test_page_content(self, owner, ann):
        r = Client().get(claim_url("never-issued"))
        body = r.content.decode()
        assert r.status_code == 404
        assert "no-cache" in r["Cache-Control"] and "no-store" in r["Cache-Control"]
        assert NF_HEADING in body and NF_BODY in body
        assert "<title>Link no longer active</title>" in body
        for leak in ("Pat Owner", "retro3_fn", "Ann", "Not Found"):
            assert leak not in body

    def test_identical_across_cases(self, owner, cars, ann, executor, ben):
        bob = Beneficiary.objects.create(owner=owner, name="Bob", relationship="Child")
        foreign = _assign(owner, cars, bob, "Bob Ferrari")
        expected = _not_found_body()
        responses = [
            Client().get(HOME),  # no session
            Client().get(detail(foreign.pk)),
            Client().post(claim_url("never-issued")),
            ben.get(detail(foreign.pk)),  # foreign item, live session
            ben.get(photo(foreign.pk)),
        ]
        issue_beneficiary_link(ann, _token(owner))  # kills Ann's session
        responses += [ben.get(HOME), ben.get(detail(foreign.pk))]
        for r in responses:
            assert r.status_code == 404 and r.content == expected
            assert "no-cache" in r["Cache-Control"]

    def test_pending_flash_not_rendered(self, owner, ben):
        # Stale executor keys: the executor check queues a flash message
        session = ben.session
        session[EXECUTOR_OWNER_KEY] = owner.pk
        session[EXECUTOR_TOKEN_KEY] = 999999
        session.save()
        assert ben.get(DASH).status_code == 302
        r = ben.get(claim_url("never-issued"))
        assert r.status_code == 404 and r.content == _not_found_body()
        assert GENERIC_CODE_ERROR not in r.content.decode()


class TestExecutorExpiryGuard:
    def test_stale_executor_keys_keep_beneficiary_session(self, owner, ben):
        session = ben.session
        session[EXECUTOR_OWNER_KEY] = owner.pk
        session[EXECUTOR_TOKEN_KEY] = 999999
        session.save()
        r = ben.get(DASH)
        assert r.status_code == 302 and r.url == PORTAL
        assert EXECUTOR_TOKEN_KEY not in ben.session
        assert LINK_KEY in ben.session and OWNER_KEY in ben.session
        assert ben.session.get_expiry_age() > timedelta(days=29).total_seconds()
        assert ben.get(HOME).status_code == 200

    def test_beneficiary_only_session_expiry_unchanged(self, ben):
        session = ben.session
        session.set_expiry(timedelta(days=5))
        session.save()
        before = ben.session["_session_expiry"]
        r = ben.get(DASH)
        assert r.status_code == 302 and r.url == PORTAL
        assert ben.session["_session_expiry"] == before

    def test_no_session_still_cleared(self):
        client = Client()
        session = client.session
        session[EXECUTOR_OWNER_KEY] = 1
        session[EXECUTOR_TOKEN_KEY] = 999999
        session.set_expiry(timedelta(days=30))
        session.save()
        assert client.get(DASH).status_code == 302
        assert "_session_expiry" not in client.session


class TestReissueOverOldTokenLink:
    def test_revoked_row_has_old_token(self, owner, ann):
        activate_estate_plan(owner)
        old = _token(owner)
        issue_beneficiary_link(ann, old)
        executor = _executor(owner)  # owner reactivates: token B
        new = _token(owner)
        assert executor.post(issue_url(ann.pk)).status_code == 302
        revoked = EstateAccessLog.objects.get(event="LINK_REVOKED")
        assert revoked.token == old and revoked.beneficiary_name == "Ann"
        assert (
            EstateAccessLog.objects.filter(event="LINK_ISSUED")
            .order_by("pk")
            .last()
            .token
            == new
        )


class TestOwnerCopy:
    def test_executor_form(self, owner):
        EstateExecutor.objects.create(owner=owner, name="Jo Smith")
        activate_estate_plan(owner)
        client = Client()
        client.force_login(owner)
        body = client.get("/estate/executor/").content.decode()
        assert (
            "Saving this revokes the current access code and ends every "
            "beneficiary link issued under it. Continue?" in body
        )
        assert (
            "Saving a different name revokes the current access code and ends "
            "every beneficiary link issued under it." in body
        )
        assert (
            "Their access code will also be revoked, and every beneficiary link "
            "issued under it will stop working." in body
        )

    def test_activate_page(self, owner):
        activate_estate_plan(owner)
        client = Client()
        client.force_login(owner)
        body = client.get(ACTIVATE).content.decode()
        assert (
            "Your executor will lose access immediately, and every beneficiary "
            "link issued under the code will stop working." in body
        )
        assert (
            body.count(
                "Issuing a new code revokes the current one immediately and ends "
                "every beneficiary link issued under it."
            )
            == 2
        )

    def test_messages(self, owner):
        client = Client()
        client.force_login(owner)
        EstateExecutor.objects.create(owner=owner, name="Jo Smith")
        activate_estate_plan(owner)
        r = client.post(
            "/estate/executor/", {"name": "Sam Lee", "contact_info": ""}, follow=True
        )
        assert (
            "Their previous access code has been revoked, and beneficiary links "
            "issued under it no longer work" in r.content.decode()
        )
        activate_estate_plan(owner)
        r = client.post("/estate/executor/remove/", follow=True)
        assert (
            "Executor removed. Their access code has been revoked, and beneficiary "
            "links issued under it no longer work." in r.content.decode()
        )
        activate_estate_plan(owner)
        r = client.post("/estate/activate/revoke/", follow=True)
        assert (
            "Executor access revoked. Beneficiary links issued under the code no "
            "longer work." in r.content.decode()
        )
