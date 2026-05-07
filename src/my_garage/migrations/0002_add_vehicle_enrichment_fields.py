from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("my_garage", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="features",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="vehicle",
            name="specs",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="vehicle",
            name="photo",
            field=models.ImageField(blank=True, null=True, upload_to="vehicles/%Y/%m/"),
        ),
    ]
