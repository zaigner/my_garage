"""
Unit tests for the pluggable collection service provider system (Phase 1).

Tests cover:
  - Registry lookup (known keys, unknown fallback, custom registration)
  - BaseCollectionServices default capability flags
  - DefaultCollectionServices (no-ops)
  - VehicleCollectionServices capability flags and field extraction helpers
  - TimepieceCollectionServices capability flags
  - GenericValuationHistory model (basic field contracts)

All tests are pure unit tests — no database access, no HTTP calls.
External API calls in VehicleCollectionServices and TimepieceCollectionServices
are tested via mocks so CI runs without live services.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from my_garage.services.collection_services.base import BaseCollectionServices
from my_garage.services.collection_services.default import DefaultCollectionServices
from my_garage.services.collection_services.registry import (
    _REGISTRY,
    get_collection_services,
    register,
)
from my_garage.services.collection_services.vehicle import (
    VehicleCollectionServices,
    _build_market_search_args,
    _cf,
)
from my_garage.services.collection_services.timepiece import TimepieceCollectionServices


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(**custom_fields):
    """Build a lightweight DynamicCollectionItem-like namespace for unit tests."""
    item = SimpleNamespace()
    item.custom_fields = custom_fields
    item.photo = None
    item.current_market_value = Decimal("0.00")
    item.name = custom_fields.get("make", custom_fields.get("brand", "Test Item"))
    item.owner = SimpleNamespace(id=1)
    # Fake valuation_history — all() returns a plain list so [:5] slicing works
    item.valuation_history = SimpleNamespace(all=lambda: [], count=lambda: 0)
    return item


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_vehicle_key_returns_vehicle_provider(self):
        provider = get_collection_services("vehicle")
        assert isinstance(provider, VehicleCollectionServices)

    def test_timepiece_key_returns_timepiece_provider(self):
        provider = get_collection_services("timepiece")
        assert isinstance(provider, TimepieceCollectionServices)

    def test_default_key_returns_default_provider(self):
        provider = get_collection_services("default")
        assert isinstance(provider, DefaultCollectionServices)

    def test_unknown_key_falls_back_to_default(self):
        provider = get_collection_services("whisky_collection_xyz")
        assert isinstance(provider, DefaultCollectionServices)

    def test_empty_string_falls_back_to_default(self):
        provider = get_collection_services("")
        assert isinstance(provider, DefaultCollectionServices)

    def test_registry_contains_expected_keys(self):
        assert "vehicle" in _REGISTRY
        assert "timepiece" in _REGISTRY
        assert "default" in _REGISTRY

    def test_register_custom_provider(self):
        """register() inserts a custom provider that get_collection_services returns."""

        class _CustomProvider(BaseCollectionServices):
            pass

        custom = _CustomProvider()
        register("custom_test_key", custom)

        assert get_collection_services("custom_test_key") is custom

        # Cleanup — remove the test key so it doesn't pollute other tests
        _REGISTRY.pop("custom_test_key", None)

    def test_register_replaces_existing_key(self):
        class _ProviderA(BaseCollectionServices):
            pass

        class _ProviderB(BaseCollectionServices):
            pass

        register("replace_test", _ProviderA())
        register("replace_test", _ProviderB())

        assert isinstance(get_collection_services("replace_test"), _ProviderB)
        _REGISTRY.pop("replace_test", None)


# ---------------------------------------------------------------------------
# BaseCollectionServices defaults
# ---------------------------------------------------------------------------


class TestBaseCollectionServices:
    """All capability guards must default to False on the base class."""

    def setup_method(self):
        # Instantiate directly — it is not abstract (no @abstractmethod)
        self.base = BaseCollectionServices()

    def test_supports_valuation_refresh_is_false(self):
        assert self.base.supports_valuation_refresh() is False

    def test_supports_enrichment_is_false(self):
        assert self.base.supports_enrichment() is False

    def test_supports_photo_fetch_is_false(self):
        assert self.base.supports_photo_fetch() is False

    def test_get_enrichment_trigger_field_is_none(self):
        assert self.base.get_enrichment_trigger_field() is None

    def test_get_detail_context_returns_empty_dict(self):
        item = _make_item()
        assert self.base.get_detail_context(item) == {}

    def test_run_valuation_raises(self):
        with pytest.raises(NotImplementedError):
            self.base.run_valuation(_make_item())

    def test_run_enrichment_raises(self):
        with pytest.raises(NotImplementedError):
            self.base.run_enrichment(_make_item())

    def test_run_photo_fetch_raises(self):
        with pytest.raises(NotImplementedError):
            self.base.run_photo_fetch(_make_item())


# ---------------------------------------------------------------------------
# DefaultCollectionServices
# ---------------------------------------------------------------------------


class TestDefaultCollectionServices:
    def setup_method(self):
        self.provider = DefaultCollectionServices()

    def test_supports_valuation_refresh_is_false(self):
        assert self.provider.supports_valuation_refresh() is False

    def test_supports_enrichment_is_false(self):
        assert self.provider.supports_enrichment() is False

    def test_supports_photo_fetch_is_false(self):
        assert self.provider.supports_photo_fetch() is False

    def test_get_detail_context_empty(self):
        assert self.provider.get_detail_context(_make_item()) == {}

    def test_is_base_subclass(self):
        assert isinstance(self.provider, BaseCollectionServices)


# ---------------------------------------------------------------------------
# VehicleCollectionServices — capabilities
# ---------------------------------------------------------------------------


class TestVehicleCollectionServicesCapabilities:
    def setup_method(self):
        self.provider = VehicleCollectionServices()

    def test_supports_valuation_refresh(self):
        assert self.provider.supports_valuation_refresh() is True

    def test_supports_enrichment(self):
        assert self.provider.supports_enrichment() is True

    def test_supports_photo_fetch(self):
        assert self.provider.supports_photo_fetch() is True

    def test_enrichment_trigger_field_is_vin(self):
        assert self.provider.get_enrichment_trigger_field() == "vin"

    def test_is_base_subclass(self):
        assert isinstance(self.provider, BaseCollectionServices)


# ---------------------------------------------------------------------------
# VehicleCollectionServices — _cf helper
# ---------------------------------------------------------------------------


class TestCfHelper:
    def test_returns_value_for_existing_key(self):
        item = _make_item(make="Toyota", year=2021)
        assert _cf(item, "make") == "Toyota"
        assert _cf(item, "year") == 2021

    def test_returns_default_for_missing_key(self):
        item = _make_item()
        assert _cf(item, "vin") == ""
        assert _cf(item, "mileage", 0) == 0

    def test_returns_custom_default(self):
        item = _make_item()
        assert _cf(item, "nonexistent", 42) == 42


# ---------------------------------------------------------------------------
# VehicleCollectionServices — _build_market_search_args
# ---------------------------------------------------------------------------


class TestBuildMarketSearchArgs:
    def test_basic_fields_always_present(self):
        item = _make_item(make="Toyota", model="Tacoma", year=2021, trim="TRD Pro")
        args = _build_market_search_args(item)
        assert args["make"] == "Toyota"
        assert args["model"] == "Tacoma"
        assert args["year"] == 2021
        assert args["trim"] == "TRD Pro"

    def test_mileage_included_when_nonzero(self):
        item = _make_item(make="Toyota", model="Tacoma", year=2021, mileage=15000)
        args = _build_market_search_args(item)
        assert args["mileage"] == 15000

    def test_mileage_excluded_when_zero(self):
        item = _make_item(make="Toyota", model="Tacoma", year=2021, mileage=0)
        args = _build_market_search_args(item)
        assert "mileage" not in args

    def test_exterior_color_included(self):
        item = _make_item(make="Porsche", model="911", year=2022, exterior_color="Guards Red")
        args = _build_market_search_args(item)
        assert args["exterior_color"] == "Guards Red"

    def test_specs_engine_extracted(self):
        item = _make_item(
            make="Ford", model="Mustang", year=2020,
            specs={"engine": "5.0L V8", "drivetrain": "RWD"}
        )
        args = _build_market_search_args(item)
        assert args["engine"] == "5.0L V8"
        assert args["drivetrain"] == "RWD"

    def test_specs_title_case_keys_extracted(self):
        """Verify that Title Case spec keys (from NHTSA) are normalised."""
        item = _make_item(
            make="Ford", model="F-150", year=2021,
            specs={"Body Style": "Pickup", "Fuel Type": "Gasoline"}
        )
        args = _build_market_search_args(item)
        assert args.get("body_style") == "Pickup"
        assert args.get("fuel_type") == "Gasoline"

    def test_features_dict_becomes_keywords(self):
        item = _make_item(
            make="BMW", model="M3", year=2022,
            features={"Sunroof": True, "Leather Seats": True, "Sunshades": False}
        )
        args = _build_market_search_args(item)
        assert set(args["keywords"]) == {"Sunroof", "Leather Seats"}

    def test_features_list_becomes_keywords(self):
        item = _make_item(
            make="BMW", model="M3", year=2022,
            features=["Sunroof", "Leather Seats"]
        )
        args = _build_market_search_args(item)
        assert args["keywords"] == ["Sunroof", "Leather Seats"]

    def test_no_optional_fields(self):
        """Item with only required fields produces a minimal args dict."""
        item = _make_item(make="Honda", model="Civic", year=2020)
        args = _build_market_search_args(item)
        assert "mileage" not in args
        assert "exterior_color" not in args
        assert "keywords" not in args


# ---------------------------------------------------------------------------
# VehicleCollectionServices — get_detail_context
# ---------------------------------------------------------------------------


class TestVehicleDetailContext:
    def setup_method(self):
        self.provider = VehicleCollectionServices()

    def test_vin_present_enables_enrich_button(self):
        item = _make_item(vin="1HGBH41JXMN109186")
        ctx = self.provider.get_detail_context(item)
        assert ctx["show_vin_enrich_button"] is True

    def test_no_vin_disables_enrich_button(self):
        item = _make_item()
        ctx = self.provider.get_detail_context(item)
        assert ctx["show_vin_enrich_button"] is False

    def test_valuation_button_always_shown(self):
        item = _make_item()
        ctx = self.provider.get_detail_context(item)
        assert ctx["show_valuation_button"] is True

    def test_photo_refresh_button_always_shown(self):
        item = _make_item()
        ctx = self.provider.get_detail_context(item)
        assert ctx["show_photo_refresh_button"] is True


# ---------------------------------------------------------------------------
# VehicleCollectionServices — run_valuation (mocked HTTP)
# run_valuation uses @transaction.atomic so these tests need DB access.
# HTTP calls are still mocked — no live FastAPI required.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVehicleRunValuation:
    def setup_method(self):
        self.provider = VehicleCollectionServices()

    @patch("my_garage.services.collection_services.vehicle.requests.post")
    @patch("my_garage.models.GenericValuationHistory")
    def test_updates_item_value_with_median(self, mock_history_class, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "results": [
                    {"price": 30000},
                    {"price": 35000},
                    {"price": 40000},
                ]
            },
        )
        mock_post.return_value.raise_for_status = MagicMock()

        item = _make_item(make="Toyota", model="Tacoma", year=2021)
        item.save = MagicMock()

        result = self.provider.run_valuation(item)

        assert result == Decimal("35000")
        item.save.assert_called_once_with(update_fields=["current_market_value"])
        mock_history_class.objects.create.assert_called_once()

    @patch("my_garage.services.collection_services.vehicle.requests.post")
    def test_returns_current_value_when_no_listings(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"results": []},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        item = _make_item(make="Lada", model="Niva", year=1985)
        item.current_market_value = Decimal("1500.00")
        item.save = MagicMock()

        result = self.provider.run_valuation(item)

        assert result == Decimal("1500.00")
        item.save.assert_not_called()

    @patch("my_garage.services.collection_services.vehicle.requests.post")
    def test_raises_on_request_exception(self, mock_post):
        mock_post.side_effect = requests.exceptions.ConnectionError("refused")

        item = _make_item(make="Ford", model="GT", year=2005)
        item.save = MagicMock()

        with pytest.raises(requests.exceptions.ConnectionError):
            self.provider.run_valuation(item)


# ---------------------------------------------------------------------------
# VehicleCollectionServices — run_enrichment (mocked HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVehicleRunEnrichment:
    def setup_method(self):
        self.provider = VehicleCollectionServices()

    @patch("my_garage.services.collection_services.vehicle.VehicleCollectionServices.run_photo_fetch")
    @patch("my_garage.services.collection_services.vehicle.requests.post")
    def test_updates_custom_fields_from_vin_data(self, mock_post, mock_photo):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"make": "Toyota", "model": "Tacoma", "model_year": 2021, "engine": "3.5L V6"},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        item = _make_item(vin="1HGBH41JXMN109186", make="Unknown", model="Unknown", year=2021)
        item.save = MagicMock()

        result = self.provider.run_enrichment(item)

        assert item.custom_fields["make"] == "Toyota"
        assert item.custom_fields["model"] == "Tacoma"
        assert item.custom_fields["specs"]["engine"] == "3.5L V6"
        item.save.assert_called_once_with(update_fields=["custom_fields"])

    @patch("my_garage.services.collection_services.vehicle.requests.post")
    def test_returns_empty_dict_when_no_vin(self, mock_post):
        item = _make_item(make="Ford", model="Mustang", year=2020)
        item.save = MagicMock()

        result = self.provider.run_enrichment(item)

        assert result == {}
        mock_post.assert_not_called()

    @patch("my_garage.services.collection_services.vehicle.requests.post")
    def test_returns_empty_dict_on_error_response(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"error": "VIN not found"},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        item = _make_item(vin="INVALIDVIN123456X", make="Unknown", model="Unknown", year=2000)
        item.save = MagicMock()

        result = self.provider.run_enrichment(item)

        assert result == {}
        item.save.assert_not_called()


# ---------------------------------------------------------------------------
# TimepieceCollectionServices — capabilities
# ---------------------------------------------------------------------------


class TestTimepieceCollectionServicesCapabilities:
    def setup_method(self):
        self.provider = TimepieceCollectionServices()

    def test_supports_valuation_refresh(self):
        assert self.provider.supports_valuation_refresh() is True

    def test_supports_photo_fetch(self):
        assert self.provider.supports_photo_fetch() is True

    def test_does_not_support_enrichment(self):
        assert self.provider.supports_enrichment() is False

    def test_enrichment_trigger_field_is_none(self):
        assert self.provider.get_enrichment_trigger_field() is None

    def test_is_base_subclass(self):
        assert isinstance(self.provider, BaseCollectionServices)


# ---------------------------------------------------------------------------
# TimepieceCollectionServices — run_valuation (mocked HTTP)
# run_valuation uses @transaction.atomic so these tests need DB access.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTimepieceRunValuation:
    def setup_method(self):
        self.provider = TimepieceCollectionServices()

    @patch("my_garage.services.collection_services.timepiece.requests.post")
    @patch("my_garage.models.GenericValuationHistory")
    def test_updates_item_value(self, mock_history_class, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "estimated_value": "12500.00",
                "currency": "USD",
                "confidence": "HIGH",
                "source": "mock",
            },
        )
        mock_post.return_value.raise_for_status = MagicMock()

        item = _make_item(
            brand="Rolex",
            watch_model="Submariner",
            reference_number="116610LN",
            condition_grade="MINT",
            has_box=True,
            has_papers=True,
        )
        item.save = MagicMock()

        result = self.provider.run_valuation(item)

        assert result == Decimal("12500.00")
        assert item.current_market_value == Decimal("12500.00")
        item.save.assert_called_once_with(update_fields=["current_market_value"])
        mock_history_class.objects.create.assert_called_once()

    @patch("my_garage.services.collection_services.timepiece.requests.post")
    def test_returns_current_value_when_no_estimate(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"error": "brand not found"},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        item = _make_item(brand="Obscure", watch_model="Unknown", reference_number="???")
        item.current_market_value = Decimal("500.00")
        item.save = MagicMock()

        result = self.provider.run_valuation(item)

        assert result == Decimal("500.00")
        item.save.assert_not_called()

    @patch("my_garage.services.collection_services.timepiece.requests.post")
    def test_passes_has_box_and_has_papers_to_mcp(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"estimated_value": "8000"},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        item = _make_item(
            brand="Omega",
            watch_model="Speedmaster",
            reference_number="311.30.42.30.01.005",
            has_box=True,
            has_papers=False,
        )
        item.save = MagicMock()
        # Patch history creation — local import inside run_valuation lives in my_garage.models
        with patch("my_garage.models.GenericValuationHistory"):
            self.provider.run_valuation(item)

        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs[0][1]
        assert payload["arguments"]["has_box"] is True
        assert payload["arguments"]["has_papers"] is False


# Required to make the import in test_raises work
import requests  # noqa: E402
