from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QComboBox, QCheckBox, QColorDialog,
                             QSpinBox, QGroupBox, QFormLayout, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from database import db
from models import Theme


class SettingsDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.parent = parent
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        self.setWindowTitle("Настройки интерфейса")
        self.setGeometry(300, 300, 500, 400)
        self.setModal(True)

        layout = QVBoxLayout()

        # Настройки темы
        theme_group = QGroupBox("🎨 Настройки темы")
        theme_layout = QFormLayout(theme_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Светлая", Theme.LIGHT)
        self.theme_combo.addItem("Темная", Theme.DARK)
        self.theme_combo.addItem("Синяя", Theme.BLUE)
        self.theme_combo.addItem("Зеленая", Theme.GREEN)
        theme_layout.addRow("Тема:", self.theme_combo)

        self.auto_login_checkbox = QCheckBox("Сохранять профиль для быстрого входа")
        theme_layout.addRow(self.auto_login_checkbox)

        layout.addWidget(theme_group)

        # Настройки цветов
        colors_group = QGroupBox("🌈 Цвета интерфейса")
        colors_layout = QFormLayout(colors_group)

        # Основной цвет
        self.primary_color_btn = QPushButton("#2E8B57")
        self.primary_color_btn.setFixedSize(100, 30)
        self.primary_color_btn.clicked.connect(lambda: self.choose_color('primary'))
        colors_layout.addRow("Основной цвет:", self.primary_color_btn)

        # Цвет фона
        self.background_color_btn = QPushButton("#FFFFFF")
        self.background_color_btn.setFixedSize(100, 30)
        self.background_color_btn.clicked.connect(lambda: self.choose_color('background'))
        colors_layout.addRow("Цвет фона:", self.background_color_btn)

        # Размер шрифта
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 20)
        self.font_size_spin.setValue(12)
        colors_layout.addRow("Размер шрифта:", self.font_size_spin)

        layout.addWidget(colors_group)

        # Кнопки
        buttons_layout = QHBoxLayout()

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_settings)
        buttons_layout.addWidget(save_btn)

        reset_btn = QPushButton("Сбросить")
        reset_btn.clicked.connect(self.reset_settings)
        buttons_layout.addWidget(reset_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def load_settings(self):
        """Загрузка текущих настроек"""
        try:
            ui_settings = db.get_user_interface(self.user_id)
            if ui_settings:
                # Тема
                index = self.theme_combo.findData(ui_settings.theme)
                if index >= 0:
                    self.theme_combo.setCurrentIndex(index)

                # Чекбокс авто-входа
                self.auto_login_checkbox.setChecked(ui_settings.auto_login)

                # Цвета
                if ui_settings.primary_color:
                    self.primary_color_btn.setText(ui_settings.primary_color)
                    self.primary_color_btn.setStyleSheet(
                        f"background-color: {ui_settings.primary_color}; color: white;")
                if ui_settings.background_color:
                    self.background_color_btn.setText(ui_settings.background_color)
                    self.background_color_btn.setStyleSheet(f"background-color: {ui_settings.background_color};")

                # Размер шрифта
                self.font_size_spin.setValue(ui_settings.font_size)
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")

    def choose_color(self, color_type):
        """Выбор цвета"""
        if color_type == 'primary':
            current_color = self.primary_color_btn.text()
        else:
            current_color = self.background_color_btn.text()

        color = QColorDialog.getColor(QColor(current_color), self, f"Выберите {color_type} цвет")

        if color.isValid():
            color_hex = color.name()
            if color_type == 'primary':
                self.primary_color_btn.setText(color_hex)
                self.primary_color_btn.setStyleSheet(f"background-color: {color_hex}; color: white;")
            elif color_type == 'background':
                self.background_color_btn.setText(color_hex)
                self.background_color_btn.setStyleSheet(f"background-color: {color_hex};")

    def save_settings(self):
        """Сохранение настроек"""
        try:
            updates = {
                'theme': self.theme_combo.currentData(),
                'auto_login': self.auto_login_checkbox.isChecked(),
                'primary_color': self.primary_color_btn.text(),
                'background_color': self.background_color_btn.text(),
                'font_size': self.font_size_spin.value()
            }

            success = db.update_user_interface(self.user_id, **updates)

            if success:
                QMessageBox.information(self, "Успех",
                                        "Настройки сохранены!\n"
                                        "Изменения применены к интерфейсу.")
                self.accept()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить настройки!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения настроек: {str(e)}")

    def reset_settings(self):
        """Сброс настроек к значениям по умолчанию"""
        reply = QMessageBox.question(self, "Сброс настроек",
                                     "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            defaults = {
                'theme': Theme.LIGHT,
                'auto_login': False,
                'primary_color': '#2E8B57',
                'background_color': '#FFFFFF',
                'font_size': 12
            }

            success = db.update_user_interface(self.user_id, **defaults)
            if success:
                self.load_settings()
                QMessageBox.information(self, "Успех", "Настройки сброшены к значениям по умолчанию!")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сбросить настройки!")