from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('presentation', '0008_generated_image_to_user_and_add_error_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='presentation',
            name='author',
        ),
        migrations.RemoveField(
            model_name='presentation',
            name='date_created',
        ),
        migrations.RemoveField(
            model_name='presentation',
            name='date_edited',
        ),
        migrations.RemoveField(
            model_name='presentation',
            name='group',
        ),
        migrations.RemoveField(
            model_name='presentation',
            name='theme',
        ),
    ]
