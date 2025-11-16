from rest_framework import status
from rest_framework.response import Response

from presentation.models import GeneratedImage
from presentation.services import generate_images
from source import settings


class ContentGenerationService:

    @staticmethod
    def text_generation(request):
        # Получаем параметры из тела запроса
        model = request.data.get('model', "deepseek-chat")

        user_prompt = request.data.get('user_prompt')
        system_prompt = request.data.get('system_prompt', '')

        max_tokens = request.data.get('max_tokens')
        other_params = {k: v for k, v in request.data.items() if
                        k not in ['model', 'user_prompt', 'system_prompt', 'max_tokens']}

        if not user_prompt:
            return Response({'error': 'Field "user_prompt" is required'}, status=status.HTTP_400_BAD_REQUEST)

        messages = [
            {"role": "system",
             "content": system_prompt},
            {"role": "user",
             "content": user_prompt}
        ]

        # Вызов API OpenAI с заданными параметрами
        response = settings.OPENAI_CLIENT.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            **other_params
        )

        return response


    @staticmethod
    def image_generation(request):
        prompt = request.data.get('presentation_theme')
        num_images = request.data.get('num_images', 1)
        engine = request.data.get('engine', 'yandex')
        model = request.data.get('model', 'yandex-art')
        width_ratio = request.data.get('width_ratio', 1)
        height_ratio = request.data.get('width_ratio', 2)
        seed = request.data.get('width_ratio', 50)

        image_urls = generate_images(prompt, num_images=num_images, engine=engine, model=model, width_ratio=width_ratio, height_ratio=height_ratio, seed=seed)

        saved_images = []
        for url in image_urls:

            # Загружаем изображение
            # response = requests.get(url)
            # if response.status_code == 200:
            #     # Генерируем уникальное имя файла
            #     file_name = f"{uuid.uuid4()}.jpg"
            #
            #     # Сохраняем изображение
            #     path = default_storage.save(f"generated_images/{file_name}", ContentFile(response.content))
            #
            # Создаем запись в базе данных
            image = GeneratedImage.objects.create(
                theme=prompt,
                image=url
            )
            saved_images.append({
                'id': image.id,
                # 'url': request.build_absolute_uri(image.image.url)
                'url': url
            })

        return saved_images