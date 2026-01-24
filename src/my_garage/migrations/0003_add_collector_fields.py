from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('my_garage', '0002_add_vehicle_enrichment_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehicle',
            name='exterior_color',
            field=models.CharField(blank=True, help_text='Specific paint name/code', max_length=50),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='interior_color',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='license_plate',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='notes',
            field=models.TextField(blank=True, help_text='Provenance, history, and other details.'),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='purchase_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='vehicle',
            name='transmission',
            field=models.CharField(blank=True, help_text='e.g. 6-Speed Manual, 8-Speed Auto', max_length=50),
        ),
    ]
