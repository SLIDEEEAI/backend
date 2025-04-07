import telebot

from main.models import Config

try:
    bot = telebot.TeleBot(Config.get_instance().telegram_bot_apikey)
except:
    bot = telebot.TeleBot('')