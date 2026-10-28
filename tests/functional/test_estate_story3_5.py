"""Functional tests for Story 3.5: beneficiary item detail and photo."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import Client, override_settings

from my_garage.api.services import (
    activate_estate_plan,
    issue_beneficiary_link,
    revoke_beneficiary_link,
)
from my_garage.models import (
    Beneficiary,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateAccessLog,
    EstateAccessToken,
    GenericServiceRecord,
    ValuationSnapshot,
)

User = get_user_model()
pytestmark = pytest.mark.django_db

HOME = "/estate/beneficiary/"
LINK_KEY = "estate_beneficiary_link_id"
OWNER_KEY = "estate_beneficiary_owner_id"


def detail(item_id):
    return f"/estate/beneficiary/items/{item_id}/"


def photo(item_id):
    return detail(item_id) + "photo/"


@pytest.fixture
def owner():
    return User.objects.create_user(
        username="estate_3_5", password="pass", first_name="Pat", last_name="Owner"
    )


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


def _assign(owner, ct, beneficiary, name, charitable=False, note="", **fields):
    item = DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name, **fields
    )
    BeneficiaryAssignment.objects.create(
        item=item,
        beneficiary=beneficiary,
        is_charitable=charitable,
        charitable_org="Org" if charitable else "",
        conditional_note=note,
    )
    return item


@pytest.fixture
def ann(owner):
    return Beneficiary.objects.create(owner=owner, name="Ann", relationship="Spouse")


@pytest.fixture
def car(owner, cars, ann):
    item = _assign(
        owner,
        cars,
        ann,
        "Ann Porsche",
        note="Please keep it in the family.",
        purchase_price=Decimal("10000"),
        purchase_date=date(2019, 3, 4),
        current_market_value=Decimal("12500"),
        notes="Garaged since new.",
        custom_fields={"colour": "Guards Red"},
    )
    GenericServiceRecord.objects.create(
        item=item,
        date=date(2021, 6, 1),
        vendor="Old Garage",
        description="Oil change",
        total_cost=Decimal("150"),
    )
    GenericServiceRecord.objects.create(
        item=item,
        date=date(2023, 6, 1),
        vendor="New Garage",
        description="Brakes",
        total_cost=Decimal("900"),
    )
    return item


@pytest.fixture
def token(owner, car):
    """Activation after `car` exists, so it is in the snapshot."""
    activate_estate_plan(owner)
    return EstateAccessToken.objects.get(owner=owner, is_active=True)


@pytest.fixture
def ben(ann, token):
    """A browser holding a claimed beneficiary session."""
    client = Client()
    raw = issue_beneficiary_link(ann, token)
    assert client.post(f"/estate/beneficiary/claim/{raw}/").status_code == 302
    return client


def _views():
    return EstateAccessLog.objects.filter(event="BENEFICIARY_VIEW")


def _not_found_body():
    return Client().get(HOME).content


def _section(body, heading_id):
    """The HTML of the <section> labelled by `heading_id`."""
    start = body.index(f'aria-labelledby="{heading_id}"')
    return body[start : body.index("</section>", start)]


class TestOwnItem:
    def test_every_field(self, car, token, ben):
        # Values move after activation, so current and snapshot figures differ
        car.current_market_value = Decimal("13000")
        car.purchase_price = Decimal("11000")
        car.save()
        r = ben.get(detail(car.pk))
        body = r.content.decode()
        assert r.status_code == 200
        assert "no-cache" in r["Cache-Control"]
        for text in (
            "Ann Porsche",
            "Cars",
            'data-testid="photo-placeholder"',
            "Guards Red",
            "Garaged since new.",
            "Please keep it in the family.",
            "Owner's wishes for this item",
            "Old Garage",
            "New Garage",
            "Oil change",
            "Brakes",
            "$150",
            "$900",
            "Maintenance",
            "June 1, 2021",
            "June 1, 2023",
        ):
            assert text in body, text
        assert body.index("New Garage") < body.index("Old Garage")

        snap = _section(body, "snapshot-heading")
        assert token.issued_at.strftime("%B %-d, %Y") in snap
        assert "$12,500" in snap and "$10,000" in snap and "+$2,500" in snap
        assert "Value minus purchase price" in snap
        assert "Current value: <span" in snap and "$13,000</span>" in snap
        assert "Added after activation" not in snap

        details = _section(body, "details-heading")
        assert "$11,000" in details and "March 4, 2019" in details
        assert "$10,000" not in details

        # Not part of FR29
        assert "Valuation history" not in body
        assert "/estate/portal/" not in body
        entry = _views().get()
        assert entry.item_name == "Ann Porsche" and entry.beneficiary_name == "Ann"
        assert entry.item_id == car.pk and entry.token == token

    def test_note_comes_before_snapshot(self, car, ben):
        body = ben.get(detail(car.pk)).content.decode()
        assert body.index('data-testid="conditional-note"') < body.index(
            "Value at activation"
        )

    def test_no_note_no_box(self, car, ben):
        BeneficiaryAssignment.objects.filter(item=car).update(conditional_note="  ")
        body = ben.get(detail(car.pk)).content.decode()
        assert 'data-testid="conditional-note"' not in body

    def test_added_after_activation(self, owner, cars, ann, ben):
        later = _assign(owner, cars, ann, "Later Mini")
        body = ben.get(detail(later.pk)).content.decode()
        assert "Added after activation" in body and "Snapshot date" not in body

    def test_older_tokens_snapshot_ignored(self, owner, cars, ann, ben):
        later = _assign(owner, cars, ann, "Later Mini")
        old = EstateAccessToken.objects.create(
            owner=owner, token_hash="0" * 64, is_active=False
        )
        ValuationSnapshot.objects.create(
            item=later,
            item_name=later.name,
            owner=owner,
            token=old,
            snapshot_trigger="ESTATE_ACTIVATION",
            snapshot_date=date(2020, 1, 1),
            market_value=Decimal("777"),
        )
        body = ben.get(detail(later.pk)).content.decode()
        assert "Added after activation" in body and "$777" not in body

    def test_head_logs_nothing(self, car, ben):
        assert ben.head(detail(car.pk)).status_code == 200
        assert not _views().exists()

    def test_post_not_allowed(self, car, ben):
        assert ben.post(detail(car.pk)).status_code == 405
        assert ben.post(photo(car.pk)).status_code == 405


class TestIsolation:
    @pytest.mark.parametrize(
        "case",
        [
            "other",
            "unassigned",
            "charitable",
            "soft_deleted",
            "other_owner",
            "none",
            "huge_id",
        ],
    )
    def test_404(self, owner, cars, ann, ben, case, tmp_path):
        with override_settings(MEDIA_ROOT=str(tmp_path)):
            if case == "other":
                bob = Beneficiary.objects.create(
                    owner=owner, name="Bob", relationship="Child"
                )
                item = _assign(owner, cars, bob, "Bob Ferrari")
            elif case == "unassigned":
                item = DynamicCollectionItem.objects.create(
                    owner=owner, collection_type=cars, name="Spare Mini"
                )
            elif case == "charitable":
                item = _assign(owner, cars, ann, "Charity Jaguar", charitable=True)
            elif case == "soft_deleted":
                gone = CollectionType.objects.create(owner=owner, name="Gone")
                item = _assign(owner, gone, ann, "Hidden Lotus")
                gone.is_active = False
                gone.save()
            elif case == "other_owner":
                stranger = User.objects.create_user(username="stranger", password="x")
                ct = CollectionType.objects.create(owner=stranger, name="Theirs")
                theirs = Beneficiary.objects.create(
                    owner=stranger, name="Ann", relationship="Spouse"
                )
                item = _assign(stranger, ct, theirs, "Their Aston")
            else:
                item = None
            if item is not None:
                item.photo.save("x.png", ContentFile(b"SECRET"), save=True)
            item_id = item.pk if item else (2**70 if case == "huge_id" else 999999)
            for url in (detail(item_id), photo(item_id)):
                r = ben.get(url)
                assert r.status_code == 404, url
                assert r.content == _not_found_body()
                assert "no-cache" in r["Cache-Control"]
            assert not _views().exists()
            # The session survives a 404 on someone else's item
            assert LINK_KEY in ben.session


class TestNoSession:
    def test_no_session_404(self, car):
        for url in (detail(car.pk), photo(car.pk)):
            r = Client().get(url)
            assert r.status_code == 404 and r.content == _not_found_body()

    def test_revoked_mid_session(self, ann, token, car, ben):
        revoke_beneficiary_link(ann, token)
        r = ben.get(detail(car.pk))
        assert r.status_code == 404 and r.content == _not_found_body()
        assert LINK_KEY not in ben.session and OWNER_KEY not in ben.session

    def test_revoked_mid_session_photo(self, ann, token, car, ben):
        revoke_beneficiary_link(ann, token)
        assert ben.get(photo(car.pk)).status_code == 404
        assert LINK_KEY not in ben.session and OWNER_KEY not in ben.session


class TestPhoto:
    def test_served_privately(self, car, ben, tmp_path):
        with override_settings(MEDIA_ROOT=str(tmp_path)):
            car.photo.save("car.png", ContentFile(b"PNGBYTES"), save=True)
            body = ben.get(detail(car.pk)).content.decode()
            assert f'src="{photo(car.pk)}"' in body
            assert 'alt="Ann Porsche"' in body
            assert 'data-testid="photo-placeholder"' not in body

            r = ben.get(photo(car.pk))
            assert r.status_code == 200
            assert b"".join(r.streaming_content) == b"PNGBYTES"
            cc = r["Cache-Control"]
            assert "private" in cc and "no-store" in cc
            assert ben.head(photo(car.pk)).status_code == 200
            # Only the detail page is logged
            assert _views().count() == 1

    def test_no_photo_404(self, car, ben):
        r = ben.get(photo(car.pk))
        assert r.status_code == 404 and r.content == _not_found_body()
        assert "no-cache" in r["Cache-Control"]

    def test_missing_file_404(self, car, ben, tmp_path):
        with override_settings(MEDIA_ROOT=str(tmp_path)):
            car.photo.name = "gone.png"
            car.save()
            r = ben.get(photo(car.pk))
            assert r.status_code == 404 and r.content == _not_found_body()
            assert "no-cache" in r["Cache-Control"]


class TestPortalLinks:
    def test_rows_link_to_detail(self, car, ben):
        body = ben.get(HOME).content.decode()
        hrefs = re.findall(r'href="(/estate/beneficiary/items/\d+/)"', body)
        assert hrefs == [detail(car.pk)]
        assert ben.get(hrefs[0]).status_code == 200


class TestExecutorUnchanged:
    def test_executor_detail_still_shows_snapshot(self, owner, car, token):
        client = Client()
        session = client.session
        session["estate_executor_owner_id"] = owner.pk
        session["estate_executor_token_id"] = token.pk
        session.save()
        body = client.get(f"/estate/portal/items/{car.pk}/").content.decode()
        for text in ("Snapshot date", "Market value", "Value minus purchase price"):
            assert text in body
