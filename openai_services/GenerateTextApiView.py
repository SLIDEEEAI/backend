from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication

from presentation.decorators.charge_user import charge_user
from presentation.decorators.require_scope import require_scope
from presentation.models import BalanceHistory
from presentation.service_modules.content_generation_service import ContentGenerationService


class TextGenerationAPIView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @require_scope('generate_text')
    @charge_user(
        amount=50,
        reason=BalanceHistory.Reason.TEXT_GENERATION_PAYMENT
    )
    def post(self, request, *args, **kwargs):
        user_prompt = request.data.get('user_prompt')
        if not user_prompt:
            return Response({'error': 'Field "user_prompt" is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            response = ContentGenerationService.text_generation(request)
            # Возвращаем ответ API
            return Response(response.choices[0].message.content, status=status.HTTP_200_OK)
        except Exception as e:
            # Обработка ошибок
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SystemTextGenerationAPIView(APIView):

    def post(self, request, *args, **kwargs):
        user_prompt = request.data.get('user_prompt')
        if not user_prompt:
            return Response({'error': 'Field "user_prompt" is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            response = ContentGenerationService.text_generation(request)
            # Возвращаем ответ API
            return Response(response.choices[0].message.content, status=status.HTTP_200_OK)
        except Exception as e:
            # Обработка ошибок
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)