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
            return Response({"error": "field 'presentation_theme' is required."}, status=status.HTTP_400_BAD_REQUEST)
        image_urls = ContentGenerationService.image_generation(request)
        return Response({'images': image_urls}, status=status.HTTP_200_OK)


class SystemImageGenerationAPIView(APIView):
    def post(self, request):
        prompt = request.data.get('presentation_theme')
        if not prompt:
            return Response({"error": "field 'presentation_theme' is required."}, status=status.HTTP_400_BAD_REQUEST)
        image_urls = ContentGenerationService.image_generation(request)
        return Response({'images': image_urls}, status=status.HTTP_200_OK)