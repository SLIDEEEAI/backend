# Generated by Django 5.1.2 on 2024-10-18 22:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presentation', '0009_tariff'),
    ]

    operations = [
        migrations.AddField(
            model_name='tariff',
            name='presentation_count',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
