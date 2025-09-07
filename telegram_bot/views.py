import logging


import telebot
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from telegram_bot.telegram_core import bot

logger = logging.getLogger(__name__)


class SetWebHookView(APIView):
    def get(self, request: Request) -> Response:
        """
        Удаляет текущий вебхук и устанавливает новый.

        Args:
            request: Объект запроса.

        Returns:
            Response: Пустой ответ с кодом статуса 200.
        """
        if request.GET.get('pass') != 'LirilliLarila':
            return Response(f"ok", status=200)
        bot.remove_webhook()
        url = 'https://slideee.ru/api/v1/webhook/'
        logger.info(f'Setting webhook URL {url}')
        res = bot.set_webhook(f'{url}')
        logger.info(f'Result {res}')
        return Response(f"ok {res}", status=200)


class WebhookView(APIView):
    """
    Класс для обработки вебхуков от телеграм-бота.
    """

    def post(self, request: Request) -> Response:
        """
        Обрабатывает POST-запросы, содержащие данные в формате JSON,
        полученные от телеграм-бота.

        Args:
            request: Объект запроса.

        Returns:
            Response: Пустой ответ с кодом статуса 200.
        """

        update = telebot.types.Update.de_json(request.body.decode('utf-8'))
        print(update)
        bot.process_new_updates([update])
        return Response("", status=200)
