from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QMessageBox, QCheckBox,
                             QFrame, QStackedWidget, QWidget)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
from sqlalchemy.orm import Session
from database import db
from models import User
from transaction_utils import execute_in_transaction, register_user_transaction
from datetime import datetime
import os
import random


class LoginWindow(QDialog):
    # Сигналы
    update_timer_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.authenticated_user = None
        self.tg_code = None
        self.timer = None
        self.time_left = 0
        self.current_mode = "login"
        self.saved_phone = None
        self.saved_user = None

        # Создаем ВСЕ виджеты в конструкторе
        self.create_widgets()

        # Подключаем сигналы
        self.update_timer_signal.connect(self.update_timer_display)

        self.setup_ui()
        self.check_saved_profile()

    def create_widgets(self):
        """Создание всех виджетов один раз при инициализации"""

        # Виджеты для быстрого входа
        self.quick_login_frame = QFrame()
        self.quick_user_info = QLabel("")
        self.quick_login_btn = QPushButton("Войти в этот профиль")
        self.quick_remove_btn = QPushButton("Удалить профиль")

        # Виджеты для страницы входа
        self.login_phone_input = QLineEdit()
        self.login_code_input = QLineEdit()
        self.login_get_code_btn = QPushButton("📲 Получить код в Telegram")
        self.login_timer_label = QLabel("")
        self.login_submit_btn = QPushButton("✅ Войти")

        # Виджеты для страницы регистрации
        self.register_phone_input = QLineEdit()
        self.register_name_input = QLineEdit()
        self.register_telegram_input = QLineEdit()
        self.register_code_input = QLineEdit()
        self.register_get_code_btn = QPushButton("📲 Получить код подтверждения")
        self.register_timer_label = QLabel("")
        self.register_save_checkbox = QCheckBox("💾 Сохранить профиль для быстрого входа")
        self.register_submit_btn = QPushButton("✅ Зарегистрироваться")

        # Кнопки переключения режимов
        self.login_mode_btn = QPushButton("Вход")
        self.register_mode_btn = QPushButton("Регистрация")

        # Stacked widget
        self.stacked_widget = QStackedWidget()

        # Страницы
        self.quick_login_page = None
        self.login_page = None
        self.register_page = None

    def setup_ui(self):
        """Настройка интерфейса"""
        self.setWindowTitle("Крипто Кошелек - Авторизация")
        self.setGeometry(300, 300, 500, 500)
        self.setModal(True)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # Заголовок
        title = QLabel("🔐 Крипто Кошелек")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2E8B57; margin-bottom: 15px;")
        main_layout.addWidget(title)

        # Создаем страницы
        self.create_quick_login_page()
        self.create_login_page()
        self.create_register_page()

        # Добавляем страницы в stacked widget
        self.stacked_widget.addWidget(self.quick_login_page)
        self.stacked_widget.addWidget(self.login_page)
        self.stacked_widget.addWidget(self.register_page)

        main_layout.addWidget(self.stacked_widget)

        # Кнопки переключения
        mode_layout = QHBoxLayout()

        self.login_mode_btn.setCheckable(True)
        self.login_mode_btn.setChecked(True)
        self.login_mode_btn.clicked.connect(lambda: self.switch_mode("login"))
        self.login_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E8B57;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
                border: 2px solid #2E8B57;
            }
        """)
        mode_layout.addWidget(self.login_mode_btn)

        self.register_mode_btn.setCheckable(True)
        self.register_mode_btn.clicked.connect(lambda: self.switch_mode("register"))
        self.register_mode_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #2E8B57;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
                border: 2px solid #2E8B57;
            }
            QPushButton:hover {
                background-color: #F0FFF0;
            }
        """)
        mode_layout.addWidget(self.register_mode_btn)

        main_layout.addLayout(mode_layout)

        self.setLayout(main_layout)

    def create_quick_login_page(self):
        """Создание страницы быстрого входа"""
        self.quick_login_page = QWidget()
        layout = QVBoxLayout(self.quick_login_page)

        self.quick_login_frame.setFrameStyle(QFrame.Box)
        self.quick_login_frame.setStyleSheet("""
            QFrame {
                background-color: #F0FFF0;
                border: 2px solid #2E8B57;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0px;
            }
        """)
        quick_layout = QVBoxLayout(self.quick_login_frame)

        quick_title = QLabel("🚀 Быстрый вход")
        quick_title.setFont(QFont("Arial", 14, QFont.Bold))
        quick_title.setStyleSheet("color: #2E8B57; margin-bottom: 10px;")
        quick_layout.addWidget(quick_title)

        self.quick_user_info.setWordWrap(True)
        self.quick_user_info.setStyleSheet(
            "margin: 10px 0px; padding: 10px; background-color: white; border-radius: 5px;")
        quick_layout.addWidget(self.quick_user_info)

        quick_buttons_layout = QHBoxLayout()
        quick_buttons_layout.setSpacing(10)

        self.quick_login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E8B57;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #3CB371;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.quick_login_btn.clicked.connect(self.quick_login)
        quick_buttons_layout.addWidget(self.quick_login_btn)

        self.quick_remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #FF8C8C;
            }
        """)
        self.quick_remove_btn.clicked.connect(self.remove_saved_profile)
        quick_buttons_layout.addWidget(self.quick_remove_btn)

        quick_layout.addLayout(quick_buttons_layout)
        layout.addWidget(self.quick_login_frame)

        separator = QLabel("───── или войдите вручную ─────")
        separator.setAlignment(Qt.AlignCenter)
        separator.setStyleSheet("color: #666; margin: 15px 0px; font-style: italic;")
        layout.addWidget(separator)

        manual_login_btn = QPushButton("Войти с другим номером")
        manual_login_btn.setStyleSheet("""
            QPushButton {
                background-color: #4682B4;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5A9BD3;
            }
        """)
        manual_login_btn.clicked.connect(lambda: self.switch_mode("login"))
        layout.addWidget(manual_login_btn)

        layout.addStretch()

    def create_login_page(self):
        """Создание страницы входа"""
        self.login_page = QWidget()
        layout = QVBoxLayout(self.login_page)
        layout.setSpacing(15)

        title = QLabel("🔐 Вход в систему")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2E8B57; margin-bottom: 10px;")
        layout.addWidget(title)

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(10)

        # Телефон
        phone_group = QFrame()
        phone_group.setStyleSheet("background-color: #f9f9f9; border-radius: 5px; padding: 10px;")
        phone_layout = QHBoxLayout(phone_group)

        phone_label = QLabel("📱 Номер телефона:")
        phone_label.setFont(QFont("Arial", 10))
        phone_layout.addWidget(phone_label)

        self.login_phone_input.setPlaceholderText("+79991234567")
        self.login_phone_input.setStyleSheet("padding: 8px; border-radius: 4px; border: 1px solid #ddd;")
        phone_layout.addWidget(self.login_phone_input)

        form_layout.addWidget(phone_group)

        # Кнопка получения кода
        self.login_get_code_btn.setStyleSheet("""
            QPushButton {
                background-color: #4682B4;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5A9BD3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.login_get_code_btn.clicked.connect(lambda: self.get_telegram_code("login"))
        form_layout.addWidget(self.login_get_code_btn)

        # Код подтверждения
        code_group = QFrame()
        code_group.setStyleSheet("background-color: #f9f9f9; border-radius: 5px; padding: 10px;")
        code_layout = QVBoxLayout(code_group)

        code_label = QLabel("🔐 Код из Telegram:")
        code_label.setFont(QFont("Arial", 10))
        code_layout.addWidget(code_label)

        self.login_code_input.setPlaceholderText("Введите 6-значный код")
        self.login_code_input.setEnabled(False)
        self.login_code_input.setStyleSheet(
            "padding: 8px; border-radius: 4px; border: 1px solid #ddd; font-size: 16px; letter-spacing: 2px;")
        code_layout.addWidget(self.login_code_input)

        form_layout.addWidget(code_group)

        # Таймер
        self.login_timer_label.setAlignment(Qt.AlignCenter)
        self.login_timer_label.setStyleSheet("color: #FF6B6B; font-weight: bold; font-size: 13px;")
        form_layout.addWidget(self.login_timer_label)

        layout.addWidget(form_widget)

        # Кнопка входа
        self.login_submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        self.login_submit_btn.clicked.connect(self.perform_login)
        layout.addWidget(self.login_submit_btn)

        # Ссылка на регистрацию
        register_link = QLabel("Нет аккаунта? <a href='register'>Зарегистрироваться</a>")
        register_link.setAlignment(Qt.AlignCenter)
        register_link.setStyleSheet("color: #666; margin-top: 15px;")
        register_link.linkActivated.connect(lambda: self.switch_mode("register"))
        layout.addWidget(register_link)

        layout.addStretch()

    def create_register_page(self):
        """Создание страницы регистрации"""
        self.register_page = QWidget()
        layout = QVBoxLayout(self.register_page)
        layout.setSpacing(15)

        title = QLabel("📝 Регистрация")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2196F3; margin-bottom: 10px;")
        layout.addWidget(title)

        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(10)

        # Телефон
        phone_group = QFrame()
        phone_group.setStyleSheet("background-color: #f9f9f9; border-radius: 5px; padding: 10px;")
        phone_layout = QHBoxLayout(phone_group)

        phone_label = QLabel("📱 Номер телефона:")
        phone_label.setFont(QFont("Arial", 10))
        phone_layout.addWidget(phone_label)

        self.register_phone_input.setPlaceholderText("+79991234567")
        self.register_phone_input.setStyleSheet("padding: 8px; border-radius: 4px; border: 1px solid #ddd;")
        phone_layout.addWidget(self.register_phone_input)

        form_layout.addWidget(phone_group)

        # ФИО
        name_group = QFrame()
        name_group.setStyleSheet("background-color: #f9f9f9; border-radius: 5px; padding: 10px;")
        name_layout = QHBoxLayout(name_group)

        name_label = QLabel("👤 ФИО:")
        name_label.setFont(QFont("Arial", 10))
        name_layout.addWidget(name_label)

        self.register_name_input.setPlaceholderText("Иванов Иван Иванович")
        self.register_name_input.setStyleSheet("padding: 8px; border-radius: 4px; border: 1px solid #ddd;")
        name_layout.addWidget(self.register_name_input)

        form_layout.addWidget(name_group)

        # Telegram ID
        tg_group = QFrame()
        tg_group.setStyleSheet("background-color: #f9f9f9; border-radius: 5px; padding: 10px;")
        tg_layout = QHBoxLayout(tg_group)

        tg_label = QLabel("🤖 Telegram ID:")
        tg_label.setFont(QFont("Arial", 10))
        tg_layout.addWidget(tg_label)

        self.register_telegram_input.setPlaceholderText("Ваш ID в Telegram (цифры)")
        self.register_telegram_input.setStyleSheet("padding: 8px; border-radius: 4px; border: 1px solid #ddd;")
        tg_layout.addWidget(self.register_telegram_input)

        form_layout.addWidget(tg_group)

        # Кнопка получения кода
        self.register_get_code_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #BA68C8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.register_get_code_btn.clicked.connect(lambda: self.get_telegram_code("register"))
        form_layout.addWidget(self.register_get_code_btn)

        # Код подтверждения
        code_group = QFrame()
        code_group.setStyleSheet("background-color: #f9f9f9; border-radius: 5px; padding: 10px;")
        code_layout = QVBoxLayout(code_group)

        code_label = QLabel("🔐 Код из Telegram:")
        code_label.setFont(QFont("Arial", 10))
        code_layout.addWidget(code_label)

        self.register_code_input.setPlaceholderText("Введите 6-значный код")
        self.register_code_input.setEnabled(False)
        self.register_code_input.setStyleSheet(
            "padding: 8px; border-radius: 4px; border: 1px solid #ddd; font-size: 16px; letter-spacing: 2px;")
        code_layout.addWidget(self.register_code_input)

        form_layout.addWidget(code_group)

        # Таймер
        self.register_timer_label.setAlignment(Qt.AlignCenter)
        self.register_timer_label.setStyleSheet("color: #FF6B6B; font-weight: bold; font-size: 13px;")
        form_layout.addWidget(self.register_timer_label)

        # Чекбокс
        self.register_save_checkbox.setChecked(True)
        self.register_save_checkbox.setStyleSheet("margin-top: 10px;")
        form_layout.addWidget(self.register_save_checkbox)

        layout.addWidget(form_widget)

        # Кнопка регистрации
        self.register_submit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 14px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #42A5F5;
            }
        """)
        self.register_submit_btn.clicked.connect(self.perform_register)
        layout.addWidget(self.register_submit_btn)

        # Ссылка на вход
        login_link = QLabel("Уже есть аккаунт? <a href='login'>Войти</a>")
        login_link.setAlignment(Qt.AlignCenter)
        login_link.setStyleSheet("color: #666; margin-top: 15px;")
        login_link.linkActivated.connect(lambda: self.switch_mode("login"))
        layout.addWidget(login_link)

        layout.addStretch()

    def switch_mode(self, mode):
        """Переключение между режимами"""
        try:
            self.current_mode = mode
            self.stop_timer()

            if mode == "login":
                self.stacked_widget.setCurrentWidget(self.login_page)
                self.login_mode_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2E8B57;
                        color: white;
                        font-weight: bold;
                        padding: 8px;
                        border-radius: 4px;
                        border: 2px solid #2E8B57;
                    }
                """)
                self.register_mode_btn.setStyleSheet("""
                    QPushButton {
                        background-color: white;
                        color: #2E8B57;
                        font-weight: bold;
                        padding: 8px;
                        border-radius: 4px;
                        border: 2px solid #2E8B57;
                    }
                    QPushButton:hover {
                        background-color: #F0FFF0;
                    }
                """)
            else:
                self.stacked_widget.setCurrentWidget(self.register_page)
                self.login_mode_btn.setStyleSheet("""
                    QPushButton {
                        background-color: white;
                        color: #2E8B57;
                        font-weight: bold;
                        padding: 8px;
                        border-radius: 4px;
                        border: 2px solid #2E8B57;
                    }
                    QPushButton:hover {
                        background-color: #F0FFF0;
                    }
                """)
                self.register_mode_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2196F3;
                        color: white;
                        font-weight: bold;
                        padding: 8px;
                        border-radius: 4px;
                        border: 2px solid #2196F3;
                    }
                """)
        except Exception as e:
            print(f"Ошибка при переключении режима: {e}")

    def update_timer_display(self, text):
        """Обновить отображение таймера"""
        if self.current_mode == "login":
            self.login_timer_label.setText(text)
        else:
            self.register_timer_label.setText(text)

    def check_saved_profile(self):
        """Проверка сохраненного профиля"""
        try:
            if os.path.exists('saved_profile.txt'):
                with open('saved_profile.txt', 'r', encoding='utf-8') as f:
                    phone = f.read().strip()

                if phone:
                    session = db.get_session()
                    try:
                        user = session.query(User).filter_by(phone=phone).first()
                        if user:
                            self.saved_phone = phone
                            self.saved_user = user

                            self.quick_user_info.setText(
                                f"👤 {user.full_name}\n"
                                f"📞 {user.phone}\n"
                                f"🤖 Telegram: {'✅' if user.telegram_id else '❌'}\n"
                                f"👑 Роль: {user.get_role_display()}\n"
                                f"📅 Регистрация: {user.registration_date.strftime('%d.%m.%Y')}"
                            )
                            self.quick_login_frame.setVisible(True)
                            self.stacked_widget.setCurrentWidget(self.quick_login_page)
                        else:
                            # Пользователь не найден, удаляем файл
                            os.remove('saved_profile.txt')
                            self.quick_login_frame.setVisible(False)
                    except Exception as e:
                        print(f"Ошибка проверки профиля: {e}")
                    finally:
                        session.close()
            else:
                self.quick_login_frame.setVisible(False)
        except Exception as e:
            print(f"Ошибка чтения сохраненного профиля: {e}")

    def generate_telegram_code(self):
        """Генерация 6-значного кода"""
        return str(random.randint(100000, 999999))

    def get_telegram_code(self, mode):
        """Получение кода для Telegram подтверждения"""
        try:
            if mode == "login":
                phone = self.login_phone_input.text().strip()
                telegram_id = None
            else:
                phone = self.register_phone_input.text().strip()
                telegram_id = self.register_telegram_input.text().strip()

            if not phone:
                QMessageBox.warning(self, "Ошибка", "Введите номер телефона!")
                return

            # Проверяем в основном потоке
            session = db.get_session()
            try:
                user = session.query(User).filter_by(phone=phone).first()

                if mode == "login":
                    if not user:
                        QMessageBox.warning(self, "Ошибка", "Пользователь не найден! Зарегистрируйтесь.")
                        return
                    if not user.telegram_id:
                        QMessageBox.warning(self, "Ошибка", "Telegram не привязан к аккаунту!")
                        return
                    telegram_id = user.telegram_id
                else:
                    if user:
                        QMessageBox.warning(self, "Ошибка", "Пользователь с таким номером уже существует!")
                        return
                    if not telegram_id:
                        QMessageBox.warning(self, "Ошибка", "Введите Telegram ID!")
                        return
                    if not telegram_id.isdigit():
                        QMessageBox.warning(self, "Ошибка", "Telegram ID должен содержать только цифры!")
                        return

            finally:
                session.close()

            # Генерируем код
            self.tg_code = self.generate_telegram_code()

            # Отправляем код через Telegram
            try:
                from bot import telegram_bot
                current_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

                message = (
                    f"🔐 Код подтверждения для {'регистрации в' if mode == 'register' else 'входа в'} Crypto Wallet\n\n"
                    f"📱 Телефон: {phone}\n"
                    f"🕐 Время: {current_time}\n"
                    f"📍 IP: 127.0.0.1 (локальное приложение)\n\n"
                    f"Ваш код: `{self.tg_code}`\n\n"
                    f"Код действителен 5 минут.\n"
                    f"Если это не вы, проигнорируйте это сообщение."
                )

                success = telegram_bot.send_notification(telegram_id, message)

                if success:
                    # Активируем поле ввода и запускаем таймер
                    if mode == "login":
                        self.login_code_input.setEnabled(True)
                        self.login_code_input.setFocus()
                        self.login_get_code_btn.setEnabled(False)
                        self.login_get_code_btn.setText("Код отправлен")
                    else:
                        self.register_code_input.setEnabled(True)
                        self.register_code_input.setFocus()
                        self.register_get_code_btn.setEnabled(False)
                        self.register_get_code_btn.setText("Код отправлен")

                    self.start_timer(mode)
                    QMessageBox.information(self, "Код отправлен",
                                            f"Код подтверждения отправлен в Telegram!\n"
                                            f"Проверьте свои сообщения.")
                else:
                    QMessageBox.warning(self, "Ошибка",
                                        "Не удалось отправить код. Проверьте Telegram ID.")

            except Exception as e:
                print(f"Ошибка отправки кода: {e}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка отправки кода: {str(e)}")

        except Exception as e:
            print(f"Общая ошибка: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка: {str(e)}")

    def start_timer(self, mode):
        """Запуск таймера"""
        self.stop_timer()
        self.time_left = 300  # 5 минут

        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.update_timer(mode))
        self.timer.start(1000)  # Каждую секунду
        self.update_timer(mode)  # Первое обновление

    def update_timer(self, mode):
        """Обновление таймера"""
        if self.time_left > 0:
            minutes = self.time_left // 60
            seconds = self.time_left % 60
            self.update_timer_signal.emit(f"⏳ Код действителен: {minutes:02d}:{seconds:02d}")
            self.time_left -= 1
        else:
            self.stop_timer()
            self.tg_code = None
            self.update_timer_signal.emit("❌ Срок действия кода истек")

            if mode == "login":
                self.login_code_input.setEnabled(False)
                self.login_code_input.clear()
                self.login_get_code_btn.setEnabled(True)
                self.login_get_code_btn.setText("📲 Получить код в Telegram")
            else:
                self.register_code_input.setEnabled(False)
                self.register_code_input.clear()
                self.register_get_code_btn.setEnabled(True)
                self.register_get_code_btn.setText("📲 Получить код подтверждения")

    def stop_timer(self):
        """Остановка таймера"""
        if self.timer:
            self.timer.stop()
            self.timer = None

    def quick_login(self):
        """Безопасный быстрый вход"""
        if not self.saved_phone:
            QMessageBox.warning(self, "Ошибка", "Профиль не найден!")
            return

        try:
            # Переключаемся на страницу входа
            self.switch_mode("login")

            # Заполняем поле телефона
            self.login_phone_input.setText(self.saved_phone)

            # Отправляем код
            self.get_telegram_code("login")

        except Exception as e:
            print(f"Ошибка быстрого входа: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка быстрого входа: {str(e)}")

    def remove_saved_profile(self):
        """Удаление сохраненного профиля"""
        try:
            if os.path.exists('saved_profile.txt'):
                os.remove('saved_profile.txt')
            self.quick_login_frame.setVisible(False)
            self.saved_phone = None
            self.saved_user = None
            self.stacked_widget.setCurrentWidget(self.login_page)
            QMessageBox.information(self, "Успех", "Сохраненный профиль удален!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка удаления профиля: {str(e)}")

    def perform_login(self):
        """Выполнение входа"""
        phone = self.login_phone_input.text().strip()
        code = self.login_code_input.text().strip()

        if not phone:
            QMessageBox.warning(self, "Ошибка", "Введите номер телефона!")
            return

        if not code:
            QMessageBox.warning(self, "Ошибка", "Введите код подтверждения!")
            return

        if not self.tg_code:
            QMessageBox.warning(self, "Ошибка", "Сначала получите код!")
            return

        if code != self.tg_code:
            QMessageBox.warning(self, "Ошибка", "Неверный код подтверждения!")
            return

        session = db.get_session()
        try:
            user = session.query(User).filter_by(phone=phone).first()
            if not user:
                QMessageBox.warning(self, "Ошибка", "Пользователь не найден!")
                return

            self.authenticated_user = user.id
            user.last_login = datetime.now()

            db.create_user_session(user.id, "127.0.0.1", "PyQt5 Desktop App")

            # Сохраняем профиль
            with open('saved_profile.txt', 'w', encoding='utf-8') as f:
                f.write(phone)

            session.commit()

            # Отправляем уведомление
            if user.telegram_id:
                try:
                    from bot import telegram_bot
                    telegram_bot.send_notification(
                        user.telegram_id,
                        f"✅ Успешный вход в Crypto Wallet\n"
                        f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                        f"📍 IP: 127.0.0.1\n"
                        f"🖥️ Устройство: PyQt5 Desktop App"
                    )
                except:
                    pass

            QMessageBox.information(self, "Успех",
                                    f"Добро пожаловать, {user.full_name}!\n"
                                    f"Роль: {user.get_role_display()}")

            self.stop_timer()
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при входе: {str(e)}")
        finally:
            session.close()

    def perform_register(self):
        """Выполнение регистрации"""
        phone = self.register_phone_input.text().strip()
        full_name = self.register_name_input.text().strip()
        telegram_id = self.register_telegram_input.text().strip()
        code = self.register_code_input.text().strip()

        if not all([phone, full_name, telegram_id, code]):
            QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
            return

        if not telegram_id.isdigit():
            QMessageBox.warning(self, "Ошибка", "Telegram ID должен содержать только цифры!")
            return

        if not code:
            QMessageBox.warning(self, "Ошибка", "Введите код подтверждения!")
            return

        if not self.tg_code:
            QMessageBox.warning(self, "Ошибка", "Сначала получите код!")
            return

        if code != self.tg_code:
            QMessageBox.warning(self, "Ошибка", "Неверный код подтверждения!")
            return

        try:
            user_id = execute_in_transaction(
                register_user_transaction,
                phone, full_name, telegram_id
            )

            self.authenticated_user = user_id

            if self.register_save_checkbox.isChecked():
                with open('saved_profile.txt', 'w', encoding='utf-8') as f:
                    f.write(phone)

            # Отправляем приветствие
            try:
                from bot import telegram_bot
                telegram_bot.send_notification(
                    telegram_id,
                    f"🎉 Добро пожаловать в Crypto Wallet!\n\n"
                    f"Ваш аккаунт успешно создан.\n"
                    f"👤 Имя: {full_name}\n"
                    f"📱 Телефон: {phone}\n"
                    f"👑 Роль: Пользователь\n\n"
                    f"На ваши кошельки зачислено по 10 единиц каждой валюты.\n"
                    f"Для операций требуется подтверждение через этого бота."
                )
            except:
                pass

            QMessageBox.information(self, "Успех",
                                    f"Аккаунт успешно создан!\n"
                                    f"Добро пожаловать, {full_name}!\n"
                                    f"👑 Роль: Пользователь\n"
                                    f"На ваши кошельки зачислено по 10 единиц каждой валюты.")

            self.stop_timer()
            self.accept()

        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при регистрации: {str(e)}")

    def get_authenticated_user(self):
        return self.authenticated_user

    def closeEvent(self, event):
        self.stop_timer()
        event.accept()