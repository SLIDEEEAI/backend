from telebot import types

from telegram_bot.models import TelegramUser, Command
from telegram_bot.tg_bot import bot


def execute_commands(chat_id, cmds, user=None):
    for cmd in cmds:
        finish = _execute_command(chat_id, cmd, user, 10, True)
        if finish:
            break


def _execute_command(chat_id, cmd, user=None, deep_call_limit=10, stop_if_called_cmd_twice=True):
    deep_call = 0
    called_cmds = []
    while cmd:
        print(f'Func: {cmd}\nUser: {user}\n is_group_member: {user.is_group_member}\npromocode_received: {user.promocode_received}')
        if (stop_if_called_cmd_twice and (cmd in called_cmds)) or deep_call > deep_call_limit:
            break
        if cmd.action:
            cmd.call_action(user)
            user.refresh_from_db()
            print('\n')
            print(f'Func action: {cmd.action}\nUser: {user}\n is_group_member: {user.is_group_member}\npromocode_received: {user.promocode_received}')
        if cmd.only_for:
            if cmd.only_for == Command.OnlyFor.NOT_JOINED_TO_GROUP and user.is_group_member:
                break
            elif cmd.only_for == Command.OnlyFor.PROMOCODE_NOT_RECEIVED and user.promocode_received:
                break
            elif cmd.only_for == Command.OnlyFor.JOINED_TO_GROUP and not user.is_group_member:
                break
            elif cmd.only_for == Command.OnlyFor.PROMOCODE_RECEIVED and not user.promocode_received:
                break
        markup = None
        if cmd.button_text and cmd.button_link:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(
                text=cmd.button_text,
                url=cmd.button_link if cmd.button_link.startswith('http') else None,
                callback_data=cmd.button_link if not cmd.button_link.startswith('http') else None
            ))
        if cmd.response:
            bot.send_message(chat_id, make_message(cmd.response, user), reply_markup=markup)
        if cmd.finish:
            return True
        called_cmds.append(cmd)
        cmd = cmd.next_message
        deep_call += 1


def make_message(text, user: TelegramUser, **kwargs):
    result = text.format(
        username=user.username,
        fullname=user.fullname,
        id=user.telegram_id,
        promocode_received="получен" if user.promocode_received else 'не получен',
        promocode=user.promocode.code if user.promocode else '*****',
        amount=user.promocode.token_amount if user.promocode else '*****',
        **kwargs,
    )
    return result