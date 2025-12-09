from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import threading


class TelegramLinkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Привязка Telegram")
        self.setGeometry(300, 300, 400, 300)
        self.setModal(True)

        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("🔗 Привязка Telegram аккаунта")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Инструкция
        instruction = QLabel(
            "Для привязки Telegram аккаунта:\n\n"
            "1. Перейдите в бота: @CryptoWalletConfirmationBot\n"
            "2. Нажмите /start\n"
            "3. Нажмите /link чтобы получить код\n"
            "4. Введите полученный код ниже:"
        )
        instruction.setWordWrap(True)
        layout.addWidget(instruction)

        # Поле для ввода кода
        code_layout = QHBoxLayout()
        code_layout.addWidget(QLabel("Код из Telegram:"))

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Введите ваш Telegram ID")
        code_layout.addWidget(self.code_input)

        layout.addLayout(code_layout)

        # Кнопки
        buttons_layout = QHBoxLayout()

        link_btn = QPushButton("Привязать")
        link_btn.clicked.connect(self.link_account)
        buttons_layout.addWidget(link_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        # Информация
        info = QLabel(
            "После привязки вы будете получать уведомления "
            "и подтверждать операции через Telegram."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info)

        self.setLayout(layout)

    def link_account(self):
        """Привязка аккаунта"""
        telegram_id = self.code_input.text().strip()

        if not telegram_id:
            QMessageBox.warning(self, "Ошибка", "Введите код из Telegram!")
            return

        if not telegram_id.isdigit():
            QMessageBox.warning(self, "Ошибка", "Код должен содержать только цифры!")
            return

        # Вызываем метод родителя в основном потоке
        if self.parent and self.parent.link_telegram_account(telegram_id):
            self.accept()