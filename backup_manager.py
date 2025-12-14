import threading
import schedule
import time
from datetime import datetime, timedelta
from database import db
from yadisk_backup import yadisk_backup
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    def __init__(self):
        self.running = False
        self.thread = None

        # Настройки бэкапов - КАЖДЫЙ ЧАС
        self.settings = {
            'auto_backup': True,
            'backup_interval_hours': 1,  # КАЖДЫЙ ЧАС
            'keep_last_backups': 24,  # Хранить 24 последних бэкапа (сутки)
            'backup_on_start': True,  # Бэкап при запуске
            'backup_on_exit': True  # Бэкап при выходе
        }

    def start_auto_backup(self):
        """Запуск автоматического бэкапа КАЖДЫЙ ЧАС"""
        if not self.settings['auto_backup']:
            logger.info("⏸️ Автоматический бэкап отключен")
            return

        self.running = True

        # Бэкап при старте
        if self.settings['backup_on_start']:
            logger.info("🔄 Создание бэкапа при запуске...")
            self.create_backup("Автоматический бэкап при запуске приложения")

        # Настройка расписания - КАЖДЫЙ ЧАС
        logger.info(f"⏰ Настройка авто-бэкапов каждые {self.settings['backup_interval_hours']} часов")

        schedule.every(self.settings['backup_interval_hours']).hours.do(
            self.create_scheduled_backup
        )

        # Также делаем бэкап каждое утро в 3:00
        schedule.every().day.at("03:00").do(
            self.create_backup,
            description="Ежедневный утренний бэкап"
        )

        # Запуск в отдельном потоке
        def scheduler_loop():
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту

        self.thread = threading.Thread(target=scheduler_loop, daemon=True)
        self.thread.start()

        next_run = schedule.next_run()
        if next_run:
            next_time = next_run.strftime("%H:%M:%S")
            logger.info(f"✅ Автоматический бэкап запущен. Следующий бэкап в: {next_time}")
        else:
            logger.info(f"✅ Автоматический бэкап запущен (интервал: {self.settings['backup_interval_hours']} часов)")

    def create_scheduled_backup(self):
        """Создание запланированного бэкапа"""
        try:
            current_hour = datetime.now().hour
            description = f"Авто-бэкап в {current_hour:02d}:00"

            logger.info(f"⏰ Создание запланированного бэкапа: {description}")

            backup_name = self.create_backup(description)

            if backup_name:
                # Очищаем старые бэкапы
                self.cleanup_old_backups()

                next_run = schedule.next_run()
                if next_run:
                    next_time = next_run.strftime("%H:%M:%S")
                    logger.info(f"✅ Запланированный бэкап создан. Следующий в: {next_time}")

        except Exception as e:
            logger.error(f"❌ Ошибка запланированного бэкапа: {e}")

    def cleanup_old_backups(self):
        """Очистка старых бэкапов на Яндекс.Диске"""
        try:
            yadisk_backup.cleanup_old_backups(keep_last=self.settings['keep_last_backups'])
        except Exception as e:
            logger.error(f"❌ Ошибка очистки старых бэкапов: {e}")

    def stop_auto_backup(self):
        """Остановка автоматического бэкапа"""
        self.running = False
        schedule.clear()

        if self.thread:
            self.thread.join(timeout=5)

        logger.info("⏸️ Автоматический бэкап остановлен")

    def create_backup(self, description="", additional_metadata=None):
        """
        Создание бэкапа

        Args:
            description (str): Описание бэкапа
            additional_metadata (dict): Дополнительные метаданные

        Returns:
            str: Имя созданного бэкапа или None
        """
        try:
            logger.info(f"🔄 Создание бэкапа: {description}")

            # Создаем локальный бэкап базы данных
            db.backup_database()

            # Подготавливаем метаданные
            metadata = {
                'description': description,
                'created_by': 'BackupManager',
                'app_state': 'running',
                'timestamp': datetime.now().isoformat(),
                'hour': datetime.now().hour
            }

            if additional_metadata:
                metadata.update(additional_metadata)

            # Создаем бэкап на Яндекс.Диске
            backup_name = yadisk_backup.create_backup(
                db_path="crypto_wallet.db",
                metadata=metadata
            )

            if backup_name:
                logger.info(f"✅ Бэкап создан: {backup_name}")
                return backup_name
            else:
                logger.error("❌ Не удалось создать бэкап на Яндекс.Диске")
                return None

        except Exception as e:
            logger.error(f"❌ Ошибка при создании бэкапа: {e}")
            return None

    def get_latest_backup(self):
        """
        Получение последнего бэкапа

        Returns:
            dict: Информация о последнем бэкапе или None
        """
        try:
            backups = yadisk_backup.list_backups()
            if backups:
                latest = backups[0]  # Уже отсортированы по дате (новые первыми)
                return latest
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка получения последнего бэкапа: {e}")
            return None

    def get_backup_list(self, limit=10):
        """
        Получение списка бэкапов

        Args:
            limit (int): Максимальное количество бэкапов

        Returns:
            list: Список бэкапов с информацией
        """
        try:
            backups = yadisk_backup.list_backups()
            return backups[:limit]
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка бэкапов: {e}")
            return []

    def restore_latest_backup(self):
        """
        Восстановление из последнего бэкапа

        Returns:
            tuple: (success, backup_name, error_message)
        """
        try:
            latest = self.get_latest_backup()
            if not latest:
                return False, None, "Нет доступных бэкапов"

            backup_name = latest['name']
            logger.info(f"🔄 Восстановление из последнего бэкапа: {backup_name}")

            success = yadisk_backup.restore_from_backup(backup_name)

            if success:
                logger.info(f"✅ Восстановление успешно: {backup_name}")

                # Пересоздаем таблицы после восстановления
                db.create_tables()

                # Обновляем курсы валют
                from crypto_manager import crypto_manager
                crypto_manager.update_exchange_rates()

                return True, backup_name, None
            else:
                error_msg = f"Не удалось восстановить из бэкапа: {backup_name}"
                logger.error(f"❌ {error_msg}")
                return False, backup_name, error_msg

        except Exception as e:
            error_msg = f"Ошибка восстановления: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, None, error_msg

    def restore_backup(self, backup_name):
        try:
            logger.info(f"🔄 Восстановление из бэкапа: {backup_name}")

            success = yadisk_backup.restore_from_backup(backup_name)

            if success:
                logger.info(f"✅ Восстановление успешно: {backup_name}")

                # Пересоздаем таблицы после восстановления
                db.create_tables()

                # Обновляем курсы валют
                from crypto_manager import crypto_manager
                crypto_manager.update_exchange_rates()

                return True, None
            else:
                error_msg = f"Не удалось восстановить из бэкапа: {backup_name}"
                logger.error(f"❌ {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"Ошибка восстановления: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg

    def get_backup_info(self, backup_name):
        """Получение информации о бэкапе"""
        try:
            info = yadisk_backup.get_backup_info(backup_name)
            return info
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о бэкапе: {e}")
            return None

    def get_disk_info(self):
        """Получение информации о Яндекс.Диске"""
        try:
            info = yadisk_backup.get_disk_info()
            return info
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о диске: {e}")
            return None

    def update_settings(self, **kwargs):
        """Обновление настроек бэкапа"""
        for key, value in kwargs.items():
            if key in self.settings:
                self.settings[key] = value

        # Перезапускаем автоматический бэкап если он включен
        if self.running:
            self.stop_auto_backup()
            self.start_auto_backup()

        logger.info("⚙️ Настройки бэкапа обновлены")

    def backup_on_exit(self):
        """Бэкап при выходе из приложения"""
        if self.settings['backup_on_exit']:
            logger.info("🔄 Создание бэкапа перед выходом...")
            self.create_backup("Бэкап перед выходом из приложения")
            self.stop_auto_backup()


# Создаем экземпляр менеджера
backup_manager = BackupManager()