"""
Functional smoke tests for timepiece views.
"""
import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


class TestTimepieceViewsAuthenticated:
    def test_timepiece_list(self, auth_client):
        response = auth_client.get("/timepieces/")
        assert response.status_code == 200

    def test_timepiece_winder(self, auth_client):
        response = auth_client.get("/timepieces/winder/")
        assert response.status_code == 200

    def test_timepiece_detail(self, auth_client, timepiece):
        response = auth_client.get(f"/timepieces/{timepiece.id}/")
        assert response.status_code == 200


class TestTimepieceViewsUnauthenticated:
    def test_timepiece_list_redirects(self):
        response = Client().get("/timepieces/")
        assert response.status_code == 302

    def test_timepiece_detail_redirects(self, timepiece):
        response = Client().get(f"/timepieces/{timepiece.id}/")
        assert response.status_code == 302
