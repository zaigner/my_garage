from datetime import timedelta

from django.db import migrations
from django.db.models import F


def backfill_expires_at(apps, schema_editor):
    """Give never-used active tokens the 72-hour unused-code expiry."""
    EstateAccessToken = apps.get_model("my_garage", "EstateAccessToken")
    EstateAccessToken.objects.filter(
        is_active=True, use_count=0, expires_at__isnull=True
    ).update(expires_at=F("issued_at") + timedelta(hours=72))


class Migration(migrations.Migration):
    dependencies = [
        ("my_garage", "0020_estate_access_log"),
    ]

    operations = [
        migrations.RunPython(backfill_expires_at, migrations.RunPython.noop),
    ]
