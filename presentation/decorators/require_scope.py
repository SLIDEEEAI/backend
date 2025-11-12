from functools import wraps
from django.http import JsonResponse
from presentation.service_modules.permission_service import PermissionService

# Декоратор для API
def require_scope(scope_code):
    """Декоратор для проверки скоупа в API"""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(self, request, *args, **kwargs):
            if not PermissionService.user_has_scope(request.user, scope_code):
                return JsonResponse(
                    {'error': f'Scope {scope_code} required'},
                    status=403
                )
            return view_func(self, request, *args, **kwargs)

        return _wrapped_view

    return decorator