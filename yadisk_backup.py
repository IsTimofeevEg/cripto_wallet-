import os
import shutil
import tempfile
import zipfile
import json
from datetime import datetime, timedelta
from yadisk import YaDisk
from yadisk.exceptions import YaDiskError
import logging

logger = logging.getLogger(__name__)


class YandexDiskBackup:
    def __init__(self, token, app_folder="crypto_wallet_backups"):
        """
        Инициализация Яндекс.Диск бэкапа

        Args:
            token (str): OAuth токен Яндекс.Диск
            app_folder (str): Папка приложения на Яндекс.Диске
        """
        self.token = token
        self.app_folder = app_folder
        self.disk = YaDisk(token=token)

        # Проверяем соединение
        try:
            if not self.disk.check_token():
                raise ValueError("Недействительный токен Яндекс.Диск")
            logger.info("✅ Соединение с Яндекс.Диск установлено")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Яндекс.Диск: {e}")
            raise

    def ensure_app_folder(self):
        """Создание папки приложения на Яндекс.Диске если её нет"""
        try:
            if not self.disk.exists(self.app_folder):
                self.disk.mkdir(self.app_folder)
                logger.info(f"📁 Папка {self.app_folder} создана на Яндекс.Диске")
            return True
        except YaDiskError as e:
            logger.error(f"❌ Ошибка создания папки: {e}")
            return False

    def create_backup(self, db_path="crypto_wallet.db", metadata=None):
        """
        Создание бэкапа базы данных

        Args:
            db_path (str): Путь к файлу базы данных
            metadata (dict): Дополнительная метаинформация

        Returns:
            str: Имя созданного файла бэкапа или None в случае ошибки
        """
        if not os.path.exists(db_path):
            logger.error(f"❌ Файл базы данных не найден: {db_path}")
            return None

        try:
            # Создаем временную директорию для бэкапа
            temp_dir = tempfile.mkdtemp(prefix="crypto_backup_")

            # Копируем файл базы данных
            backup_file = os.path.join(temp_dir, "crypto_wallet.db")
            shutil.copy2(db_path, backup_file)

            # Создаем файл с метаданными
            meta = {
                "backup_date": datetime.now().isoformat(),
                "db_size": os.path.getsize(db_path),
                "app_version": "1.0.0",
                "description": "Автоматический бэкап крипто-кошелька"
            }

            if metadata:
                meta.update(metadata)

            meta_file = os.path.join(temp_dir, "metadata.json")
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

            # Создаем архив
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_filename = f"crypto_wallet_backup_{timestamp}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(backup_file, "crypto_wallet.db")
                zipf.write(meta_file, "metadata.json")

            # Загружаем на Яндекс.Диск
            if self.ensure_app_folder():
                remote_path = f"{self.app_folder}/{zip_filename}"
                self.disk.upload(zip_path, remote_path)
                logger.info(f"✅ Бэкап загружен на Яндекс.Диск: {zip_filename}")

                # Очищаем старые бэкапы (оставляем последние 7)
                self.cleanup_old_backups()

                return zip_filename

            # Очищаем временную директорию
            shutil.rmtree(temp_dir)

        except Exception as e:
            logger.error(f"❌ Ошибка создания бэкапа: {e}")
            return None

    def cleanup_old_backups(self, keep_last=7):
        """
        Очистка старых бэкапов

        Args:
            keep_last (int): Сколько последних бэкапов оставить
        """
        try:
            if not self.disk.exists(self.app_folder):
                return

            # Получаем список файлов
            files = []
            for item in self.disk.listdir(self.app_folder):
                if item.name.endswith('.zip'):
                    files.append({
                        'name': item.name,
                        'modified': item.modified
                    })

            # Сортируем по дате изменения (новые сначала)
            files.sort(key=lambda x: x['modified'], reverse=True)

            # Удаляем старые
            if len(files) > keep_last:
                for file in files[keep_last:]:
                    remote_path = f"{self.app_folder}/{file['name']}"
                    self.disk.remove(remote_path, permanently=True)
                    logger.info(f"🗑️ Удален старый бэкап: {file['name']}")

        except Exception as e:
            logger.error(f"❌ Ошибка очистки старых бэкапов: {e}")

    def list_backups(self):
        """
        Получение списка бэкапов на Яндекс.Диске

        Returns:
            list: Список бэкапов с информацией
        """
        backups = []

        try:
            if not self.disk.exists(self.app_folder):
                return backups

            for item in self.disk.listdir(self.app_folder):
                if item.name.endswith('.zip'):
                    backups.append({
                        'name': item.name,
                        'size': item.size,
                        'modified': item.modified,
                        'path': item.path
                    })

            # Сортируем по дате (новые сначала)
            backups.sort(key=lambda x: x['modified'], reverse=True)

        except Exception as e:
            logger.error(f"❌ Ошибка получения списка бэкапов: {e}")

        return backups

    def download_backup(self, backup_name, download_path=None):
        """
        Скачивание бэкапа с Яндекс.Диска

        Args:
            backup_name (str): Имя файла бэкапа
            download_path (str): Путь для сохранения (опционально)

        Returns:
            str: Путь к скачанному файлу или None в случае ошибки
        """
        try:
            remote_path = f"{self.app_folder}/{backup_name}"

            if not self.disk.exists(remote_path):
                logger.error(f"❌ Бэкап не найден: {backup_name}")
                return None

            # Создаем папку для загрузок если нет
            if download_path is None:
                download_path = "backups/downloads"

            os.makedirs(download_path, exist_ok=True)

            local_path = os.path.join(download_path, backup_name)
            self.disk.download(remote_path, local_path)

            logger.info(f"✅ Бэкап скачан: {local_path}")
            return local_path

        except Exception as e:
            logger.error(f"❌ Ошибка скачивания бэкапа: {e}")
            return None

    def restore_from_backup(self, backup_name, db_path="crypto_wallet.db"):
        """
        Восстановление базы данных из бэкапа

        Args:
            backup_name (str): Имя файла бэкапа
            db_path (str): Путь для восстановления базы данных

        Returns:
            bool: Успешно ли восстановление
        """
        try:
            # Скачиваем бэкап
            zip_path = self.download_backup(backup_name)
            if not zip_path:
                return False

            # Создаем временную директорию для распаковки
            temp_dir = tempfile.mkdtemp(prefix="crypto_restore_")

            # Распаковываем архив
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(temp_dir)

            # Находим файл базы данных
            db_backup = os.path.join(temp_dir, "crypto_wallet.db")
            if not os.path.exists(db_backup):
                logger.error("❌ Файл базы данных не найден в архиве")
                shutil.rmtree(temp_dir)
                return False

            # Создаем бэкап текущей базы данных
            if os.path.exists(db_path):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_current = f"{db_path}.pre_restore_{timestamp}"
                shutil.copy2(db_path, backup_current)
                logger.info(f"📋 Создан бэкап текущей базы: {backup_current}")

            # Восстанавливаем базу данных
            shutil.copy2(db_backup, db_path)

            # Читаем метаданные
            meta_file = os.path.join(temp_dir, "metadata.json")
            if os.path.exists(meta_file):
                with open(meta_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                logger.info(f"📊 Восстановлен бэкап от: {metadata.get('backup_date')}")

            # Очищаем временные файлы
            shutil.rmtree(temp_dir)

            logger.info("✅ База данных успешно восстановлена!")
            return True

        except Exception as e:
            logger.error(f"❌ Ошибка восстановления из бэкапа: {e}")
            return False

    def get_backup_info(self, backup_name):
        """
        Получение информации о бэкапе

        Args:
            backup_name (str): Имя файла бэкапа

        Returns:
            dict: Информация о бэкапе или None
        """
        try:
            # Создаем временную директорию
            temp_dir = tempfile.mkdtemp(prefix="crypto_info_")

            # Скачиваем архив
            zip_path = self.download_backup(backup_name, temp_dir)
            if not zip_path:
                shutil.rmtree(temp_dir)
                return None

            # Извлекаем метаданные
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                # Получаем список файлов
                file_list = zipf.namelist()

                # Ищем файл метаданных
                if "metadata.json" in file_list:
                    with zipf.open("metadata.json") as f:
                        metadata = json.load(f)

                    # Добавляем информацию о файле
                    file_info = self.disk.get_meta(f"{self.app_folder}/{backup_name}")

                    result = {
                        'name': backup_name,
                        'size': file_info.size,
                        'modified': file_info.modified,
                        'created': file_info.created,
                        'metadata': metadata
                    }

                    # Очищаем временные файлы
                    shutil.rmtree(temp_dir)
                    return result

            shutil.rmtree(temp_dir)
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о бэкапе: {e}")
            return None

    def get_disk_info(self):
        """
        Получение информации о Яндекс.Диске

        Returns:
            dict: Информация о диске
        """
        try:
            info = self.disk.get_disk_info()
            return {
                'total_space': info.total_space,
                'used_space': info.used_space,
                'free_space': info.free_space,
                'trash_size': info.trash_size
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о диске: {e}")
            return None


# Создаем экземпляр для использования в приложении
yadisk_backup = YandexDiskBackup(token="y0__xCW4LiVBxjqkjwg0MPQyBUwhKuk2QeCZsFVQw3RgamSSMv-2OIDtGDuWQ")