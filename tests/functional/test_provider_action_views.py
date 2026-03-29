"""
Functional tests for provider-dispatched collection item action views:
  - collection_item_detail provider context injection
  - collection_item_trigger_valuation
  - collection_item_trigger_enrich
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

import pytest
from django.test import Client
from django.contrib.auth import get_user_model

from my_garage.models import CollectionType, DynamicCollectionItem

User = get_user_model()

pytestmark = pytest.mark.django_db


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def user(db):
    return User.objects.create_user(username="action_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def vehicle_collection(user):
    return CollectionType.objects.create(
        owner=user,
        name="Automobiles",
        slug="automobiles",
        service_provider_key="vehicle",
        field_schema={"fields": []},
    )


@pytest.fixture
def timepiece_collection(user):
    return CollectionType.objects.create(
        owner=user,
        name="Horology Salon",
        slug="horology-salon",
        service_provider_key="timepiece",
        field_schema={"fields": []},
    )


@pytest.fixture
def default_collection(user):
    return CollectionType.objects.create(
        owner=user,
        name="Sneakers",
        slug="sneakers",
        service_provider_key="default",
        field_schema={"fields": []},
    )


@pytest.fixture
def vehicle_item(user, vehicle_collection):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=vehicle_collection,
        name="2021 Toyota Tacoma",
        purchase_price=Decimal("38000.00"),
        current_market_value=Decimal("40000.00"),
        custom_fields={
            "make": "Toyota",
            "model": "Tacoma",
            "year": 2021,
            "vin": "1NXBR32E85Z396567",
        },
    )


@pytest.fixture
def timepiece_item(user, timepiece_collection):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=timepiece_collection,
        name="Rolex Submariner",
        purchase_price=Decimal("9000.00"),
        current_market_value=Decimal("12000.00"),
        custom_fields={
            "brand": "Rolex",
            "watch_model": "Submariner",
            "reference_number": "116610LN",
            "condition_grade": "EXCELLENT",
            "has_box": True,
            "has_papers": True,
        },
    )


@pytest.fixture
def default_item(user, default_collection):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=default_collection,
        name="Nike Air Jordan 1",
        purchase_price=Decimal("170.00"),
        custom_fields={},
    )


# ── Provider context injection (detail view) ──────────────────────────────────


class TestProviderContextInDetailView:
    def test_vehicle_detail_shows_valuation_button(self, auth_client, vehicle_item):
        slug = vehicle_item.collection_type.slug
        with patch(
            "my_garage.services.collection_services.vehicle.VehicleCollectionServices.get_detail_context",
            return_value={"show_valuation_button": True, "show_vin_enrich_button": True,
                          "show_photo_refresh_button": False, "valuation_history": []},
        ):
            response = auth_client.get(
                f"/collections/{slug}/items/{vehicle_item.id}/"
            )
        assert response.status_code == 200
        assert b"Refresh Valuation" in response.content
        assert b"Decode VIN" in response.content

    def test_vehicle_detail_hides_buttons_when_provider_returns_false(
        self, auth_client, vehicle_item
    ):
        slug = vehicle_item.collection_type.slug
        with patch(
            "my_garage.services.collection_services.vehicle.VehicleCollectionServices.get_detail_context",
            return_value={"show_valuation_button": False, "show_vin_enrich_button": False,
                          "show_photo_refresh_button": False, "valuation_history": []},
        ):
            response = auth_client.get(
                f"/collections/{slug}/items/{vehicle_item.id}/"
            )
        assert response.status_code == 200
        assert b"Refresh Valuation" not in response.content
        assert b"Decode VIN" not in response.content

    def test_default_collection_shows_no_action_buttons(self, auth_client, default_item):
        slug = default_item.collection_type.slug
        response = auth_client.get(
            f"/collections/{slug}/items/{default_item.id}/"
        )
        assert response.status_code == 200
        assert b"Refresh Valuation" not in response.content
        assert b"Decode VIN" not in response.content

    def test_timepiece_detail_shows_valuation_button(self, auth_client, timepiece_item):
        slug = timepiece_item.collection_type.slug
        with patch(
            "my_garage.services.collection_services.timepiece.TimepieceCollectionServices.get_detail_context",
            return_value={"show_valuation_button": True, "show_winder_link": False,
                          "winder_items": [], "has_box": True, "has_papers": True,
                          "valuation_history": []},
        ):
            response = auth_client.get(
                f"/collections/{slug}/items/{timepiece_item.id}/"
            )
        assert response.status_code == 200
        assert b"Refresh Valuation" in response.content

    def test_timepiece_detail_shows_chronovault_when_winder_link_true(
        self, auth_client, timepiece_item
    ):
        slug = timepiece_item.collection_type.slug
        with patch(
            "my_garage.services.collection_services.timepiece.TimepieceCollectionServices.get_detail_context",
            return_value={"show_valuation_button": False, "show_winder_link": True,
                          "winder_items": [True, True, None, None, None, None, None, None],
                          "has_box": True, "has_papers": True, "valuation_history": []},
        ):
            response = auth_client.get(
                f"/collections/{slug}/items/{timepiece_item.id}/"
            )
        assert response.status_code == 200
        assert b"ChronoVault" in response.content

    def test_valuation_history_rendered_when_present(self, auth_client, vehicle_item):
        from my_garage.models import GenericValuationHistory
        slug = vehicle_item.collection_type.slug
        entry = GenericValuationHistory.objects.create(
            item=vehicle_item, value=Decimal("39500.00"), raw_data={}
        )
        with patch(
            "my_garage.services.collection_services.vehicle.VehicleCollectionServices.get_detail_context",
            return_value={"show_valuation_button": True, "show_vin_enrich_button": False,
                          "show_photo_refresh_button": False, "valuation_history": [entry]},
        ):
            response = auth_client.get(
                f"/collections/{slug}/items/{vehicle_item.id}/"
            )
        assert response.status_code == 200
        assert b"Valuation History" in response.content
        assert b"39500" in response.content


# ── Trigger Valuation view ────────────────────────────────────────────────────


class TestTriggerValuationView:
    def test_post_queues_task_and_redirects(self, auth_client, vehicle_item):
        slug = vehicle_item.collection_type.slug
        with patch(
            "my_garage.views.task_collection_item_refresh_valuation"
        ) as mock_task:
            response = auth_client.post(
                f"/collections/{slug}/items/{vehicle_item.id}/refresh-valuation/"
            )
        assert response.status_code == 302
        assert response["Location"] == (
            f"/collections/{slug}/items/{vehicle_item.id}/"
        )
        mock_task.delay.assert_called_once_with(vehicle_item.id)

    def test_post_unsupported_provider_shows_warning(self, auth_client, default_item):
        slug = default_item.collection_type.slug
        with patch(
            "my_garage.views.task_collection_item_refresh_valuation"
        ) as mock_task:
            response = auth_client.post(
                f"/collections/{slug}/items/{default_item.id}/refresh-valuation/"
            )
        assert response.status_code == 302
        mock_task.delay.assert_not_called()

    def test_get_redirects_to_detail_without_queuing(self, auth_client, vehicle_item):
        slug = vehicle_item.collection_type.slug
        with patch(
            "my_garage.views.task_collection_item_refresh_valuation"
        ) as mock_task:
            response = auth_client.get(
                f"/collections/{slug}/items/{vehicle_item.id}/refresh-valuation/"
            )
        assert response.status_code == 302
        mock_task.delay.assert_not_called()

    def test_unauthenticated_redirects_to_login(self, vehicle_item):
        slug = vehicle_item.collection_type.slug
        response = Client().post(
            f"/collections/{slug}/items/{vehicle_item.id}/refresh-valuation/"
        )
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_wrong_owner_returns_404(self, vehicle_item):
        other_user = User.objects.create_user(username="other_valuation", password="x")
        other_client = Client()
        other_client.force_login(other_user)
        slug = vehicle_item.collection_type.slug
        response = other_client.post(
            f"/collections/{slug}/items/{vehicle_item.id}/refresh-valuation/"
        )
        assert response.status_code == 404


# ── Trigger Enrich view ───────────────────────────────────────────────────────


class TestTriggerEnrichView:
    def test_post_queues_task_and_redirects(self, auth_client, vehicle_item):
        slug = vehicle_item.collection_type.slug
        with patch(
            "my_garage.views.task_collection_item_enrich"
        ) as mock_task:
            response = auth_client.post(
                f"/collections/{slug}/items/{vehicle_item.id}/enrich/"
            )
        assert response.status_code == 302
        assert response["Location"] == (
            f"/collections/{slug}/items/{vehicle_item.id}/"
        )
        mock_task.delay.assert_called_once_with(vehicle_item.id)

    def test_post_unsupported_provider_shows_warning(self, auth_client, default_item):
        slug = default_item.collection_type.slug
        with patch(
            "my_garage.views.task_collection_item_enrich"
        ) as mock_task:
            response = auth_client.post(
                f"/collections/{slug}/items/{default_item.id}/enrich/"
            )
        assert response.status_code == 302
        mock_task.delay.assert_not_called()

    def test_timepiece_provider_does_not_support_enrich(
        self, auth_client, timepiece_item
    ):
        """TimepieceCollectionServices.supports_enrichment() returns False."""
        slug = timepiece_item.collection_type.slug
        with patch(
            "my_garage.views.task_collection_item_enrich"
        ) as mock_task:
            response = auth_client.post(
                f"/collections/{slug}/items/{timepiece_item.id}/enrich/"
            )
        assert response.status_code == 302
        mock_task.delay.assert_not_called()

    def test_get_redirects_to_detail_without_queuing(self, auth_client, vehicle_item):
        slug = vehicle_item.collection_type.slug
        with patch(
            "my_garage.views.task_collection_item_enrich"
        ) as mock_task:
            response = auth_client.get(
                f"/collections/{slug}/items/{vehicle_item.id}/enrich/"
            )
        assert response.status_code == 302
        mock_task.delay.assert_not_called()

    def test_unauthenticated_redirects_to_login(self, vehicle_item):
        slug = vehicle_item.collection_type.slug
        response = Client().post(
            f"/collections/{slug}/items/{vehicle_item.id}/enrich/"
        )
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_wrong_owner_returns_404(self, vehicle_item):
        other_user = User.objects.create_user(username="other_enrich", password="x")
        other_client = Client()
        other_client.force_login(other_user)
        slug = vehicle_item.collection_type.slug
        response = other_client.post(
            f"/collections/{slug}/items/{vehicle_item.id}/enrich/"
        )
        assert response.status_code == 404
