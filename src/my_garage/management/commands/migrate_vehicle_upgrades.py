from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from my_garage.models import Upgrade, GenericUpgrade, Vehicle

class Command(BaseCommand):
    help = 'Migrates legacy Vehicle Upgrades to GenericUpgrades'

    def handle(self, *args, **options):
        legacy_upgrades = Upgrade.objects.all()
        vehicle_content_type = ContentType.objects.get_for_model(Vehicle)
        
        count = 0
        for old_upgrade in legacy_upgrades:
            # Map status
            new_status = old_upgrade.status
            if old_upgrade.status == 'INSTALLED':
                new_status = 'COMPLETED'
            
            # Check if already migrated to avoid duplicates
            # We use a combination of fields to check for existence
            exists = GenericUpgrade.objects.filter(
                content_type=vehicle_content_type,
                object_id=old_upgrade.vehicle.id,
                name=old_upgrade.part_name,
                brand=old_upgrade.brand,
                part_number=old_upgrade.part_number
            ).exists()
            
            if not exists:
                GenericUpgrade.objects.create(
                    content_type=vehicle_content_type,
                    object_id=old_upgrade.vehicle.id,
                    name=old_upgrade.part_name,
                    brand=old_upgrade.brand,
                    part_number=old_upgrade.part_number,
                    status=new_status,
                    cost=old_upgrade.cost,
                    completion_date=old_upgrade.installation_date,
                    notes=old_upgrade.notes
                )
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated {count} upgrades to GenericUpgrades'))
