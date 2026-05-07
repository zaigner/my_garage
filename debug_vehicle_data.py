import os
import sys

import django

# Setup Django environment
sys.path.append("/home/zaigner77/projects/zaigner/my_garage/src")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "my_garage.settings")
django.setup()

from my_garage.models import ServiceRecord, Upgrade, Vehicle  # noqa: E402


def check_vehicle_data(vehicle_id):
    try:
        vehicle = Vehicle.objects.get(pk=vehicle_id)
        print(f"Vehicle: {vehicle} (ID: {vehicle.id})")
        print(f"Purchase Price: {vehicle.purchase_price}")
        print(f"Market Value: {vehicle.current_market_value}")

        print("\n--- Service Records ---")
        records = ServiceRecord.objects.filter(vehicle=vehicle)
        print(f"Total Records: {records.count()}")
        for r in records:
            print(
                f"- {r.date}: {r.service_type} (Cost: {r.total_cost}, Verified: {r.is_verified})"  # noqa: E501
            )

        print("\n--- Legacy Upgrades ---")
        legacy = Upgrade.objects.filter(vehicle=vehicle)
        print(f"Total Legacy: {legacy.count()}")
        for u in legacy:
            print(f"- {u.part_name} (Cost: {u.cost}, Status: {u.status})")

        print("\n--- Generic Upgrades ---")
        generic = vehicle.projects.all()
        print(f"Total Generic: {generic.count()}")
        for g in generic:
            print(f"- {g.name} (Cost: {g.cost}, Status: {g.status})")

    except Vehicle.DoesNotExist:
        print(f"Vehicle with ID {vehicle_id} not found.")


if __name__ == "__main__":
    check_vehicle_data(1)
