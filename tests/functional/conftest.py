"""
Shared fixtures for functional (HTTP smoke) tests.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    ServiceRecord,
    Timepiece,
    Vehicle,
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
def vehicle(user):
    v = Vehicle.objects.create(
        owner=user,
        make="Toyota",
        model="Tacoma",
        year=2021,
        mileage=15000,
        purchase_price=Decimal("38000.00"),
        current_market_value=Decimal("40000.00"),
    )
    ServiceRecord.objects.create(
        vehicle=v,
        date=date(2023, 3, 10),
        vendor="Toyota Dealer",
        description="Oil change",
        category="MAINTENANCE",
        total_cost=Decimal("80.00"),
        is_verified=True,
    )
    return v


@pytest.fixture
def service_record(vehicle):
    return vehicle.services.first()


@pytest.fixture
def timepiece(user):
    return Timepiece.objects.create(
        owner=user,
        brand="Seiko",
        model="Prospex",
        reference_number="SPB143J1",
        year=2021,
        movement_type="AUTOMATIC",
        case_material="Stainless Steel",
        dial_color="Blue",
        complications=[],
        has_box=True,
        has_papers=False,
        purchase_price=Decimal("500.00"),
        current_market_value=Decimal("550.00"),
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
