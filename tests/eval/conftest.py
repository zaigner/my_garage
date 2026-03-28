"""
Eval suite conftest — shared fixtures for the golden dataset evaluation tests.
"""
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model

from my_garage.models import (
    CollectionType,
    DynamicCollectionItem,
    ServiceRecord,
    Timepiece,
    Vehicle,
)
from my_garage.services import ContextService

User = get_user_model()

GOLDEN_DATASET_PATH = Path(__file__).parent / "golden_dataset.json"


@pytest.fixture(scope="module")
def golden_dataset():
    with open(GOLDEN_DATASET_PATH) as f:
        return json.load(f)


@pytest.fixture
def eval_user(db):
    return User.objects.create_user(username="eval_user", password="eval")


@pytest.fixture
def eval_vehicle(eval_user):
    v = Vehicle.objects.create(
        owner=eval_user,
        make="Porsche",
        model="911",
        year=2019,
        trim="Carrera S",
        vin="WP0AB2A91KS123456",
        exterior_color="Guards Red",
        mileage=12000,
        purchase_price=Decimal("85000.00"),
        current_market_value=Decimal("92000.00"),
        specs={"engine": "3.0L Twin-Turbo Flat-6", "horsepower": "443"},
        notes="One owner, all service records.",
    )
    ServiceRecord.objects.create(
        vehicle=v,
        date=date(2023, 1, 15),
        vendor="Porsche of Austin",
        description="Annual service and oil change",
        category="MAINTENANCE",
        total_cost=Decimal("1200.00"),
        is_verified=True,
    )
    ServiceRecord.objects.create(
        vehicle=v,
        date=date(2023, 6, 1),
        vendor="Porsche of Austin",
        description="Brake fluid flush",
        category="MAINTENANCE",
        total_cost=Decimal("350.00"),
        is_verified=True,
    )
    return v


@pytest.fixture
def eval_timepiece(eval_user):
    return Timepiece.objects.create(
        owner=eval_user,
        brand="Rolex",
        model="Submariner",
        reference_number="126610LN",
        serial_number="SN123456",
        year=2022,
        movement_type="AUTOMATIC",
        case_material="Oystersteel",
        dial_color="Black",
        complications=["Date"],
        has_box=True,
        has_papers=True,
        condition_grade="Mint",
        purchase_price=Decimal("13500.00"),
        current_market_value=Decimal("14800.00"),
    )


@pytest.fixture
def eval_collection_type(eval_user):
    return CollectionType.objects.create(
        owner=eval_user,
        name="Wine Collection",
        slug="wine-collection",
        field_schema={
            "fields": [
                {"name": "vintage", "type": "number", "label": "Vintage Year"},
                {"name": "region", "type": "text", "label": "Region"},
                {"name": "producer", "type": "text", "label": "Producer"},
            ]
        },
    )


@pytest.fixture
def eval_collection_item(eval_user, eval_collection_type):
    return DynamicCollectionItem.objects.create(
        owner=eval_user,
        collection_type=eval_collection_type,
        name="2015 Opus One",
        purchase_price=Decimal("350.00"),
        current_market_value=Decimal("420.00"),
        custom_fields={
            "vintage": 2015,
            "region": "Napa Valley",
            "producer": "Opus One",
        },
        notes="Perfect condition, stored at 55°F.",
    )


@pytest.fixture
def context_service():
    return ContextService()
