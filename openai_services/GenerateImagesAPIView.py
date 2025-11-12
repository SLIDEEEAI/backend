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
from presentation.services import generate_images

class ImageGenerationAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)

    @require_scope('generate_picture')
    @charge_user(
        amount=150,
        reason=BalanceHistory.Reason.IMAGE_GENERATION_PAYMENT
    )
    def post(self, request):
        presentation_theme = request.data.get('presentation_theme')
        num_images = request.data.get('num_images', 1)
        engine = request.data.get('engine', 'yandex')
        model = request.data.get('model', 'yandex-art')
        width_ratio = request.data.get('width_ratio', 1)
        height_ratio = request.data.get('width_ratio', 2)
        seed = request.data.get('width_ratio', 50)

        image_urls = generate_images(presentation_theme, num_images=num_images, engine=engine, model=model, width_ratio=width_ratio, height_ratio=height_ratio, seed=seed)

        saved_images = []
        for url in image_urls:

            # Загружаем изображение
            response = requests.get(url)
            if response.status_code == 200:
                # Генерируем уникальное имя файла
                file_name = f"{uuid.uuid4()}.jpg"

                # Сохраняем изображение
                path = default_storage.save(f"generated_images/{file_name}", ContentFile(response.content))

                # Создаем запись в базе данных
                image = GeneratedImage.objects.create(
                    theme=presentation_theme,
                    image=path
                )

                saved_images.append({
                    'id': image.id,
                    'url': request.build_absolute_uri(image.image.url)
                })

        return Response({'images': saved_images}, status=status.HTTP_200_OK)

    # def post(self, request, *args, **kwargs):
    #
    #     # Получаем параметры из тела запроса
    #     prompt = request.data.get('prompt')
    #     model = request.data.get('model','dall-e-2') # используемая модель ('dall-e-2' or 'dall-e-3')
    #     n = request.data.get('n', 1)  # Количество изображений для генерации
    #     size = request.data.get('size', '1024x1024')  # Размер изображения
    #     quality = request.data.get('quality', 'hd')  # Качество изображения
    #     style = request.data.get('style', 'natural') #Стиль изображения (`vivid` or `natural`)
    #
    #     if not prompt:
    #         return Response({'error': 'Field "Prompt" is required'}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     try:
    #         # Вызов API OpenAI для генерации изображений
    #         images = settings.OPENAI_IMAGE_CLIENT.images.generate(
    #             prompt=prompt,
    #             model=model,
    #             size=size,
    #             quality=quality,
    #             n=n,
    #             style=style
    #         )
    #
    #         if images.data:
    #             # Возвращаем ответ API
    #             return Response(images.data, status=status.HTTP_200_OK)
    #         else:
    #             return Response({'error': "no data"}, status=status.HTTP_502_BAD_GATEWAY)
    #
    #     except Exception as e:
    #         # Обработка ошибок
    #         return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)