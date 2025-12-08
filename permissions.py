from functools import wraps
from PyQt5.QtWidgets import QMessageBox
from models import UserRole
from roles import check_permission


def require_permission_decorator(permission):
    """Декоратор для проверки разрешений в PyQt"""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'user'):
                QMessageBox.warning(self, "Ошибка", "Пользователь не аутентифицирован")
                return

            if not check_permission(self.user, permission):
                QMessageBox.warning(self, "Доступ запрещен",
                                    f"Недостаточно прав для выполнения этого действия")
                return

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def require_admin(func):
    """Декоратор для проверки прав администратора"""
    return require_permission_decorator('manage_settings')(func)


def require_moderator(func):
    """Декоратор для проверки прав модератора"""
    def wrapper(self, *args, **kwargs):
        if not hasattr(self, 'user'):
            QMessageBox.warning(self, "Ошибка", "Пользователь не аутентифицирован")
            return

        # Модератор или админ имеют доступ
        if not check_permission(self.user, 'view_all_users'):
            QMessageBox.warning(self, "Доступ запрещен",
                                "Требуются права модератора или администратора")
            return

        return func(self, *args, **kwargs)

    return wrapper


def require_permission(permission):
    """Декоратор для проверки конкретного разрешения"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, 'user'):
                QMessageBox.warning(self, "Ошибка", "Пользователь не аутентифицирован")
                return None

            if not check_permission(self.user, permission):
                QMessageBox.warning(self, "Доступ запрещен",
                                    f"Недостаточно прав. Требуется разрешение: {permission}")
                return None

            return func(self, *args, **kwargs)
        return wrapper
    return decorator