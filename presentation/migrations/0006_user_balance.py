# Generated by Django 5.0.6 on 2024-05-09 19:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presentation', '0005_presentation_author_presentation_date_created_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='balance',
            field=models.IntegerField(default=100),
        ),
    ]
