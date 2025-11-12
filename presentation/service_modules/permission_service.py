class PermissionService:

    @staticmethod
    def user_has_scope(user, scope_code):
        """Проверяет доступ пользователя к скоупу"""
        return user.has_scope(scope_code)

    @staticmethod
    def get_user_scopes(user):
        """Возвращает все скоупы пользователя"""
        return user.get_scopes()