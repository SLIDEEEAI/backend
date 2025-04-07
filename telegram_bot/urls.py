from django.urls import path
from rest_framework import routers

from telegram_bot.views import SetWebHookView, WebhookView

app_name = 'telegram_webhook'

router = routers.SimpleRouter()

urlpatterns = [
    path('set-webhook/', SetWebHookView.as_view(), name='test'),
    path('webhook/', WebhookView.as_view(), name='webhook'),
]+router.urls
