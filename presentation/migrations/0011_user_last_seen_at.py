from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('presentation', '0010_promocode_access_rules'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='last_seen_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
