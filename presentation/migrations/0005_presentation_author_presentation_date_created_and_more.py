# Generated by Django 5.0 on 2024-03-26 17:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presentation', '0004_presentation_created_at_presentation_updated_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='presentation',
            name='author',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='presentation',
            name='date_created',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='presentation',
            name='date_edited',
            field=models.DateTimeField(null=True),
        ),
        migrations.AddField(
            model_name='presentation',
            name='favourite',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='presentation',
            name='group',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='presentation',
            name='removed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='presentation',
            name='theme',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='presentation',
            name='title',
            field=models.CharField(max_length=255, null=True),
        ),
    ]