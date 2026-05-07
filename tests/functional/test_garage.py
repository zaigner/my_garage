"""
Functional smoke tests for garage/vehicle URL patterns (Phase 5).

/garage/ redirects to the automobiles collection list.
/garage/<id>/ is a smart permalink redirect — finds the migrated DynamicCollectionItem
by source_vehicle_id and forwards to collections:collection_item_detail.
"""

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


class TestGarageListRedirect:
    def test_garage_view_redirects_to_collection(self, auth_client):
        """Phase 4: /garage/ now redirects to the automobiles collection list."""
        response = auth_client.get("/garage/")
        assert response.status_code == 302
        assert response["Location"] == "/collections/automobiles/items/"

    def test_garage_redirects_unauthenticated(self):
        response = Client().get("/garage/")
        assert response.status_code == 302


class TestLegacyVehicleDetailRedirect:
    def test_migrated_vehicle_redirects_to_collection_item(
        self, auth_client, migrated_vehicle_item
    ):
        """Legacy /garage/<source_vehicle_id>/ redirects to collection item detail."""
        source_id = migrated_vehicle_item.custom_fields["source_vehicle_id"]
        response = auth_client.get(f"/garage/{source_id}/")
        assert response.status_code == 302
        assert (
            f"/collections/automobiles/items/{migrated_vehicle_item.id}/"
            in response["Location"]
        )

    def test_unmigrated_vehicle_returns_404(self, auth_client, automobiles_type):
        """An ID with no matching source_vehicle_id raises Http404."""
        response = auth_client.get("/garage/99999/")
        assert response.status_code == 404

    def test_legacy_vehicle_detail_requires_login(self, migrated_vehicle_item):
        source_id = migrated_vehicle_item.custom_fields["source_vehicle_id"]
        response = Client().get(f"/garage/{source_id}/")
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]
