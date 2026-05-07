import base64
import os
import traceback
import uuid
import requests as http_requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.response import Response
from openai import OpenAI

from presentation.models import GeneratedImage
from source import settings
from source.settings import config


class ContentGenerationService:
    DEFAULT_IMAGE_MODEL = 'gpt-image-2'

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



    # --- НОВЫЙ МЕТОД ГЕНЕРАЦИИ ИЗОБРАЖЕНИЙ ---
    @staticmethod
    def image_generation(request):
        """
        Генерация изображений с использованием AITunnel API.
        Возвращает список словарей с id и url сохраненных изображений.
        """
        prompt = request.data.get('presentation_theme')
        if not prompt:
            raise ValueError("field 'presentation_theme' is required.")

        print(f'Генерация для промпта: "{prompt}"')

        num_images = int(request.data.get('num_images', 1))
        # model = request.data.get('model', ContentGenerationService.DEFAULT_IMAGE_MODEL)
        model = ContentGenerationService.DEFAULT_IMAGE_MODEL
        size = request.data.get('size', "1024x1024")
        quality = request.data.get('quality', "low")

        saved_images = []

        for i in range(num_images):
            try:
                # Формируем запрос к AITunnel
                headers = {
                    "Authorization": f"Bearer {settings.AITUNNEL_API_KEY}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": model,
                    "prompt": prompt if num_images == 1 else f"{prompt} (вариант {i + 1})",
                    "n": 1,
                    "size": size,
                    "quality": quality
                    # "response_format": "b64_json",
                }

                print(f"Отправка запроса ({i + 1}/{num_images})...")

                response = http_requests.post(
                    "https://api.aitunnel.ru/v1/images/generations",
                    headers=headers,
                    json=payload,
                    timeout=150
                )

                if response.status_code != 200:
                    print(f"Ошибка API: {response.status_code} - {response.text}")
                    continue

                data = response.json()

                if not data.get('data'):
                    print("Нет данных в ответе")
                    continue

                # Получаем изображение
                image_data = data['data'][0]
                file_name = f"aitunnel_images/{str(uuid.uuid4())}.png"
                saved_path = None

                # Пробуем получить URL
                if 'url' in image_data and image_data['url']:
                    print(f"Скачивание изображения по URL...")
                    img_response = http_requests.get(image_data['url'], timeout=30)
                    if img_response.status_code == 200:
                        saved_path = default_storage.save(file_name, ContentFile(img_response.content))

                    else:
                        print(f"Не удалось скачать по URL: {img_response.status_code}")
                        continue

                # Пробуем получить base64
                elif 'b64_json' in image_data and image_data['b64_json']:
                    print(f"Декодирование base64 изображения...")
                    try:
                        image_bytes = base64.b64decode(image_data['b64_json'])
                        saved_path = default_storage.save(file_name, ContentFile(image_bytes))
                    except Exception as decode_error:
                        print(f"Ошибка декодирования base64: {decode_error}")
                        continue
                else:
                    print("Нет ни URL, ни base64 в ответе")
                    continue

                if not saved_path:
                    print("Не удалось сохранить изображение")
                    continue

                # Формируем публичный URL
                file_url = settings.MEDIA_URL + saved_path
                if not file_url.startswith("/"):
                    file_url = "/" + file_url

                # Сохраняем в БД
                image_record = GeneratedImage.objects.create(
                    theme=prompt,
                    image=file_url
                )

                saved_images.append({
                    'id': image_record.id,
                    'url': file_url
                })
                print(f"✅ Изображение {i + 1} сохранено")

                # Для отладки - сохраняем информацию о первом ответе
                if i == 0:
                    debug_path = os.path.join(settings.LOGS_ROOT, f"aitunnel_response_{uuid.uuid4()}.json")
                    with open(debug_path, 'w', encoding='utf-8') as f:
                        import json
                        debug_data = data.copy()
                        if 'data' in debug_data and debug_data['data']:
                            for item in debug_data['data']:
                                if 'b64_json' in item:
                                    item['b64_json'] = f"[BASE64_STRING_LENGTH:{len(item['b64_json'])}]"
                        json.dump(debug_data, f, indent=2, ensure_ascii=False)
                    print(f"Ответ API сохранен в: {debug_path}")

            except Exception as e:
                print(f"❌ Ошибка {i + 1}: {e}")
                print(traceback.format_exc())
                continue

        if not saved_images:
            raise Exception("Не удалось сгенерировать ни одного изображения")

        return saved_images  # Возвращаем список, а не Response



    # # --- FOR U ---
    # @staticmethod
    # def image_generation(request):
    #     prompt = request.data.get('presentation_theme')
    #     num_images = request.data.get('num_images', 1)
    #     engine = request.data.get('engine', 'yandex')
    #     model = request.data.get('model', 'yandex-art')
    #     width_ratio = request.data.get('width_ratio', 1)
    #     height_ratio = request.data.get('height_ratio', 2)
    #     seed = request.data.get('seed', 50)
    #
    #     image_urls = generate_images(prompt, num_images=num_images, engine=engine, model=model, width_ratio=width_ratio, height_ratio=height_ratio, seed=seed)
    #
    #     saved_images = []
    #     for url in image_urls:
    #
    #         # Загружаем изображение
    #         # response = requests.get(url)
    #         # if response.status_code == 200:
    #         #     # Генерируем уникальное имя файла
    #         #     file_name = f"{uuid.uuid4()}.jpg"
    #         #
    #         #     # Сохраняем изображение
    #         #     path = default_storage.save(f"generated_images/{file_name}", ContentFile(response.content))
    #         #
    #         # Создаем запись в базе данных
    #         image = GeneratedImage.objects.create(
    #             theme=prompt,
    #             image=url
    #         )
    #         saved_images.append({
    #             'id': image.id,
    #             # 'url': request.build_absolute_uri(image.image.url)
    #             'url': url
    #         })
    #
    #     return saved_images