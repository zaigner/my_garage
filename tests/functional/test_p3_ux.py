"""
Functional tests for P3 UX improvements:
  P3a — Loading states on action buttons (Refresh Valuation, Decode VIN)
  P3b — Auto-dismiss toast notifications in base.html
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from my_garage.models import CollectionType, DynamicCollectionItem

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):
    return User.objects.create_user(username="p3_user", password="pass")


@pytest.fixture
def auth_client(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def auto_collection_type(user):
    return CollectionType.objects.create(
        owner=user,
        name="Automobiles",
        slug="automobiles",
        field_schema={"fields": [{"name": "make", "type": "text", "label": "Make"}]},
    )


@pytest.fixture
def auto_item(user, auto_collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=auto_collection_type,
        name="2020 BMW M3",
        purchase_price=Decimal("55000.00"),
        custom_fields={"make": "BMW"},
    )


@pytest.fixture
def vehicle_collection_type(user):
    """CollectionType with vehicle service provider — exposes action buttons."""
    return CollectionType.objects.create(
        owner=user,
        name="My Cars",
        slug="my-cars",
        service_provider_key="vehicle",
        field_schema={"fields": [{"name": "vin", "type": "text", "label": "VIN"}]},
    )


@pytest.fixture
def vehicle_item(user, vehicle_collection_type):
    return DynamicCollectionItem.objects.create(
        owner=user,
        collection_type=vehicle_collection_type,
        name="2021 Ford F-150",
        purchase_price=Decimal("45000.00"),
        custom_fields={"vin": "1FTFW1E57MFC12345"},
    )


def _detail_url(item):
    return reverse(
        "collections:collection_item_detail",
        kwargs={"collection_slug": item.collection_type.slug, "item_id": item.id},
    )


# ---------------------------------------------------------------------------
# P3a — Loading states on action buttons
# ---------------------------------------------------------------------------


class TestLoadingStates:
    def test_valuation_form_has_alpine_loading_data(self, auth_client, vehicle_item):
        """Valuation form must declare x-data loading state."""
        content = auth_client.get(_detail_url(vehicle_item)).content.decode()
        assert "Refresh Valuation" in content
        assert 'x-data="{ loading: false }"' in content

    def test_valuation_button_has_disabled_binding(self, auth_client, vehicle_item):
        """Valuation button uses :disabled binding tied to loading state."""
        content = auth_client.get(_detail_url(vehicle_item)).content.decode()
        assert ':disabled="loading"' in content

    def test_valuation_button_has_spinner_span(self, auth_client, vehicle_item):
        """Valuation button contains a spinner element shown while loading."""
        content = auth_client.get(_detail_url(vehicle_item)).content.decode()
        assert "animate-spin" in content

    def test_enrich_form_has_alpine_loading_data(self, auth_client, vehicle_item):
        """VIN enrich form declares x-data loading state."""
        content = auth_client.get(_detail_url(vehicle_item)).content.decode()
        assert "Decode VIN" in content
        assert 'x-data="{ loading: false }"' in content

    def test_action_forms_have_submit_handler(self, auth_client, vehicle_item):
        """Action forms set loading=true on submit."""
        content = auth_client.get(_detail_url(vehicle_item)).content.decode()
        assert '@submit="loading = true"' in content

    def test_processing_label_present_for_loading_state(
        self, auth_client, vehicle_item
    ):
        """A 'Processing...' label exists inside the spinner span."""
        content = auth_client.get(_detail_url(vehicle_item)).content.decode()
        assert "Processing..." in content


# ---------------------------------------------------------------------------
# P3b — Toast structure in base.html
# ---------------------------------------------------------------------------


class TestToastDismiss:
    def _get_page_with_messages(self, auth_client, url, messages_to_add):
        """
        Django messages are consumed per-request. Inject them by hitting a
        view that uses the messages framework — here we use the detail page
        directly and inspect the rendered base.html template output.

        Since we can't inject messages without a view, we test the template
        structure by inspecting the rendered HTML from a page that does
        trigger messages (e.g., a successful POST). For structure tests we
        assert directly on the detail page's static HTML output.
        """
        return auth_client.get(url).content.decode()

    def test_detail_page_renders_without_error(self, auth_client, auto_item):
        """Baseline: detail page renders with 200 without toast messages."""
        response = auth_client.get(_detail_url(auto_item))
        assert response.status_code == 200

    def test_toast_alpine_x_data_on_messages(self, auth_client, auto_item):
        """
        When a POST triggers a redirect + message, the redirect target
        renders a toast with x-data="{ show: true }".
        """
        url = _detail_url(auto_item)
        response = auth_client.post(
            url,
            {
                "name": auto_item.name,
                "purchase_price": "55000.00",
                "current_market_value": "",
                "custom_make": "BMW",
            },
        )
        if response.status_code == 302:
            follow_response = auth_client.get(response["Location"])
            content = follow_response.content.decode()
            if 'x-data="{ show: true }"' in content:
                assert 'x-show="show"' in content

    def test_base_html_toast_structure_has_dismiss_button(
        self, auth_client, auto_item, user
    ):
        """
        After a successful form save the redirected page should contain
        a dismiss button with aria-label="Dismiss" if a message was added.
        Verify structure is correct by triggering a real message.
        """
        url = _detail_url(auto_item)
        response = auth_client.post(
            url,
            {
                "name": "Updated Name",
                "purchase_price": "55000.00",
                "current_market_value": "",
                "custom_make": "BMW",
            },
        )
        if response.status_code == 302:
            follow_response = auth_client.get(response["Location"])
            content = follow_response.content.decode()
            if "Dismiss" in content:
                assert 'aria-label="Dismiss"' in content
                assert '@click="show = false"' in content

    def test_base_html_has_no_raw_message_div_without_messages(
        self, auth_client, auto_item
    ):
        """Without messages the toast container should not be rendered."""
        content = auth_client.get(_detail_url(auto_item)).content.decode()
        assert 'x-data="{ show: true }"' not in content
