# Generated by Django 5.2 on 2025-06-08 21:23

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Config',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('referral_bonus', models.DecimalField(decimal_places=2, default=1, max_digits=10)),
                ('bonus_to_new_users', models.DecimalField(decimal_places=2, default=1000, max_digits=10)),
                ('telegram_group_joined_promocode_token_amount', models.IntegerField(default=100000)),
                ('telegram_admins_id', models.JSONField(default=dict)),
                ('telegram_group_id', models.CharField(default='', max_length=255)),
                ('telegram_bot_apikey', models.CharField(default='', max_length=255)),
            ],
            options={
                'verbose_name': 'Config',
                'verbose_name_plural': 'Configs',
            },
        ),
    ]
