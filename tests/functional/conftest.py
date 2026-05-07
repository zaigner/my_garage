"""
Shared fixtures for functional (HTTP smoke) tests.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
)

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="func_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def automobiles_type(user):
    ct, _ = CollectionType.objects.get_or_create(
        owner=user,
        slug="automobiles",
        defaults={
            "name": "Automobiles",
            "service_provider_key": "vehicle",
            "is_system": True,
        },
    )
    return ct


@pytest.fixture
def horology_type(user):
    ct, _ = CollectionType.objects.get_or_create(
        owner=user,
        slug="horology-salon",
        defaults={
            "name": "Horology Salon",
            "service_provider_key": "timepiece",
            "is_system": True,
        },
    )
    return ct


@pytest.fixture
def migrated_vehicle_item(user, automobiles_type):
    """A DynamicCollectionItem representing a migrated vehicle (has
    source_vehicle_id)."""
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=automobiles_type,
        name="2021 Toyota Tacoma",
        purchase_price=Decimal("38000.00"),
        current_market_value=Decimal("40000.00"),
        custom_fields={
            "source_vehicle_id": 999,
            "make": "Toyota",
            "model": "Tacoma",
            "year": 2021,
        },
    )


@pytest.fixture
def migrated_timepiece_item(user, horology_type):
    """A DynamicCollectionItem representing a migrated timepiece (has
    source_timepiece_id)."""
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=horology_type,
        name="Seiko Prospex SPB143J1",
        purchase_price=Decimal("500.00"),
        current_market_value=Decimal("550.00"),
        custom_fields={
            "source_timepiece_id": 888,
            "brand": "Seiko",
            "watch_model": "Prospex",
            "reference_number": "SPB143J1",
        },
    )


@pytest.fixture
def collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Sneaker Collection",
        slug="sneaker-collection",
        field_schema={
            "fields": [
                {"name": "size", "type": "number", "label": "Size"},
                {"name": "colorway", "type": "text", "label": "Colorway"},
            ]
        },
    )


@pytest.fixture
def collection_item(user, collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=collection_type,
        name="Air Jordan 1 Bred",
        purchase_price=Decimal("170.00"),
        current_market_value=Decimal("350.00"),
        custom_fields={"size": 10, "colorway": "Black/Red"},
    )
