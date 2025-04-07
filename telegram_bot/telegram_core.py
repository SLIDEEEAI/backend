import telebot

from main.models import Config
from telegram_bot.models import Command, TelegramUser
from telegram_bot.signals import user_start_use_bot, user_joined_to_group, user_left_to_group
from telegram_bot.tg_bot import bot
from telegram_bot.utils import execute_commands, make_message


@bot.message_handler(commands=['send_to_users'])
def send_to_users_init(message):
    admin_id = message.chat.id
    if admin_id not in Config.get_instance().telegram_admins_id:
        return

    bot.send_message(
        admin_id,
        "Напиши текст для отправки\nБУДЬТЕ ОСТОРОЖНЫ, любое действие (вызов другие команды) далее отправиться всем пользователям"
    )
    bot.register_next_step_handler(message, process_admin_text)


def process_admin_text(message):
    if message.chat.id not in Config.get_instance().telegram_admins_id:
        return
    users = TelegramUser.objects.all()
    for user in users:
        bot.send_message(user.telegram_id, make_message(message.text, user))
    bot.send_message(message.chat.id, f"Сообщение '{message.text}' отправлена {users.count()} пользователям.")


@bot.message_handler(func=lambda message: True, chat_types=['group', 'channel', 'supergroup'], content_types=['new_chat_members'])
def new_chat_members(message):
    if str(message.chat.id) != Config.get_instance().telegram_group_id:
        return
    user, new = _create_tg_user_or_get(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        is_group_member=True,
    )
    user_joined_to_group.send(sender=user.__class__, user=user)


@bot.message_handler(func=lambda message: True, chat_types=['group', 'channel', 'supergroup'], content_types=['left_chat_member'])
def left_chat_member(message):
    if str(message.chat.id) != Config.get_instance().telegram_group_id:
        return
    user, new = _create_tg_user_or_get(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        is_group_member=False,
    )
    user_left_to_group.send(sender=user.__class__, user=user)


@bot.message_handler(func=lambda message: True)
def handle_text_command(message: telebot.types.Message):
    user, new = _create_tg_user_or_get(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name
    )

    try:
        cmds = Command.objects.filter(command__iexact=message.text.strip()).all()
    except Command.DoesNotExist:
        bot.reply_to(message, "Неизвестная команда.")
        return
    execute_commands(message.chat.id, cmds, user)

    if new:
        user_start_use_bot.send(sender=telebot.types.Message.__class__, user=user)
        if user.is_group_member:
            user_joined_to_group.send(sender=telebot.types.Message.__class__, user=user)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_command(call: telebot.types.CallbackQuery):
    user, _ = _create_tg_user_or_get(
        call.from_user.id,
        call.from_user.username,
        call.from_user.full_name,
    )
    try:
        cmds = Command.objects.filter(command__iexact=call.data.strip()).all()
    except Command.DoesNotExist:
        bot.answer_callback_query(call.id, "Неизвестная команда.")
        return

    bot.answer_callback_query(call.id)
    execute_commands(call.message.chat.id, cmds, user)


def _create_tg_user_or_get(id, username, fullname, is_group_member=False):
    user, created = TelegramUser.objects.get_or_create(
        telegram_id=str(id),
        defaults={
            'is_group_member': is_group_member,
            'username': username,
            'fullname': fullname,
        }
    )
    if created:
        user.is_group_member = is_user_in_group(user.telegram_id, Config.get_instance().telegram_group_id)
        user.save(update_fields=['is_group_member'])
    return user, created



def is_user_in_group(user_id, chat_id):
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status not in ['left', 'kicked']
    except Exception:
        return False
