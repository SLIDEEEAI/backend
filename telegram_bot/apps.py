from django.apps import AppConfig

from telegram_bot.signals import user_start_use_bot, user_left_to_group, user_joined_to_group


class TelegramBotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telegram_bot'

    def ready(self):
        from telegram_bot import events

        user_start_use_bot.connect(events.notify_user_start_use_bot)
        user_joined_to_group.connect(events.notify_user_joined_to_group)
        user_left_to_group.connect(events.notify_user_left_to_group)
