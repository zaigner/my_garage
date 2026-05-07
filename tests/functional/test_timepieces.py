"""
Functional smoke tests for timepiece URL patterns (Phase 5).

/timepieces/ redirects to the horology-salon collection list.
/timepieces/<id>/ is a smart permalink redirect — finds the migrated
DynamicCollectionItem by source_timepiece_id and forwards to
collections:collection_item_detail.
"""

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


class TestTimepieceListRedirect:
    def test_timepiece_list_redirects_to_collection(self, auth_client):
        """Phase 4: /timepieces/ now redirects to the horology-salon collection list."""
        response = auth_client.get("/timepieces/")
        assert response.status_code == 302
        assert response["Location"] == "/collections/horology-salon/items/"

    def test_timepiece_list_redirects_unauthenticated(self):
        response = Client().get("/timepieces/")
        assert response.status_code == 302


class TestLegacyTimepieceDetailRedirect:
    def test_migrated_timepiece_redirects_to_collection_item(
        self, auth_client, migrated_timepiece_item
    ):
        """Legacy /timepieces/<source_timepiece_id>/ redirects to collection item
        detail."""
        source_id = migrated_timepiece_item.custom_fields["source_timepiece_id"]
        response = auth_client.get(f"/timepieces/{source_id}/")
        assert response.status_code == 302
        assert (
            f"/collections/horology-salon/items/{migrated_timepiece_item.id}/"
            in response["Location"]
        )

    def test_unmigrated_timepiece_returns_404(self, auth_client, horology_type):
        """An ID with no matching source_timepiece_id raises Http404."""
        response = auth_client.get("/timepieces/99999/")
        assert response.status_code == 404

    def test_legacy_timepiece_detail_requires_login(self, migrated_timepiece_item):
        source_id = migrated_timepiece_item.custom_fields["source_timepiece_id"]
        response = Client().get(f"/timepieces/{source_id}/")
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]
