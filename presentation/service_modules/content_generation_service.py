import base64
import json
import logging
import traceback
import uuid
import requests as http_requests
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.response import Response

from presentation.models import GeneratedImage
from presentation.services import chat_completion_create
from source import settings

logger = logging.getLogger(__name__)


class ImageGenerationError(Exception):
    def __init__(self, user_message, debug_details=None):
        self.user_message = user_message
        self.debug_details = debug_details or user_message
        super().__init__(user_message)


class ContentGenerationService:
    DEFAULT_IMAGE_MODEL = 'gpt-image-2'

    @staticmethod
    def text_generation(request):
        # Получаем параметры из тела запроса
        model = request.data.get('model', "deepseek-v4-flash")

        user_prompt = request.data.get('user_prompt')
        system_prompt = request.data.get('system_prompt', '')

        max_tokens = ContentGenerationService._to_int_or_none(request.data.get('max_tokens'))
        temperature = ContentGenerationService._to_float_or_none(request.data.get('temperature'))
        thinking_enabled = ContentGenerationService._to_bool(request.data.get('thinking_enabled'), default=False)
        thinking_type = request.data.get('thinking_type', 'enabled')
        other_params = {k: v for k, v in request.data.items() if
                        k not in [
                            'model', 'user_prompt', 'system_prompt',
                            'max_tokens', 'temperature',
                            'thinking_enabled', 'thinking_type'
                        ]}

        if not user_prompt:
            return Response({'error': 'Field "user_prompt" is required'}, status=status.HTTP_400_BAD_REQUEST)

        messages = [{"role": "user", "content": user_prompt}]
        if system_prompt:
            messages.insert(0, {"role": "system", "content": system_prompt})

        # Используем общую обертку для единообразной работы с DeepSeek.
        chat_completion = chat_completion_create(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            thinking_enabled=thinking_enabled,
            thinking_type=thinking_type,
            request_options=other_params,
            return_full_response=True,
        )

        content = ContentGenerationService._extract_text_content(chat_completion)
        finish_reason = ContentGenerationService._extract_finish_reason(chat_completion)

        # Если ответ пустой или модель уперлась в лимит, делаем 1 безопасный повтор.
        # Для пользовательского текста reasoning/thinking обычно не нужен и только съедает токены.
        if (not content) or finish_reason == "length":
            retry_max_tokens = ContentGenerationService._calc_retry_max_tokens(max_tokens)
            if retry_max_tokens is not None and (max_tokens is None or retry_max_tokens > max_tokens):
                chat_completion = chat_completion_create(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=retry_max_tokens,
                    thinking_enabled=False,
                    request_options=other_params,
                    return_full_response=True,
                )
                retried_content = ContentGenerationService._extract_text_content(chat_completion)
                if retried_content:
                    return retried_content
            elif not thinking_enabled:
                # thinking уже выключен и увеличить лимит нельзя — вернем исходный контент.
                pass
            else:
                chat_completion = chat_completion_create(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    thinking_enabled=False,
                    request_options=other_params,
                    return_full_response=True,
                )
                retried_content = ContentGenerationService._extract_text_content(chat_completion)
                if retried_content:
                    return retried_content

        return content

    @staticmethod
    def _extract_text_content(chat_completion):
        if not chat_completion or not getattr(chat_completion, 'choices', None):
            return ''
        message = chat_completion.choices[0].message
        content = getattr(message, 'content', None)
        return (content or '').strip()

    @staticmethod
    def _extract_finish_reason(chat_completion):
        if not chat_completion or not getattr(chat_completion, 'choices', None):
            return None
        return getattr(chat_completion.choices[0], 'finish_reason', None)

    @staticmethod
    def _calc_retry_max_tokens(max_tokens):
        if max_tokens is None:
            return 700
        if max_tokens < 450:
            return min(max_tokens * 2, 900)
        if max_tokens < 700:
            return 700
        return max_tokens

    @staticmethod
    def _to_bool(value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}

    @staticmethod
    def _to_int_or_none(value):
        if value in (None, ''):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_float_or_none(value):
        if value in (None, ''):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

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

        user = ContentGenerationService._resolve_user(request)
        saved_images = []
        failed_images = []

        for i in range(num_images):
            theme = prompt if num_images == 1 else f"{prompt} (вариант {i + 1})"
            image_record = GeneratedImage.objects.create(
                user=user,
                theme=theme,
            )

            try:
                headers = {
                    "Authorization": f"Bearer {settings.AITUNNEL_API_KEY}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": model,
                    "prompt": theme,
                    "n": 1,
                    "size": size,
                    "quality": quality,
                    "moderation": "low"
                }

                print(f"Отправка запроса ({i + 1}/{num_images})...")

                response = http_requests.post(
                    "https://api.aitunnel.ru/v1/images/generations",
                    headers=headers,
                    json=payload,
                    timeout=150
                )

                if response.status_code != 200:
                    raw_response = response.text
                    try:
                        error_data = response.json()
                    except ValueError:
                        error_data = None

                    user_message = ContentGenerationService._parse_api_error(error_data or {})
                    debug_details = ContentGenerationService._format_debug_details(
                        user_message=user_message,
                        status_code=response.status_code,
                        raw_response=raw_response,
                        error_data=error_data,
                    )
                    raise ImageGenerationError(user_message, debug_details)

                data = response.json()

                if not data.get('data'):
                    raise ImageGenerationError(
                        "Пустой ответ от API",
                        ContentGenerationService._format_debug_details(
                            user_message="Пустой ответ от API",
                            status_code=response.status_code,
                            raw_response=response.text,
                            error_data=data,
                        ),
                    )

                image_data = data['data'][0]
                file_name = f"aitunnel_images/{str(uuid.uuid4())}.png"
                saved_path = None

                if 'url' in image_data and image_data['url']:
                    print("Скачивание изображения по URL...")
                    img_response = http_requests.get(image_data['url'], timeout=30)
                    if img_response.status_code == 200:
                        saved_path = default_storage.save(file_name, ContentFile(img_response.content))
                    else:
                        raise ImageGenerationError(
                            "Не удалось скачать сгенерированное изображение. Попробуйте позже.",
                            ContentGenerationService._format_debug_details(
                                user_message=f"Не удалось скачать изображение (HTTP {img_response.status_code})",
                                status_code=img_response.status_code,
                                raw_response=img_response.text[:4000],
                            ),
                        )

                elif 'b64_json' in image_data and image_data['b64_json']:
                    print("Декодирование base64 изображения...")
                    image_bytes = base64.b64decode(image_data['b64_json'])
                    saved_path = default_storage.save(file_name, ContentFile(image_bytes))
                else:
                    raise ImageGenerationError(
                        "Неизвестный формат ответа от API. Попробуйте позже.",
                        ContentGenerationService._format_debug_details(
                            user_message="Неизвестный формат ответа от API",
                            error_data=data,
                        ),
                    )

                if not saved_path:
                    raise ImageGenerationError(
                        "Не удалось сохранить изображение. Попробуйте позже.",
                        ContentGenerationService._format_debug_details(
                            user_message="Не удалось сохранить файл на диск",
                        ),
                    )

                image_record.image = saved_path
                image_record.save(update_fields=['image'])

                file_url = default_storage.url(saved_path)
                if not file_url.startswith("/"):
                    file_url = "/" + file_url

                saved_images.append({
                    'id': image_record.id,
                    'url': file_url,
                })
                print(f"✅ Изображение {i + 1} сохранено")

            except http_requests.exceptions.Timeout as e:
                user_message = "Превышено время ожидания ответа от API. Попробуйте позже."
                debug_details = ContentGenerationService._format_debug_details(
                    user_message=user_message,
                    extra=f"Exception: {e!r}",
                    traceback_str=traceback.format_exc(),
                )
                ContentGenerationService._mark_image_failed(
                    image_record, user_message, failed_images, debug_details
                )
            except http_requests.exceptions.ConnectionError as e:
                user_message = "Ошибка подключения к серверу генерации изображений. Проверьте интернет-соединение."
                debug_details = ContentGenerationService._format_debug_details(
                    user_message=user_message,
                    extra=f"Exception: {e!r}",
                    traceback_str=traceback.format_exc(),
                )
                ContentGenerationService._mark_image_failed(
                    image_record, user_message, failed_images, debug_details
                )
            except ImageGenerationError as e:
                ContentGenerationService._mark_image_failed(
                    image_record, e.user_message, failed_images, e.debug_details
                )
            except Exception as e:
                user_message = "Ошибка при обработке запроса. Попробуйте позже."
                debug_details = ContentGenerationService._format_debug_details(
                    user_message=str(e),
                    extra=f"Exception type: {type(e).__name__}",
                    traceback_str=traceback.format_exc(),
                )
                ContentGenerationService._mark_image_failed(
                    image_record, user_message, failed_images, debug_details
                )

        if not saved_images:
            user_errors = "; ".join(item['error'] for item in failed_images)
            user_message = user_errors or "Неизвестная ошибка при генерации изображений"
            raise ImageGenerationError(user_message)

        return {
            'images': saved_images,
            'failed': failed_images,
        }

    @staticmethod
    def _resolve_user(request):
        if request.user.is_authenticated:
            return request.user

        user_id = request.data.get('user_id')
        if user_id:
            from django.contrib.auth import get_user_model
            return get_user_model().objects.get(pk=user_id)

        raise ValueError("Пользователь не определён. Требуется аутентификация или поле user_id.")

    @staticmethod
    def _mark_image_failed(image_record, user_message, failed_images, debug_details=None):
        details = debug_details or user_message
        image_record.error_description = details
        image_record.save(update_fields=['error_description'])
        logger.error(
            "Image generation failed (record_id=%s, user_id=%s):\n%s",
            image_record.id,
            image_record.user_id,
            details,
        )
        print(f"❌ Ошибка генерации изображения (record_id={image_record.id}):\n{details}")
        failed_images.append({
            'id': image_record.id,
            'error': user_message,
        })

    @staticmethod
    def _format_debug_details(
            user_message,
            status_code=None,
            raw_response=None,
            error_data=None,
            extra=None,
            traceback_str=None,
    ):
        parts = [f"User message: {user_message}"]

        if status_code is not None:
            parts.append(f"HTTP status: {status_code}")
        if error_data is not None:
            parts.append(
                "AITunnel JSON:\n"
                + json.dumps(error_data, ensure_ascii=False, indent=2)
            )
        elif raw_response:
            parts.append(f"AITunnel raw response:\n{raw_response}")
        if extra:
            parts.append(extra)
        if traceback_str:
            parts.append(f"Traceback:\n{traceback_str}")

        return "\n\n".join(parts)

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