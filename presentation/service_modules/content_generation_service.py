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
        model = ContentGenerationService.DEFAULT_IMAGE_MODEL
        size = request.data.get('size', "1024x1024")
        quality = request.data.get('quality', "low")

        saved_images = []
        errors = []

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
                    "quality": quality,
                    # "response_format": "b64_json",  # Явно запрашиваем base64
                }

                print(f"Отправка запроса ({i + 1}/{num_images})...")

                response = http_requests.post(
                    "https://api.aitunnel.ru/v1/images/generations",
                    headers=headers,
                    json=payload,
                    timeout=150
                )

                # Обработка ошибок API
                if response.status_code != 200:
                    error_data = response.json()
                    error_message = ContentGenerationService._parse_api_error(error_data)
                    # При первой же ошибке выбрасываем исключение
                    raise Exception(error_message)

                data = response.json()

                if not data.get('data'):
                    raise Exception("Пустой ответ от API")

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
                        raise Exception(f"Не удалось скачать изображение (статус {img_response.status_code})")

                # Пробуем получить base64
                elif 'b64_json' in image_data and image_data['b64_json']:
                    print(f"Декодирование base64 изображения...")
                    try:
                        image_bytes = base64.b64decode(image_data['b64_json'])
                        saved_path = default_storage.save(file_name, ContentFile(image_bytes))
                    except Exception as decode_error:
                        raise Exception(f"Ошибка декодирования изображения: {decode_error}")
                else:
                    raise Exception("Неизвестный формат ответа от API")

                if not saved_path:
                    raise Exception("Не удалось сохранить файл")

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

            except http_requests.exceptions.Timeout:
                raise Exception("Превышено время ожидания ответа от API. Попробуйте позже.")
            except http_requests.exceptions.ConnectionError:
                raise Exception("Ошибка подключения к серверу генерации изображений. Проверьте интернет-соединение.")
            except Exception as e:
                # Пробрасываем исключение дальше
                print(f"❌ Ошибка при генерации изображения {i + 1}: {e}")
                raise

        # Проверяем, что хотя бы одно изображение сгенерировано
        if not saved_images:
            error_detail = "; ".join(errors) if errors else "Неизвестная ошибка при генерации изображений"
            raise Exception(error_detail)

        return saved_images

    @staticmethod
    def _parse_api_error(error_data):
        """
        Парсит ошибку от AITunnel API и возвращает понятное сообщение.
        """
        if 'error' not in error_data:
            return "Неизвестная ошибка API"

        error = error_data['error']
        code = error.get('code')
        message = error.get('message', '')

        # Русскоязычные сообщения для различных ошибок
        error_messages = {
            'moderation_blocked': "Ваш запрос был отклонен системой безопасности. Пожалуйста, измените описание изображения, убрав неуместный или запрещенный контент.",
            'invalid_request_error': "Некорректный запрос к API. Проверьте параметры запроса.",
            'authentication_error': "Ошибка аутентификации. Обратитесь к администратору.",
            'rate_limit_error': "Превышен лимит запросов. Попробуйте позже.",
            'insufficient_quota': "Недостаточно средств на балансе. Пополните баланс в сервисе AITunnel.",
        }

        # Проверяем наличие специфических флагов в сообщении
        if 'safety_violations' in message:
            import re
            violations = re.findall(r'safety_violations=\[(.*?)\]', message)
            if violations:
                return f"Ваш запрос был отклонен системой безопасности. Нарушение правил: {violations[0]}. Пожалуйста, измените описание."

        # Возвращаем понятное сообщение на основе кода ошибки
        if code in error_messages:
            return error_messages[code]

        # Если сообщение на русском, оставляем как есть
        if any(russian_char in message for russian_char in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'):
            return message

        # Стандартное сообщение для неизвестных ошибок
        return f"Ошибка генерации изображения: {message}" if message else "Неизвестная ошибка при генерации изображения"