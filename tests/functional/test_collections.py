"""
Functional smoke tests for collection views.
"""
import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


class TestCollectionViewsAuthenticated:
    def test_collection_type_list(self, auth_client):
        response = auth_client.get("/collections/")
        assert response.status_code == 200

    def test_collection_list(self, auth_client, collection_type):
        response = auth_client.get(f"/collections/{collection_type.slug}/items/")
        assert response.status_code == 200

    def test_collection_item_detail(self, auth_client, collection_item):
        slug = collection_item.collection_type.slug
        response = auth_client.get(f"/collections/{slug}/items/{collection_item.id}/")
        assert response.status_code == 200

    def test_collection_upgrades_kanban(self, auth_client, collection_type):
        response = auth_client.get(
            f"/collections/{collection_type.slug}/upgrades/kanban/"
        )
        assert response.status_code == 200

    def test_add_collection_item_get(self, auth_client, collection_type):
        response = auth_client.get(f"/collections/{collection_type.slug}/items/add/")
        assert response.status_code == 200


class TestCollectionViewsUnauthenticated:
    def test_collection_list_redirects(self):
        response = Client().get("/collections/")
        assert response.status_code == 302

    def test_collection_items_redirects(self, collection_type):
        response = Client().get(f"/collections/{collection_type.slug}/items/")
        assert response.status_code == 302

    def test_collection_item_detail_redirects(self, collection_item):
        slug = collection_item.collection_type.slug
        response = Client().get(f"/collections/{slug}/items/{collection_item.id}/")
        assert response.status_code == 302
