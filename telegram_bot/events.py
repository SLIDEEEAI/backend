from django.utils.timezone import now

from telegram_bot.models import Command
from telegram_bot.telegram_core import execute_commands


def notify_user_joined_to_group(sender, user, **kwargs):
    commands = Command.objects.filter(signal=Command.Signals.USER_JOIN_GROUP).all()
    if not user.promocode_received:
        user.apply_promocode()
    user.join_at = now()
    user.is_group_member = True
    user.promocode_received = True
    user.save(update_fields=['join_at', 'is_group_member', 'promocode_received'])
    execute_commands(user.telegram_id, commands, user)


def notify_user_left_to_group(sender, user, **kwargs):
    user.is_group_member = False
    user.left_at = now()
    user.save(update_fields=['is_group_member', 'left_at'])
    commands = Command.objects.filter(signal=Command.Signals.USER_LEFT_GROUP).all()
    execute_commands(user.telegram_id, commands, user)



def notify_user_start_use_bot(sender, user, **kwargs):
    commands = Command.objects.filter(signal=Command.Signals.USER_START_USE_BOT).all()
    execute_commands(user.telegram_id, commands, user)
