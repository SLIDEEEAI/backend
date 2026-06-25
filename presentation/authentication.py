from django.core.cache import cache
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication as SimpleJWTAuthentication

from .models import User


class JWTAuthentication(SimpleJWTAuthentication):
    def authenticate(self, request):
        auth_result = super().authenticate(request)
        if auth_result is None:
            return None

        user, validated_token = auth_result
        cache_key = f'user-last-seen-update:{user.pk}'

        if cache.add(cache_key, True, timeout=60):
            User.objects.filter(pk=user.pk).update(last_seen_at=timezone.now())

        return user, validated_token
