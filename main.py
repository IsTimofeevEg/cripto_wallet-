import sys
import threading
import traceback
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from database import db
from crypto_manager import crypto_manager
from bot import telegram_bot
from main_window import MainWindow
from login_window import LoginWindow
from backup_manager import backup_manager  # Импортируем менеджер бэкапов


def run_telegram_bot():
    """Запуск Telegram бота в отдельном потоке"""
    try:
        telegram_bot.run()
    except Exception as e:
        print(f"Telegram bot error: {e}")
        print(traceback.format_exc())


def main():
    try:
        # Создаем таблицы (если их нет)
        db.create_tables()

        # Очистка старых сессий при запуске
        db.cleanup_expired_sessions()

        # Создаем резервную копию базы данных локально
        db.backup_database()

        # ЗАПУСКАЕМ АВТО-БЭКАПЫ КАЖДЫЙ ЧАС
        try:
            backup_manager.start_auto_backup()
            print("✅ Авто-бэкапы запущены (каждый час)")
        except Exception as e:
            print(f"⚠️ Не удалось запустить авто-бэкапы: {e}")

        # Инициализируем криптовалюты и курсы
        crypto_manager.initialize_currencies()

        # Запускаем Telegram бота в отдельном потоке
        bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
        bot_thread.start()

        app = QApplication(sys.argv)

        # Показываем окно входа
        login_window = LoginWindow()
        if login_window.exec_() == LoginWindow.Accepted:
            user_id = login_window.get_authenticated_user()

            if user_id:
                # Показываем главное окно
                main_window = MainWindow(user_id)
                main_window.show()

                # Запускаем приложение
                exit_code = app.exec_()

                # Бэкап при выходе
                try:
                    backup_manager.backup_on_exit()
                except Exception as e:
                    print(f"⚠️ Ошибка бэкапа при выходе: {e}")

                sys.exit(exit_code)
            else:
                QMessageBox.critical(None, "Ошибка", "Не удалось получить ID пользователя")
                sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"Application error: {e}")
        print(traceback.format_exc())
        QMessageBox.critical(None, "Критическая ошибка", f"Ошибка при запуске приложения: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()