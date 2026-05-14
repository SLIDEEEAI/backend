import logging
import uuid

import requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication

from presentation.decorators.charge_user import charge_user
from presentation.decorators.require_scope import require_scope
from presentation.models import BalanceHistory, GeneratedImage
from presentation.service_modules.content_generation_service import ContentGenerationService

logger = logging.getLogger(__name__)

class ImageGenerationAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    @require_scope('generate_picture')
    @charge_user(
        amount=150,
        reason=BalanceHistory.Reason.IMAGE_GENERATION_PAYMENT
    )
    def post(self, request):
        prompt = request.data.get('presentation_theme')
        if not prompt:
            return Response(
                {"error": "field 'presentation_theme' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Вызываем сервис генерации
            images = ContentGenerationService.image_generation(request)

            # Успешный ответ
            return Response(
                {
                    'success': True,
                    'message': f'Успешно сгенерировано {len(images)} изображений',
                    'images': images
                },
                status=status.HTTP_200_OK
            )

        except ValueError as e:
            # Ошибка валидации (например, отсутствует prompt)
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'validation_error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            # Ошибка генерации изображений
            error_message = str(e)

            # Определяем тип ошибки для более точного HTTP статуса
            if "отклонен системой безопасности" in error_message:
                status_code = status.HTTP_400_BAD_REQUEST
                error_code = 'moderation_blocked'
            elif "Недостаточно средств" in error_message:
                status_code = status.HTTP_402_PAYMENT_REQUIRED
                error_code = 'insufficient_balance'
            elif "Превышен лимит" in error_message:
                status_code = status.HTTP_429_TOO_MANY_REQUESTS
                error_code = 'rate_limit'
            elif "Ошибка подключения" in error_message or "таймаут" in error_message.lower():
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                error_code = 'service_unavailable'
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                error_code = 'generation_error'

            # Логируем ошибку для администратора
            logger.error(
                f"Image generation failed for user {request.user.id if request.user.is_authenticated else 'unknown'}: {error_message}")

            return Response(
                {
                    'success': False,
                    'error': error_message,
                    'code': error_code
                },
                status=status_code
            )


class SystemImageGenerationAPIView(APIView):
    permission_classes = []  # Для системного эндпоинта без аутентификации
    authentication_classes = []

    def post(self, request):
        prompt = request.data.get('presentation_theme')
        if not prompt:
            return Response(
                {"error": "field 'presentation_theme' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            images = ContentGenerationService.image_generation(request)
            return Response(
                {
                    'success': True,
                    'message': f'Успешно сгенерировано {len(images)} изображений',
                    'images': images
                },
                status=status.HTTP_200_OK
            )

        except ValueError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'validation_error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            error_message = str(e)

            if "отклонен системой безопасности" in error_message:
                status_code = status.HTTP_400_BAD_REQUEST
                error_code = 'moderation_blocked'
            elif "Недостаточно средств" in error_message:
                status_code = status.HTTP_402_PAYMENT_REQUIRED
                error_code = 'insufficient_balance'
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                error_code = 'generation_error'

            return Response(
                {
                    'success': False,
                    'error': error_message,
                    'code': error_code
                },
                status=status_code
            )