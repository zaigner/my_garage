"""Epic 3 retro decisions Q2-Q4: LINK_REJECTED, noindex, the notes hint."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from my_garage.api import services
from my_garage.api.services import (
    activate_estate_plan,
    issue_beneficiary_link,
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
)

User = get_user_model()
pytestmark = pytest.mark.django_db

HOME = "/estate/beneficiary/"
ACTIVATE = "/estate/activate/"
BUTTON = "View my designated items"
NOINDEX = '<meta name="robots" content="noindex">'
IP = "203.0.113.7"
HINT = (
    "If you designate this item to a beneficiary, they will see its full details "
    "once estate access is activated, including these notes, custom fields, photo "
    "and service records."
)


def claim_url(raw):
    return f"/estate/beneficiary/claim/{raw}/"


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="estate_retro_q", password="pass", first_name="Pat", last_name="Owner"
    )


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


@pytest.fixture
def ann(owner, cars):
    b = Beneficiary.objects.create(owner=owner, name="Ann", relationship="Spouse")
    item = DynamicCollectionItem.objects.create(
        owner=owner, collection_type=cars, name="Ann Porsche"
    )
    BeneficiaryAssignment.objects.create(item=item, beneficiary=b)
    return b


@pytest.fixture
def token(owner):
    activate_estate_plan(owner)
    return EstateAccessToken.objects.get(owner=owner, is_active=True)


@pytest.fixture
def raw(ann, token):
    return issue_beneficiary_link(ann, token)


@pytest.fixture
def ben(raw):
    """A browser holding a claimed beneficiary session."""
    client = Client()
    assert client.post(claim_url(raw)).status_code == 302
    return client


def _rejected():
    return EstateAccessLog.objects.filter(event="LINK_REJECTED")


def _events():
    return list(EstateAccessLog.objects.order_by("pk").values_list("event", flat=True))


def _not_found_body():
    return Client().get(claim_url("never-issued")).content


def _age_last_rejection(by):
    # The link must predate the row, or the dedupe ignores it
    BeneficiaryAccessLink.objects.update(issued_at=timezone.now() - timedelta(days=2))
    _rejected().update(timestamp=timezone.now() - by)


class TestLinkRejectedMatrix:
    def test_unknown_url_logs_nothing(self, raw):
        for r in (
            Client().get(claim_url("never-issued"), REMOTE_ADDR=IP),
            Client().post(claim_url("never-issued"), REMOTE_ADDR=IP),
        ):
            assert r.status_code == 404
        assert not _rejected().exists()

    def test_reused_link_get_logs_one(self, token, raw, ben):
        r = Client().get(claim_url(raw), REMOTE_ADDR=IP)
        assert r.status_code == 404 and r.content == _not_found_body()
        entry = _rejected().get()
        assert entry.beneficiary_name == "Ann" and entry.token == token
        assert entry.ip_address == IP

    def test_reused_link_post_logs_one(self, token, raw, ben):
        r = Client().post(claim_url(raw), REMOTE_ADDR=IP)
        assert r.status_code == 404 and r.content == _not_found_body()
        entry = _rejected().get()
        assert entry.beneficiary_name == "Ann" and entry.token == token
        assert entry.ip_address == IP

    @pytest.mark.parametrize(
        "kill",
        ["revoked", "expired", "token_revoked", "token_expired", "old", "token_gone"],
    )
    def test_dead_link_logs_one(self, owner, ann, token, raw, kill):
        issuing_token = token
        if kill == "revoked":
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
        else:
            token.delete()
            issuing_token = None
        expected = _not_found_body()
        for r in (Client().get(claim_url(raw)), Client().post(claim_url(raw))):
            assert r.status_code == 404 and r.content == expected
        entry = _rejected().get()
        assert entry.beneficiary_name == "Ann" and entry.token == issuing_token
        assert entry.owner == owner

    def test_lost_claim_race_logs_one(self, raw, monkeypatch):
        real_claim = services.claim_beneficiary_link

        def lose_race(raw_token, request=None):
            # Another browser's claim wins between this POST's read and write
            assert real_claim(raw_token) is not None
            return None

        monkeypatch.setattr("my_garage.estate_views.claim_beneficiary_link", lose_race)
        r = Client().post(claim_url(raw), REMOTE_ADDR=IP)
        assert r.status_code == 404 and r.content == _not_found_body()
        entry = _rejected().get()
        assert entry.beneficiary_name == "Ann" and entry.ip_address == IP

    def test_repeat_within_24h_logs_nothing(self, raw, ben):
        Client().get(claim_url(raw))
        _age_last_rejection(timedelta(hours=23, minutes=59))
        for r in (Client().get(claim_url(raw)), Client().post(claim_url(raw))):
            assert r.status_code == 404
        assert _rejected().count() == 1

    def test_repeat_after_24h_logs_one_more(self, raw, ben):
        Client().get(claim_url(raw))
        _age_last_rejection(timedelta(hours=24))
        assert Client().get(claim_url(raw)).status_code == 404
        assert _rejected().count() == 2
        # The new row restarts the 24 hours
        assert Client().post(claim_url(raw)).status_code == 404
        assert _rejected().count() == 2

    def test_head_on_dead_link_logs_nothing(self, raw, ben):
        assert Client().head(claim_url(raw)).status_code == 404
        assert not _rejected().exists()

    def test_reopen_own_link_logs_nothing(self, raw, ben):
        for r in (ben.get(claim_url(raw)), ben.post(claim_url(raw))):
            assert r.status_code == 302 and r.url == HOME
        assert not _rejected().exists()

    def test_claimable_link_unchanged(self, raw):
        before = _events()
        client = Client()
        r = client.get(claim_url(raw))
        assert r.status_code == 200 and BUTTON in r.content.decode()
        assert _events() == before
        assert client.post(claim_url(raw)).status_code == 302
        assert _events() == before + ["LINK_CLAIMED"]

    def test_owner_panel_lists_one_rejection(self, owner, raw, ben):
        other = Client()
        other.get(claim_url(raw))
        other.get(claim_url(raw))
        owner_client = Client()
        owner_client.force_login(owner)
        body = owner_client.get(ACTIVATE).content.decode()
        assert body.count("Link rejected &middot; Ann") == 1


class TestNoindex:
    def test_claim_page(self, raw):
        r = Client().get(claim_url(raw))
        assert r.status_code == 200 and NOINDEX in r.content.decode()

    def test_not_found_page(self):
        r = Client().get(claim_url("never-issued"))
        assert r.status_code == 404 and NOINDEX in r.content.decode()


def _notes_block(page, start_marker):
    """The markup from the notes textarea to the end of its field wrapper."""
    start = page.index('name="notes"', page.index(start_marker))
    return page[start : page.index("</div>", start)]


class TestNotesHint:
    @pytest.fixture
    def item(self, owner, cars):
        return DynamicCollectionItem.objects.create(
            owner=owner, collection_type=cars, name="Mini"
        )

    @pytest.fixture
    def owner_client(self, owner):
        client = Client()
        client.force_login(owner)
        return client

    def test_add_form(self, owner_client, cars):
        r = owner_client.get(f"/collections/{cars.slug}/items/add/")
        assert r.status_code == 200
        page = r.content.decode()
        assert HINT in _notes_block(page, "<form")

    def test_edit_form(self, owner_client, item):
        r = owner_client.get(
            f"/collections/{item.collection_type.slug}/items/{item.pk}/"
        )
        assert r.status_code == 200
        page = r.content.decode()
        assert HINT in _notes_block(page, 'id="main-form"')
        # Only notes gets help text on the edit page; model help texts stay off
        form = page.index('id="main-form"')
        details = page[form : page.index("</form>", form)]
        assert details.count(HINT) == 1
        assert "Primary identifier for this item" not in details
        assert "What you paid for it" not in details
