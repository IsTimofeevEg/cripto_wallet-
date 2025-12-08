from enum import Enum
from models import UserRole


class RoleManager:
    """Менеджер ролей пользователей"""

    # Словарь ролей с их описанием и правами
    ROLES = {
        UserRole.USER: {
            'name': 'Пользователь',
            'description': 'Обычный пользователь системы',
            'permissions': [
                'view_balance',
                'make_transfers',
                'create_exchanges',
                'view_history',
                'update_profile',
                'link_telegram'
            ]
        },
        UserRole.MODERATOR: {
            'name': 'Модератор',
            'description': 'Модератор системы',
            'permissions': [
                'view_balance',
                'make_transfers',
                'create_exchanges',
                'view_history',
                'update_profile',
                'link_telegram',
                'view_all_users',           # Может просматривать всех пользователей
                'view_user_transactions_30', # Может смотреть операции за 30 дней
                'block_user',               # Может блокировать пользователей (кроме админов)
                'unblock_user',             # Может разблокировать пользователей
                'view_recent_activity',     # Может видеть последние операции
                'monitor_users'             # Может мониторить пользователей
            ]
        },
        UserRole.ADMIN: {
            'name': 'Администратор',
            'description': 'Полный доступ к системе',
            'permissions': [
                'view_balance',
                'make_transfers',
                'create_exchanges',
                'view_history',
                'update_profile',
                'link_telegram',
                'view_all_users',           # Может просматривать всех пользователей
                'view_user_transactions_all', # Может смотреть все операции
                'view_user_transactions_30', # Может смотреть операции за 30 дней
                'block_user',               # Может блокировать пользователей
                'unblock_user',             # Может разблокировать пользователей
                'change_user_role',         # Может менять роли
                'view_all_transactions',    # Может смотреть все транзакции
                'manage_currencies',        # Может управлять валютами
                'view_exchange_rates',      # Может смотреть курсы валют
                'add_currency',             # Может добавлять валюты
                'manage_settings',          # Может управлять настройками системы
                'view_recent_activity',     # Может видеть последние операции
                'monitor_users',            # Может мониторить пользователей
                'view_system_logs'          # Может просматривать системные логи
            ]
        }
    }

    @classmethod
    def get_role_display(cls, role):
        """Получить отображаемое имя роли"""
        role_info = cls.ROLES.get(role)
        return role_info['name'] if role_info else 'Неизвестно'

    @classmethod
    def get_role_description(cls, role):
        """Получить описание роли"""
        role_info = cls.ROLES.get(role)
        return role_info['description'] if role_info else ''

    @classmethod
    def get_role_permissions(cls, role):
        """Получить список разрешений для роли"""
        role_info = cls.ROLES.get(role)
        return role_info['permissions'] if role_info else []

    @classmethod
    def has_permission(cls, role, permission):
        """Проверить, есть ли у роли определенное разрешение"""
        permissions = cls.get_role_permissions(role)
        return permission in permissions

    @classmethod
    def get_all_roles(cls):
        """Получить все доступные роли"""
        return list(cls.ROLES.keys())

    @classmethod
    def get_role_choices(cls):
        """Получить список ролей для выбора в UI"""
        return [
            (UserRole.USER.value, 'Пользователь'),
            (UserRole.MODERATOR.value, 'Модератор'),
            (UserRole.ADMIN.value, 'Администратор')
        ]


# Функции для проверки прав
def check_permission(user, permission):
    """Проверить разрешение для пользователя"""
    if not user or not hasattr(user, 'role'):
        return False
    return RoleManager.has_permission(user.role, permission)


def has_permission(user, permission):
    """Проверить разрешение (альтернативное название)"""
    return check_permission(user, permission)