"""
Pydantic models that define the typed shape of context dicts
passed to prompt templates and AI tool calls.

These are plain data containers — no Django ORM, no I/O.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ServiceRecordContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    date: date
    vendor: str
    description: str
    category: str
    total_cost: Decimal
    is_verified: bool


class UpgradeContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    name: str
    brand: str
    status: str
    cost: Decimal
    notes: str


class VehicleContext(BaseModel):
    """Complete context for a single vehicle — used in valuation and condition prompts."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    make: str
    model: str
    year: int
    trim: str
    vin: str | None
    exterior_color: str
    interior_color: str
    transmission: str
    mileage: int
    purchase_price: Decimal | None
    purchase_date: date | None
    current_market_value: Decimal
    specs: dict[str, Any]
    features: dict[str, Any] | list[Any]
    notes: str

    # Aggregated financials (from selectors)
    total_maintenance_cost: Decimal
    total_upgrade_cost: Decimal
    total_investment: Decimal
    equity: Decimal
    is_profitable: bool
    latest_condition_grade: float | None

    # Related records
    service_records: list[ServiceRecordContext] = Field(default_factory=list)
    upgrades: list[UpgradeContext] = Field(default_factory=list)


class TimepieceContext(BaseModel):
    """Complete context for a single timepiece."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    brand: str
    model: str
    reference_number: str
    serial_number: str
    year: int | None
    movement_type: str
    case_material: str
    dial_color: str
    complications: list[str]
    has_box: bool
    has_papers: bool
    condition_grade: str
    purchase_price: Decimal | None
    purchase_date: date | None
    current_market_value: Decimal
    notes: str


class CollectionItemContext(BaseModel):
    """Context for a single dynamic collection item."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    name: str
    collection_type_name: str
    collection_type_slug: str
    purchase_price: Decimal | None
    purchase_date: date | None
    current_market_value: Decimal | None
    custom_fields: dict[str, Any]
    notes: str
    service_record_count: int
    upgrade_count: int


class PortfolioSummary(BaseModel):
    """Aggregated portfolio-level context for the home dashboard."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    vehicle_count: int
    timepiece_count: int
    collection_item_count: int
    total_vehicles_value: Decimal
    total_timepieces_value: Decimal
    total_collections_value: Decimal
    total_portfolio_value: Decimal
    collection_types: list[str] = Field(default_factory=list)
    generated_at: datetime
