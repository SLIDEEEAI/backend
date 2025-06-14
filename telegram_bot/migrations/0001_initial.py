# Generated by Django 5.2 on 2025-06-08 21:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('presentation', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Command',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='Это не будет играть роли при исполнения инструкции', max_length=255, verbose_name='Название инструкции')),
                ('command', models.CharField(blank=True, help_text='Команда или сообщение, по которому будет отправлен ответ. Например, "start" или "привет".', max_length=256, null=True, verbose_name='Команда или текст')),
                ('signal', models.CharField(blank=True, choices=[('user_join', 'Когда пользователь вступил в группу'), ('user_left', 'Когда пользователь покинул группу'), ('user_start_use_bot', 'Когда пользователь начал использовать бота')], help_text='Автоматический сигнал, при котором будет отправлено сообщение.', max_length=56, null=True, verbose_name='Сигнал')),
                ('only_for', models.CharField(blank=True, choices=[('not_group_joined', 'Только для тех, кто НЕ вступил в группу'), ('not_code_received', 'Только для тех, кто НЕ получил промокод'), ('group_joined', 'Только для тех, кто вступил в группу'), ('code_received', 'Только для тех, кто получил промокод')], help_text='Позволяет отправлять сообщение только определённой категории пользователей.', max_length=56, null=True, verbose_name='Ограничение по пользователю')),
                ('action', models.CharField(blank=True, choices=[('ck_user_group_joined', 'Запустить проверку вступил ли юзер в группу')], help_text='Запуск дополнительной функции до выполнение инструкции. Это может быть проверка состоит ли юзер в группе', max_length=56, null=True, verbose_name='Доп. функция')),
                ('response', models.TextField(blank=True, help_text='Текст, который будет отправлен пользователю. Доступные переменные:<br><strong>{username}</strong> — Юзернейм Telegram-пользователя<br><strong>{fullname}</strong> — Имя и Фамилия пользователя<br><strong>{id}</strong> — Telegram ID пользователя<br><strong>{promocode_received}</strong> — "получен"/"не получен" статус по промокоду<br><strong>{promocode}</strong> — сам промокод<br><strong>{amount}</strong> — количество кредитов в промокоде', null=True, verbose_name='Текст сообщения')),
                ('button_text', models.CharField(blank=True, help_text='Текст, отображаемый на кнопке под сообщением.', max_length=256, null=True, verbose_name='Название кнопки')),
                ('button_link', models.CharField(blank=True, help_text='Ссылка, команда или текст. Если указана команда или текст, и они обрабатываются инструкцией, будет выполнено соответствующее действие.', max_length=256, null=True, verbose_name='Действие кнопки')),
                ('priority', models.SmallIntegerField(default=0)),
                ('finish', models.BooleanField(default=False, verbose_name='Закончить дальнейшее выполнение последующих инструкции')),
                ('next_message', models.ForeignKey(blank=True, help_text='Следующее сообщение, которое будет отправлено после текущего.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sub_commands', to='telegram_bot.command', verbose_name='Следующее сообщение')),
            ],
            options={
                'verbose_name': 'Инструкция',
                'verbose_name_plural': 'Инструкции',
                'ordering': ['-priority'],
            },
        ),
        migrations.CreateModel(
            name='TelegramUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telegram_id', models.CharField(max_length=256)),
                ('username', models.CharField(default=None, max_length=256, null=True)),
                ('fullname', models.CharField(default=None, max_length=256, null=True)),
                ('is_group_member', models.BooleanField(default=False)),
                ('join_at', models.DateTimeField(blank=True, null=True)),
                ('left_at', models.DateTimeField(blank=True, null=True)),
                ('promocode_received', models.BooleanField(default=False)),
                ('promocode', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='presentation.promocode')),
            ],
        ),
    ]
