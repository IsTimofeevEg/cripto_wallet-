from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QListWidget, QListWidgetItem,
                             QMessageBox, QSplitter, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from database import db


class NotificationsDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.init_ui()
        self.load_notifications()

    def init_ui(self):
        self.setWindowTitle("🔔 Уведомления")
        self.setGeometry(300, 200, 700, 500)
        self.setModal(True)

        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Уведомления")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Список уведомлений и детали
        splitter = QSplitter(Qt.Horizontal)

        # Список уведомлений
        self.notifications_list = QListWidget()
        self.notifications_list.currentItemChanged.connect(self.show_notification_details)
        splitter.addWidget(self.notifications_list)

        # Детали уведомления
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)

        self.notification_title = QLabel("Выберите уведомление...")
        self.notification_title.setFont(QFont("Arial", 12, QFont.Bold))
        self.notification_title.setWordWrap(True)
        details_layout.addWidget(self.notification_title)

        self.notification_date = QLabel("")
        self.notification_date.setStyleSheet("color: #666;")
        details_layout.addWidget(self.notification_date)

        self.notification_message = QLabel("")
        self.notification_message.setWordWrap(True)
        self.notification_message.setStyleSheet("margin-top: 10px;")
        details_layout.addWidget(self.notification_message)

        details_layout.addStretch()
        splitter.addWidget(details_widget)

        splitter.setSizes([300, 400])
        layout.addWidget(splitter)

        # Кнопки
        buttons_layout = QHBoxLayout()

        mark_read_btn = QPushButton("Пометить прочитанным")
        mark_read_btn.clicked.connect(self.mark_as_read)
        buttons_layout.addWidget(mark_read_btn)

        mark_all_read_btn = QPushButton("Прочитать все")
        mark_all_read_btn.clicked.connect(self.mark_all_as_read)
        buttons_layout.addWidget(mark_all_read_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def load_notifications(self):
        """Загрузка уведомлений"""
        self.notifications_list.clear()
        notifications = db.get_user_notifications(self.user_id)

        if not notifications:
            item = QListWidgetItem("📭 Нет уведомлений")
            item.setFlags(Qt.NoItemFlags)  # Делаем недоступным для выбора
            self.notifications_list.addItem(item)
            return

        for notification in notifications:
            item = QListWidgetItem()

            # Иконка в зависимости от типа
            icon = "💸" if notification.type == 'transaction' else \
                "🔄" if notification.type == 'exchange' else \
                    "🔐" if notification.type == 'security' else "⚙️"

            # Дата и заголовок
            date_str = notification.created_date.strftime("%d.%m %H:%M")
            text = f"{icon} {date_str} - {notification.title}"

            # Выделяем непрочитанные
            if not notification.is_read:
                text = f"🔔 {text}"
                item.setBackground(QColor("#FFF0F0"))
                item.setFont(QFont("Arial", 10, QFont.Bold))
            else:
                item.setFont(QFont("Arial", 9))

            item.setText(text)
            item.setData(Qt.UserRole, notification)
            self.notifications_list.addItem(item)

        # Выбираем первый элемент
        if self.notifications_list.count() > 0:
            self.notifications_list.setCurrentRow(0)

    def show_notification_details(self, current, previous):
        """Показать детали выбранного уведомления"""
        if current and current.data(Qt.UserRole):
            notification = current.data(Qt.UserRole)
            self.notification_title.setText(notification.title)
            self.notification_date.setText(f"Дата: {notification.created_date.strftime('%d.%m.%Y %H:%M:%S')}")
            self.notification_message.setText(notification.message)

    def mark_as_read(self):
        """Пометить выбранное уведомление как прочитанное"""
        current_item = self.notifications_list.currentItem()
        if current_item and current_item.data(Qt.UserRole):
            notification = current_item.data(Qt.UserRole)
            if db.mark_notification_read(notification.id):
                self.load_notifications()
                QMessageBox.information(self, "Успех", "Уведомление помечено как прочитанное!")
        else:
            QMessageBox.warning(self, "Внимание", "Выберите уведомление!")

    def mark_all_as_read(self):
        """Пометить все уведомления как прочитанные"""
        notifications = db.get_user_notifications(self.user_id, unread_only=True)
        if not notifications:
            QMessageBox.information(self, "Информация", "Нет непрочитанных уведомлений!")
            return

        marked_count = 0
        for notification in notifications:
            if db.mark_notification_read(notification.id):
                marked_count += 1

        self.load_notifications()
        QMessageBox.information(self, "Успех", f"Помечено как прочитанные: {marked_count} уведомлений!")