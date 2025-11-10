from django.core.cache import cache
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework import status
import time


def rate_limit_with_timeout(key_func, rate_seconds=120):
    """
    Декоратор для ограничения частоты запросов с возвратом времени ожидания

    Args:
        key_func: функция для получения ключа (обычно из request)
        rate_seconds: интервал в секундах между разрешенными запросами
    """

    def decorator(view_method):
        def wrapped(view, request, *args, **kwargs):
            key = key_func(request)
            cache_key = f"rate_limit:{key}"

            # Получаем время последнего запроса
            last_request_time = cache.get(cache_key)
            current_time = time.time()

            if last_request_time is not None:
                time_passed = current_time - last_request_time
                if time_passed < rate_seconds:
                    # Вычисляем оставшееся время ожидания
                    remaining_seconds = int(rate_seconds - time_passed)

                    response_data = {
                        "message": f"Слишком много запросов. Повторите попытку через {remaining_seconds} секунд",
                        "retry_after": remaining_seconds
                    }

                    return Response(response_data, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # Сохраняем время текущего запроса
            cache.set(cache_key, current_time, rate_seconds)

            return view_method(view, request, *args, **kwargs)

        return wrapped

    return decorator