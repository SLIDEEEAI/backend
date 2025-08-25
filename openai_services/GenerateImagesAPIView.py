from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from source import settings

class ImageGenerationAPIView(APIView):
    def post(self, request, *args, **kwargs):

        # Получаем параметры из тела запроса
        prompt = request.data.get('prompt')
        model = request.data.get('model','dall-e-2') # используемая модель ('dall-e-2' or 'dall-e-3')
        n = request.data.get('n', 1)  # Количество изображений для генерации
        size = request.data.get('size', '1024x1024')  # Размер изображения
        quality = request.data.get('quality', 'hd')  # Качество изображения
        style = request.data.get('style', 'natural') #Стиль изображения (`vivid` or `natural`)

        if not prompt:
            return Response({'error': 'Field "Prompt" is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Вызов API OpenAI для генерации изображений
            images = settings.OPENAI_IMAGE_CLIENT.images.generate(
                prompt=prompt,
                model=model,
                size=size,
                quality=quality,
                n=n,
                style=style
            )

            if images.data:
                # Возвращаем ответ API
                return Response(images.data, status=status.HTTP_200_OK)
            else:
                return Response({'error': "no data"}, status=status.HTTP_502_BAD_GATEWAY)

        except Exception as e:
            # Обработка ошибок
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)