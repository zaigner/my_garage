"""Functional tests for Story 2.4: executor item detail view."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.test import Client, override_settings

from my_garage.api.services import activate_estate_plan
from my_garage.models import (
    Beneficiary,
    BeneficiaryAssignment,
    CollectionType,
    DynamicCollectionItem,
    EstateAccessLog,
    GenericServiceRecord,
    GenericValuationHistory,
    ValuationSnapshot,
)

User = get_user_model()
pytestmark = pytest.mark.django_db

PORTAL = "/estate/portal/"
DASH = "/estate/portal/dashboard/"


def _snapshot_block(body):
    start = body.index('id="snapshot-heading"')
    return body[start : body.index("<section", start)]


def detail(pk):
    return f"/estate/portal/items/{pk}/"


@pytest.fixture
def owner():
    return User.objects.create_user(username="estate_2_4", password="pass")


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


def _item(owner, ct, name="Porsche", value=None, **kw):
    return DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name, current_market_value=value, **kw
    )


def _executor_client(owner):
    client = Client()
    assert client.post(PORTAL, {"code": activate_estate_plan(owner)}).status_code == 302
    return client


class TestDetailPage:
    def test_full_page(self, owner, cars):
        item = _item(
            owner,
            cars,
            "1972 Porsche 911",
            Decimal("150000"),
            purchase_price=Decimal("90000"),
            purchase_date=datetime.date(2010, 5, 4),
            notes="Matching numbers",
            custom_fields={"engine_size": "2.4L"},
        )
        priya = Beneficiary.objects.create(
            owner=owner, name="Priya", relationship="Child"
        )
        BeneficiaryAssignment.objects.create(
            item=item, beneficiary=priya, conditional_note="Only after she is 25"
        )
        GenericServiceRecord.objects.create(
            item=item,
            date=datetime.date(2023, 3, 1),
            vendor="Acme Garage",
            description="Oil change",
            category="MAINTENANCE",
            total_cost=Decimal("250"),
        )
        GenericValuationHistory.objects.create(item=item, value=Decimal("148000"))
        client = _executor_client(owner)

        r = client.get(detail(item.pk))
        body = r.content.decode()
        assert r.status_code == 200
        for text in (
            "1972 Porsche 911",
            "Cars",
            "$90,000",
            "May 4, 2010",
            "Matching numbers",
            "Engine Size",
            "2.4L",
            "Priya",
            "Only after she is 25",
            "Acme Garage",
            "Oil change",
            "Maintenance",
            "$250",
            "$148,000",
            "$150,000",
        ):
            assert text in body, text
        assert 'data-testid="photo-placeholder"' in body
        assert detail(item.pk) + "photo/" not in body
        assert 'href="/estate/portal/dashboard/"' in body
        log = EstateAccessLog.objects.get(event="ITEM_VIEW")
        assert log.item_id == item.pk and log.token is not None

    def test_snapshot_block(self, owner, cars):
        item = _item(owner, cars, value=Decimal("100"), purchase_price=Decimal("60"))
        client = _executor_client(owner)
        ValuationSnapshot.objects.filter(item=item).update(
            market_value=Decimal("4321"),
            cost_basis=Decimal("1234"),
            equity=Decimal("-777"),
        )
        body = client.get(detail(item.pk)).content.decode()
        block = _snapshot_block(body)
        snap = ValuationSnapshot.objects.get(item=item)
        assert "Added after activation" not in block
        assert f"{snap.snapshot_date:%B} {snap.snapshot_date.day}" in block
        assert "$4,321" in block and "$1,234" in block
        assert "\u2212$777" in block

    def test_added_after_activation(self, owner, cars):
        client = _executor_client(owner)
        late = _item(owner, cars, "Late", Decimal("5"))
        assert "Added after activation" in client.get(detail(late.pk)).content.decode()

    def test_null_snapshot_values_and_real_zero(self, owner, cars):
        item = _item(owner, cars)
        client = _executor_client(owner)
        ValuationSnapshot.objects.filter(item=item).update(
            market_value=None, cost_basis=None, equity=None
        )
        block = _snapshot_block(client.get(detail(item.pk)).content.decode())
        assert "Added after activation" not in block
        assert block.count("\u2014") >= 3
        ValuationSnapshot.objects.filter(item=item).update(
            market_value=Decimal("0"), cost_basis=Decimal("0"), equity=Decimal("0")
        )
        block = _snapshot_block(client.get(detail(item.pk)).content.decode())
        assert block.count("$0") >= 3

    def test_charitable_designation(self, owner, cars):
        item = _item(owner, cars)
        BeneficiaryAssignment.objects.create(
            item=item, is_charitable=True, charitable_org="Red Cross"
        )
        body = _executor_client(owner).get(detail(item.pk)).content.decode()
        assert "Red Cross" in body and "(charitable)" in body

    def test_valuation_history_newest_first(self, owner, cars):
        item = _item(owner, cars)
        GenericValuationHistory.objects.create(item=item, value=Decimal("1111"))
        GenericValuationHistory.objects.create(item=item, value=Decimal("2222"))
        body = _executor_client(owner).get(detail(item.pk)).content.decode()
        assert body.index("$2,222") < body.index("$1,111")

    def test_blank_note_omitted_and_unassigned(self, owner, cars):
        item = _item(owner, cars)
        body = _executor_client(owner).get(detail(item.pk)).content.decode()
        assert "Owner&#x27;s note" not in body and "Owner's note" not in body
        assert "Unassigned" in body

    def test_empty_lists(self, owner, cars):
        item = _item(owner, cars)
        body = _executor_client(owner).get(detail(item.pk)).content.decode()
        assert "No service records" in body and "No valuation history" in body

    def test_lists_newest_first(self, owner, cars):
        item = _item(owner, cars)
        for vendor, day in (("OldShop", 1), ("NewShop", 9)):
            GenericServiceRecord.objects.create(
                item=item,
                date=datetime.date(2024, 1, day),
                vendor=vendor,
                description="d",
                total_cost=Decimal("1"),
            )
        body = _executor_client(owner).get(detail(item.pk)).content.decode()
        assert body.index("NewShop") < body.index("OldShop")


class TestAccess:
    def test_other_owner_and_unknown_404_nothing_logged(self, owner, cars, tmp_path):
        other = User.objects.create_user(username="o2_4", password="pass")
        with override_settings(MEDIA_ROOT=str(tmp_path)):
            theirs = _item(other, CollectionType.objects.create(owner=other, name="Z"))
            theirs.photo.save("t.png", ContentFile(b"X"), save=True)
            client = _executor_client(owner)
            assert client.get(detail(theirs.pk)).status_code == 404
            assert client.get(detail(999999)).status_code == 404
            assert client.get(detail(theirs.pk) + "photo/").status_code == 404
        assert not EstateAccessLog.objects.filter(event="ITEM_VIEW").exists()

    def test_no_session_redirects(self, owner, cars):
        item = _item(owner, cars)
        r = Client().get(detail(item.pk))
        assert r.status_code == 302 and r.url == PORTAL
        assert Client().get(detail(item.pk) + "photo/").status_code == 302

    def test_head_ok_not_logged(self, owner, cars):
        item = _item(owner, cars)
        client = _executor_client(owner)
        assert client.head(detail(item.pk)).status_code == 200
        assert not EstateAccessLog.objects.filter(event="ITEM_VIEW").exists()

    def test_post_405(self, owner, cars):
        item = _item(owner, cars)
        client = _executor_client(owner)
        assert client.post(detail(item.pk)).status_code == 405
        assert client.post(detail(item.pk) + "photo/").status_code == 405

    def test_revoked_token_redirects(self, owner, cars):
        item = _item(owner, cars)
        client = _executor_client(owner)
        from my_garage.api.services import revoke_executor_access

        revoke_executor_access(owner)
        assert client.get(detail(item.pk)).status_code == 302


class TestPhoto:
    def test_photo_served_privately(self, owner, cars, tmp_path):
        with override_settings(MEDIA_ROOT=str(tmp_path)):
            item = _item(owner, cars)
            item.photo.save("car.png", ContentFile(b"PNGBYTES"), save=True)
            client = _executor_client(owner)

            body = client.get(detail(item.pk)).content.decode()
            assert f'src="{detail(item.pk)}photo/"' in body
            assert f'alt="{item.name}"' in body

            r = client.get(detail(item.pk) + "photo/")
            assert r.status_code == 200
            assert b"".join(r.streaming_content) == b"PNGBYTES"
            cc = r["Cache-Control"]
            assert "private" in cc and "no-store" in cc

    def test_photo_revoked_and_head(self, owner, cars, tmp_path):
        from my_garage.api.services import revoke_executor_access

        with override_settings(MEDIA_ROOT=str(tmp_path)):
            item = _item(owner, cars)
            item.photo.save("car.png", ContentFile(b"PNGBYTES"), save=True)
            client = _executor_client(owner)
            assert client.head(detail(item.pk) + "photo/").status_code == 200
            revoke_executor_access(owner)
            r = client.get(detail(item.pk) + "photo/")
            assert r.status_code == 302 and r.url == PORTAL

    def test_no_photo_404(self, owner, cars):
        item = _item(owner, cars)
        assert (
            _executor_client(owner).get(detail(item.pk) + "photo/").status_code == 404
        )

    def test_missing_file_404(self, owner, cars, tmp_path):
        with override_settings(MEDIA_ROOT=str(tmp_path)):
            item = _item(owner, cars)
            item.photo.name = "gone.png"
            item.save()
            r = _executor_client(owner).get(detail(item.pk) + "photo/")
            assert r.status_code == 404


class TestDashboardLinks:
    def test_rows_link_to_detail(self, owner, cars):
        item = _item(owner, cars, "Linked")
        body = _executor_client(owner).get(DASH).content.decode()
        assert body.count(f'href="{detail(item.pk)}"') == 2  # table + card


class TestMoneyAndTimes:
    @pytest.mark.parametrize(
        "value, shown",
        [
            (None, "\u2014"),
            (Decimal("0"), "$0"),
            (Decimal("-0.4"), "$0"),
            (Decimal("-50"), "\u2212$50"),
            (Decimal("-1234.6"), "\u2212$1,235"),
            (Decimal("50"), "$50"),
        ],
    )
    def test_money_partial(self, value, shown):
        html = render_to_string("my_garage/estate/portal/_money.html", {"value": value})
        assert html == shown

    def test_negative_money_on_detail_page(self, owner, cars):
        item = _item(owner, cars, value=Decimal("-50"))
        client = _executor_client(owner)
        body = client.get(detail(item.pk)).content.decode()
        assert 'Current value: <span class="text-luxury-white">\u2212$50</span>' in body

    def test_valuation_time_has_zone_label(self, owner, cars):
        item = _item(owner, cars)
        GenericValuationHistory.objects.create(item=item, value=Decimal("10"))
        client = _executor_client(owner)
        body = client.get(detail(item.pk)).content.decode()
        start = body.index('id="history-heading"')
        history = body[start : body.index("</section>", start)]
        assert " UTC</span>" in history
