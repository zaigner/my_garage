"""Story 3.1: forward backfill and reverse of migration 0022.

The test settings disable migrations (the schema is built from the models), so
these tests load the real migration graph, record every migration as applied
(the schema already matches the leaf), then really migrate my_garage back to
0021, seed rows in the old schema, and migrate forward and back again. The
schema is always returned to the leaf so later tests see the current models.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import override_settings
from django.utils import timezone

pytestmark = pytest.mark.django_db(transaction=True)

BEFORE = ("my_garage", "0021_backfill_estate_token_expiry")
AFTER = ("my_garage", "0022_valuationsnapshot_token_item_name")


def _executor():
    return MigrationExecutor(connection)


def _migrate(target):
    """Migrate my_garage to `target`; returns the historical apps there."""
    executor = _executor()
    executor.migrate([target])
    return _executor().loader.project_state([target]).apps


@pytest.fixture
def at_0021():
    """Real migration graph, schema rolled back to 0021; restored afterwards."""
    with override_settings(MIGRATION_MODULES={}):
        executor = _executor()
        executor.migrate(executor.loader.graph.leaf_nodes(), fake=True)
        try:
            yield _migrate(BEFORE)
        finally:
            executor = _executor()
            executor.migrate(executor.loader.graph.leaf_nodes())


def _seed(apps):
    """Two owners' tokens and snapshots in the 0021 schema."""
    User = apps.get_model("auth", "User")
    CollectionType = apps.get_model("my_garage", "CollectionType")
    Item = apps.get_model("my_garage", "DynamicCollectionItem")
    Token = apps.get_model("my_garage", "EstateAccessToken")
    Snapshot = apps.get_model("my_garage", "ValuationSnapshot")

    owner = User.objects.create(username="migration_owner")
    ct = CollectionType.objects.create(owner=owner, name="Cars", slug="cars")
    car = Item.objects.create(owner=owner, collection_type=ct, name="911")
    watch = Item.objects.create(owner=owner, collection_type=ct, name="Rolex")

    t0 = timezone.now() - datetime.timedelta(days=10)
    first = Token.objects.create(owner=owner, token_hash="1" * 64, is_active=False)
    second = Token.objects.create(owner=owner, token_hash="2" * 64)
    Token.objects.filter(pk=first.pk).update(issued_at=t0)
    Token.objects.filter(pk=second.pk).update(issued_at=t0 + datetime.timedelta(days=5))

    def snap(item, trigger, created_at, value):
        s = Snapshot.objects.create(
            item=item,
            owner=owner,
            snapshot_date=created_at.date(),
            market_value=Decimal(value),
            snapshot_trigger=trigger,
        )
        Snapshot.objects.filter(pk=s.pk).update(created_at=created_at)
        return s.pk

    second_issued = t0 + datetime.timedelta(days=5)
    ids = {
        "orphan": snap(  # activation row older than every token
            car, "ESTATE_ACTIVATION", t0 - datetime.timedelta(days=1), "1"
        ),
        "first_car": snap(
            car, "ESTATE_ACTIVATION", t0 + datetime.timedelta(seconds=1), "100"
        ),
        "second_car": snap(
            car,
            "ESTATE_ACTIVATION",
            second_issued + datetime.timedelta(seconds=1),
            "200",
        ),
        "second_watch": snap(
            watch,
            "ESTATE_ACTIVATION",
            second_issued + datetime.timedelta(seconds=1),
            "300",
        ),
        "manual": snap(
            car, "MANUAL", second_issued + datetime.timedelta(days=1), "999"
        ),
    }

    # Another owner's token, issued between this owner's second token and a
    # later activation row, must never be picked
    other = User.objects.create(username="migration_other")
    theirs = Token.objects.create(owner=other, token_hash="3" * 64)
    Token.objects.filter(pk=theirs.pk).update(
        issued_at=second_issued + datetime.timedelta(days=1)
    )
    ids["late_car"] = snap(
        car, "ESTATE_ACTIVATION", second_issued + datetime.timedelta(days=2), "250"
    )

    return ids, first.pk, second.pk, car.pk


def test_forward_backfills_token_and_item_name(at_0021):
    ids, first, second, car = _seed(at_0021)

    apps = _migrate(AFTER)
    Snapshot = apps.get_model("my_garage", "ValuationSnapshot")
    rows = {pk: Snapshot.objects.get(pk=pk) for pk in ids.values()}

    assert rows[ids["first_car"]].token_id == first
    assert rows[ids["second_car"]].token_id == second
    assert rows[ids["second_watch"]].token_id == second
    assert rows[ids["late_car"]].token_id == second
    assert rows[ids["orphan"]].token_id is None
    assert rows[ids["manual"]].token_id is None
    assert rows[ids["second_car"]].item_name == "911"
    assert rows[ids["second_watch"]].item_name == "Rolex"
    assert rows[ids["manual"]].item_name == ""  # MANUAL rows are left as they were

    # SET_NULL: deleting an item keeps its snapshots
    Item = apps.get_model("my_garage", "DynamicCollectionItem")
    Item.objects.filter(pk=car).delete()
    assert Snapshot.objects.filter(pk=ids["second_car"], item=None).exists()


def test_reverse_drops_itemless_rows_and_restores_schema(at_0021):
    ids, _, _, car = _seed(at_0021)

    apps = _migrate(AFTER)
    Item = apps.get_model("my_garage", "DynamicCollectionItem")
    Item.objects.filter(pk=car).delete()  # 911's rows now have item=None

    apps = _migrate(BEFORE)
    Snapshot = apps.get_model("my_garage", "ValuationSnapshot")
    assert set(Snapshot.objects.values_list("pk", flat=True)) == {ids["second_watch"]}
    field_names = {f.name for f in Snapshot._meta.get_fields()}
    assert "token" not in field_names and "item_name" not in field_names
    with connection.cursor() as cursor:
        columns = {
            c.name: c
            for c in connection.introspection.get_table_description(
                cursor, Snapshot._meta.db_table
            )
        }
    assert "token_id" not in columns and "item_name" not in columns
    assert columns["item_id"].null_ok is False
