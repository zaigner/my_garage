"""Functional tests for Story 3.1: removed items on the executor dashboard."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.api.services import activate_estate_plan
from my_garage.models import CollectionType, DynamicCollectionItem

User = get_user_model()
pytestmark = pytest.mark.django_db

PORTAL = "/estate/portal/"
DASH = "/estate/portal/dashboard/"


def detail(pk):
    return f"/estate/portal/items/{pk}/"


@pytest.fixture
def owner():
    return User.objects.create_user(username="estate_3_1", password="pass")


@pytest.fixture
def cars(owner):
    return CollectionType.objects.create(owner=owner, name="Cars")


def _item(owner, ct, name, value=None):
    return DynamicCollectionItem.objects.create(
        owner=owner, collection_type=ct, name=name, current_market_value=value
    )


def _executor_client(owner):
    client = Client()
    assert client.post(PORTAL, {"code": activate_estate_plan(owner)}).status_code == 302
    return client


def _block(body, testid):
    start = body.index(f'data-testid="{testid}"')
    end = body.index("</tr>" if testid == "removed-row" else "</li>", start)
    return body[start:end]


def _summary(body):
    start = body.index('id="summary-heading"')
    return body[start : body.index("</section>", start)]


class TestRemovedItem:
    def test_removed_row_in_table_and_cards(self, owner, cars):
        _item(owner, cars, "Kept Porsche", Decimal("100000"))
        gone = _item(owner, cars, "Sold Ferrari", Decimal("250000"))
        client = _executor_client(owner)
        gone_pk = gone.pk
        gone.delete()

        body = client.get(DASH).content.decode()
        for testid in ("removed-row", "removed-card"):
            block = _block(body, testid)
            assert "Sold Ferrari" in block
            assert "Removed after activation" in block
            assert "$250,000" in block
            assert "<a " not in block
        assert detail(gone_pk) not in body

    def test_value_at_activation_unchanged_by_deletion(self, owner, cars):
        _item(owner, cars, "Kept Porsche", Decimal("100000"))
        gone = _item(owner, cars, "Sold Ferrari", Decimal("250000"))
        client = _executor_client(owner)
        before = _summary(client.get(DASH).content.decode())
        assert "$350,000" in before

        gone.delete()
        after = _summary(client.get(DASH).content.decode())
        assert "$350,000" in after
        assert "Plus 1 removed after activation" in after
        assert "Excludes 1 removed after activation" in after
        assert "items valued" not in after  # removed item counts as valued
        assert "Plus" not in before and "Excludes" not in before

    def test_unvalued_removed_item_shows_partial_footnote(self, owner, cars):
        _item(owner, cars, "Kept Porsche", Decimal("100000"))
        gone = _item(owner, cars, "Unvalued Barn Find")
        client = _executor_client(owner)
        gone.delete()
        assert "1 of 2 items valued" in _summary(client.get(DASH).content.decode())

    def test_all_items_removed_still_lists_them(self, owner, cars):
        gone = _item(owner, cars, "Only Car", Decimal("5000"))
        client = _executor_client(owner)
        gone.delete()
        body = client.get(DASH).content.decode()
        assert "No assets are recorded in this estate." not in body
        assert "Only Car" in _block(body, "removed-row")

    def test_detail_of_deleted_item_is_404(self, owner, cars):
        gone = _item(owner, cars, "Sold Ferrari", Decimal("250000"))
        client = _executor_client(owner)
        pk = gone.pk
        gone.delete()
        assert client.get(detail(pk)).status_code == 404


class TestDashboardAndDetailAgree:
    def test_same_value_at_activation(self, owner, cars):
        item = _item(owner, cars, "Kept Porsche", Decimal("123456"))
        client = _executor_client(owner)
        item.current_market_value = Decimal("1")
        item.save()
        dash = client.get(DASH).content.decode()
        page = client.get(detail(item.pk)).content.decode()
        assert "$123,456" in dash and "$123,456" in page

    def test_reactivated_session_reads_only_new_token(self, owner, cars):
        item = _item(owner, cars, "Kept Porsche", Decimal("100000"))
        gone = _item(owner, cars, "Sold Ferrari", Decimal("250000"))
        _executor_client(owner)  # first activation
        gone.delete()
        item.current_market_value = Decimal("120000")
        item.save()
        client = _executor_client(owner)  # reactivation

        body = client.get(DASH).content.decode()
        assert 'data-testid="removed-row"' not in body
        assert "Sold Ferrari" not in body
        assert "$120,000" in _summary(body)
