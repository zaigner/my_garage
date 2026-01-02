"""Tests for my_garage models."""
import pytest
from django.contrib.auth import get_user_model
from my_garage.models import Vehicle

User = get_user_model()

@pytest.mark.django_db
def test_vehicle_creation():
    """Test vehicle creation."""
    user = User.objects.create_user(username='testuser', password='testpass')
    vehicle = Vehicle.objects.create(
        owner=user,
        make='Toyota',
        model='Supra',
        year=1998,
        purchase_price=35000.00
    )
    assert vehicle.id is not None
    assert str(vehicle) == '1998 Toyota Supra'
