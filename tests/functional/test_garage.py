"""
Functional smoke tests for garage/vehicle views.
Catches 500 errors and URL argument mismatches at the HTTP level.
"""
import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


class TestGarageViewsAuthenticated:
    def test_garage_view(self, auth_client):
        response = auth_client.get("/garage/")
        assert response.status_code == 200

    def test_vehicle_detail(self, auth_client, vehicle):
        response = auth_client.get(f"/garage/{vehicle.id}/")
        assert response.status_code == 200

    def test_vehicle_projects_kanban(self, auth_client, vehicle):
        response = auth_client.get(f"/garage/{vehicle.id}/projects/kanban/")
        assert response.status_code == 200

    def test_add_service_record_get(self, auth_client, vehicle):
        response = auth_client.get(f"/garage/{vehicle.id}/add-service/")
        assert response.status_code == 200

    def test_add_upgrade_get(self, auth_client, vehicle):
        response = auth_client.get(f"/garage/{vehicle.id}/add-project/")
        assert response.status_code == 200

    def test_service_record_edit_get(self, auth_client, service_record):
        response = auth_client.get(f"/garage/service/{service_record.id}/edit/")
        assert response.status_code == 200

    def test_service_record_delete_get(self, auth_client, service_record):
        response = auth_client.get(f"/garage/service/{service_record.id}/delete/")
        assert response.status_code == 200


class TestGarageViewsUnauthenticated:
    def test_garage_redirects(self):
        response = Client().get("/garage/")
        assert response.status_code == 302

    def test_vehicle_detail_redirects(self, vehicle):
        response = Client().get(f"/garage/{vehicle.id}/")
        assert response.status_code == 302

    def test_kanban_redirects(self, vehicle):
        response = Client().get(f"/garage/{vehicle.id}/projects/kanban/")
        assert response.status_code == 302

    def test_service_edit_redirects(self, service_record):
        response = Client().get(f"/garage/service/{service_record.id}/edit/")
        assert response.status_code == 302
