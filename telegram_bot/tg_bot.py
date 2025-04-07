import telebot

from main.models import Config

bot = telebot.TeleBot(Config.get_instance().telegram_bot_apikey)