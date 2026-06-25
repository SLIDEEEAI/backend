import logging
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from presentation.authentication import JWTAuthentication

from presentation.decorators.charge_user import charge_user
from presentation.decorators.require_scope import require_scope
from presentation.models import BalanceHistory
from presentation.service_modules.content_generation_service import (
    ContentGenerationService,
    ImageGenerationError,
)


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
            result = ContentGenerationService.image_generation(request)
            images = result['images']
            failed = result['failed']

            response_data = {
                'success': True,
                'message': f'Успешно сгенерировано {len(images)} изображений',
                'images': images,
            }
            if failed:
                response_data['failed'] = failed
                response_data['message'] += f', не удалось: {len(failed)}'

            return Response(response_data, status=status.HTTP_200_OK)

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

        except ImageGenerationError as e:
            return self._build_generation_error_response(request, e.user_message, e.debug_details)

        except Exception:
            logger.exception(
                "Unexpected image generation error for user %s",
                request.user.id if request.user.is_authenticated else 'unknown',
            )
            return self._build_generation_error_response(
                request,
                "Ошибка при обработке запроса. Попробуйте позже.",
            )

    @staticmethod
    def _build_generation_error_response(request, error_message, debug_details=None):
        if debug_details:
            logger.error(
                "Image generation failed for user %s:\n%s",
                request.user.id if request.user.is_authenticated else 'unknown',
                debug_details,
            )

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

        return Response(
            {
                'success': False,
                'error': error_message,
                'code': error_code,
            },
            status=status_code,
        )


class SystemImageGenerationAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    def post(self, request):
        prompt = request.data.get('presentation_theme')
        if not prompt:
            return Response(
                {"error": "field 'presentation_theme' is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = ContentGenerationService.image_generation(request)
            images = result['images']
            failed = result['failed']

            response_data = {
                'success': True,
                'message': f'Успешно сгенерировано {len(images)} изображений',
                'images': images,
            }
            if failed:
                response_data['failed'] = failed
                response_data['message'] += f', не удалось: {len(failed)}'

            return Response(response_data, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'code': 'validation_error'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except ImageGenerationError as e:
            return ImageGenerationAPIView._build_generation_error_response(
                request, e.user_message, e.debug_details
            )

        except Exception:
            logger.exception("Unexpected system image generation error")
            return ImageGenerationAPIView._build_generation_error_response(
                request,
                "Ошибка при обработке запроса. Попробуйте позже.",
            )