import django.core.validators
from django.db import migrations, models


def normalize_single_use_promocodes(apps, schema_editor):
    PromoCode = apps.get_model('presentation', 'PromoCode')
    PromoCode.objects.filter(usage_type='single', is_active=True).update(usage_limit=1)


class Migration(migrations.Migration):

    dependencies = [
        ('presentation', '0009_remove_presentation_legacy_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='promocode',
            name='user_access',
            field=models.CharField(
                choices=[
                    ('new_users_only', 'Только для пользователей без промокодов'),
                    ('all_users', 'Для всех пользователей')
                ],
                default='all_users',
                help_text='Кто может применить промокод.',
                max_length=20
            ),
        ),
        migrations.AlterField(
            model_name='promocode',
            name='usage_limit',
            field=models.PositiveIntegerField(
                default=1,
                help_text='Сколько пользователей могут применить промокод. Для одноразового должно быть 1.',
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(1000000)
                ]
            ),
        ),
        migrations.RunPython(normalize_single_use_promocodes, migrations.RunPython.noop),
    ]
