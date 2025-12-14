from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                             QTabWidget, QLineEdit, QComboBox, QMessageBox,
                             QGroupBox, QFormLayout, QHeaderView, QMenuBar,
                             QMenu, QAction, QStatusBar, QDialog, QApplication)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from sqlalchemy.orm import Session, joinedload
from models import User, Wallet, Transaction, Currency, ExchangeRate, Commission, Exchange, ExchangeStatus, \
    TransactionType, Theme, UserRole
from database import db
from bot import telegram_bot
from crypto_manager import crypto_manager
from telegram_link_dialog import TelegramLinkDialog
from notifications_dialog import NotificationsDialog
from settings_dialog import SettingsDialog
from transaction_utils import transaction_session
from admin_panel import AdminPanelDialog
from moderator_panel import ModeratorPanelDialog
from permissions import *
from backup_dialog import BackupDialog
from datetime import datetime
import json
import os
import threading


class MainWindow(QMainWindow):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.session_db = db.get_session()
        self.user = self.session_db.query(User).get(user_id)
        self.init_ui()
        self.apply_styles()
        self.load_data()

        # Таймер для обновления курсов
        self.rates_timer = QTimer()
        self.rates_timer.timeout.connect(self.update_rates_display)
        self.rates_timer.start(10000)

    def init_ui(self):
        self.setWindowTitle(f"Крипто Кошелек - {self.user.full_name}")
        self.setGeometry(100, 100, 1200, 800)

        self.create_menu()
        self.statusBar().showMessage(
            f"Добро пожаловать, {self.user.full_name}! | "
            f"Telegram: {'✅ Привязан' if self.user.telegram_id else '❌ Не привязан'} | "
            f"Баланс обновляется автоматически")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        title = QLabel("💰 Крипто Кошелек - Безопасный криптовалютный кошелек")
        title.setProperty("fontSize", "large")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        tabs = QTabWidget()

        balance_tab = self.create_balance_tab()
        tabs.addTab(balance_tab, "💰 Баланс")

        transfer_tab = self.create_transfer_tab()
        tabs.addTab(transfer_tab, "📤 Перевод")

        exchange_tab = self.create_exchange_tab()
        tabs.addTab(exchange_tab, "🔄 Обмен")

        history_tab = self.create_history_tab()
        tabs.addTab(history_tab, "📊 История")

        rates_tab = self.create_rates_tab()
        tabs.addTab(rates_tab, "📈 Курсы")

        layout.addWidget(tabs)

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu('Файл')

        refresh_action = QAction('Обновить', self)
        refresh_action.triggered.connect(self.load_data)
        file_menu.addAction(refresh_action)

        exit_action = QAction('Выход', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню Вид
        view_menu = menubar.addMenu('Вид')

        notifications_action = QAction('🔔 Уведомления', self)
        notifications_action.triggered.connect(self.show_notifications_dialog)
        view_menu.addAction(notifications_action)

        settings_action = QAction('⚙️ Настройки интерфейса', self)
        settings_action.triggered.connect(self.show_settings_dialog)
        view_menu.addAction(settings_action)

        # Меню Настройки
        settings_menu = menubar.addMenu('Настройки')

        telegram_action = QAction('Привязать Telegram', self)
        telegram_action.triggered.connect(self.show_telegram_link_dialog)
        settings_menu.addAction(telegram_action)

        # Меню администрирования (только для админов и модераторов)
        if self.user.role in [UserRole.ADMIN, UserRole.MODERATOR]:
            admin_menu = menubar.addMenu('🛡️ Администрирование')

            # Для админов
            if self.user.role == UserRole.ADMIN:
                admin_panel_action = QAction('Панель администратора', self)
                admin_panel_action.triggered.connect(self.show_admin_panel)
                admin_menu.addAction(admin_panel_action)

                backup_action = QAction('💾 Управление бэкапами', self)
                backup_action.triggered.connect(self.show_backup_dialog)
                admin_menu.addAction(backup_action)

            # Для модераторов
            elif self.user.role == UserRole.MODERATOR:
                moderator_panel_action = QAction('Панель модератора', self)
                moderator_panel_action.triggered.connect(self.show_moderator_panel)
                admin_menu.addAction(moderator_panel_action)

    def show_admin_panel(self):
        """Показать панель администратора"""
        try:
            dialog = AdminPanelDialog(self.user_id, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть панель администратора: {str(e)}")

    def show_moderator_panel(self):
        """Показать панель модератора"""
        try:
            dialog = ModeratorPanelDialog(self.user_id, self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть панель модератора: {str(e)}")

    def show_system_logs(self):
        """Показать системные логи"""
        if check_permission(self.user, 'view_system_logs'):
            try:
                # Здесь можно реализовать просмотр логов
                QMessageBox.information(self, "Системные логи",
                                        "Просмотр системных логов будет реализован в следующем обновлении")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка: {str(e)}")
        else:
            QMessageBox.warning(self, "Доступ запрещен", "У вас недостаточно прав для просмотра логов")

    def show_backup_dialog(self):
        """Показать диалог управления бэкапами"""
        try:
            dialog = BackupDialog(self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть управление бэкапами: {str(e)}")

    def show_currencies_management(self):
        """Управление валютами"""
        if check_permission(self.user, 'manage_currencies'):
            try:
                # Здесь можно реализовать управление валютами
                QMessageBox.information(self, "Управление валютами",
                                        "Управление валютами будет реализовано в следующем обновлении")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка: {str(e)}")
        else:
            QMessageBox.warning(self, "Доступ запрещен", "У вас недостаточно прав для управления валютами")

    def show_notifications_dialog(self):
        """Показать диалог уведомлений"""
        try:
            dialog = NotificationsDialog(self.user_id, self)
            dialog.exec_()
        except Exception as e:
            print(f"Ошибка открытия уведомлений: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть уведомления: {str(e)}")

    def show_settings_dialog(self):
        """Показать диалог настроек"""
        try:
            from settings_dialog import SettingsDialog
            dialog = SettingsDialog(self.user_id, self)
            if dialog.exec_() == QDialog.Accepted:
                self.apply_styles()
                QMessageBox.information(self, "Успех", "Настройки применены!")
        except Exception as e:
            print(f"Ошибка открытия настроек: {e}")
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть настройки: {str(e)}")

    def apply_styles(self):
        """Применение стилей из настроек пользователя"""
        try:
            ui_settings = db.get_user_interface(self.user_id)
            if not ui_settings:
                return

            style_sheet = self.generate_style_sheet(ui_settings)
            self.setStyleSheet(style_sheet)

            font = QApplication.font()
            font.setPointSize(ui_settings.font_size)
            QApplication.setFont(font)

        except Exception as e:
            print(f"Ошибка применения стилей: {e}")

    def generate_style_sheet(self, ui_settings):
        """Генерация CSS стилей на основе темы и настроек"""
        theme = ui_settings.theme if ui_settings else Theme.LIGHT
        primary_color = ui_settings.primary_color if ui_settings else '#2E8B57'
        background_color = ui_settings.background_color if ui_settings else '#FFFFFF'
        font_size = ui_settings.font_size if ui_settings and ui_settings.font_size else 12

        themes = {
            Theme.LIGHT: {
                'primary': primary_color,
                'secondary': '#4682B4',
                'background': background_color,
                'surface': '#FFFFFF',
                'text': '#333333',
                'text_secondary': '#666666',
                'border': '#DDDDDD',
                'success': '#28a745',
                'warning': '#ffc107',
                'error': '#dc3545'
            },
            Theme.DARK: {
                'primary': primary_color,
                'secondary': '#6c757d',
                'background': '#1a1a1a',
                'surface': '#2d2d2d',
                'text': '#ffffff',
                'text_secondary': '#b0b0b0',
                'border': '#404040',
                'success': '#20c997',
                'warning': '#fd7e14',
                'error': '#e83e8c'
            },
            Theme.BLUE: {
                'primary': '#2196F3',
                'secondary': '#03A9F4',
                'background': '#E3F2FD',
                'surface': '#FFFFFF',
                'text': '#1565C0',
                'text_secondary': '#1976D2',
                'border': '#BBDEFB',
                'success': '#4CAF50',
                'warning': '#FF9800',
                'error': '#F44336'
            },
            Theme.GREEN: {
                'primary': '#4CAF50',
                'secondary': '#8BC34A',
                'background': '#F1F8E9',
                'surface': '#FFFFFF',
                'text': '#2E7D32',
                'text_secondary': '#388E3C',
                'border': '#C5E1A5',
                'success': '#66BB6A',
                'warning': '#FFA726',
                'error': '#EF5350'
            },
            Theme.PURPLE: {
                'primary': '#9C27B0',
                'secondary': '#BA68C8',
                'background': '#F3E5F5',
                'surface': '#FFFFFF',
                'text': '#7B1FA2',
                'text_secondary': '#8E24AA',
                'border': '#E1BEE7',
                'success': '#7CB342',
                'warning': '#FFB300',
                'error': '#E53935'
            },
            Theme.ORANGE: {
                'primary': '#FF9800',
                'secondary': '#FFB74D',
                'background': '#FFF3E0',
                'surface': '#FFFFFF',
                'text': '#EF6C00',
                'text_secondary': '#F57C00',
                'border': '#FFCC80',
                'success': '#43A047',
                'warning': '#FF8F00',
                'error': '#E53935'
            },
            Theme.MODERN: {
                'primary': '#6366F1',
                'secondary': '#8B5CF6',
                'background': '#0F172A',
                'surface': '#1E293B',
                'text': '#F1F5F9',
                'text_secondary': '#94A3B8',
                'border': '#334155',
                'success': '#10B981',
                'warning': '#F59E0B',
                'error': '#EF4444'
            }
        }

        colors = themes.get(theme, themes[Theme.LIGHT])

        if ui_settings and ui_settings.primary_color:
            colors['primary'] = ui_settings.primary_color
        if ui_settings and ui_settings.background_color:
            colors['background'] = ui_settings.background_color

        style = f"""
            /* Основные стили */
            QMainWindow, QWidget, QDialog {{
                background-color: {colors['background']};
                color: {colors['text']};
                font-size: {font_size}px;
                font-family: "Arial", sans-serif;
            }}

            /* ЗАГОЛОВКИ */
            QLabel[fontSize="large"] {{
                font-size: {font_size + 4}px;
                font-weight: bold;
            }}

            QLabel[fontSize="medium"] {{
                font-size: {font_size + 2}px;
            }}

            QLabel[fontSize="small"] {{
                font-size: {font_size}px;
                color: {colors['text_secondary']};
            }}

            /* КНОПКИ */
            QPushButton {{
                background-color: {colors['primary']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-size: {font_size}px;
                min-height: 10px;
            }}

            QPushButton:hover {{
                background-color: {self.adjust_color(colors['primary'], 15)};
            }}

            QPushButton:pressed {{
                background-color: {self.adjust_color(colors['primary'], -10)};
            }}

            /* Кнопка перевода (зеленая) */
            QPushButton[objectName="transfer_btn"] {{
                background-color: {colors['success']};
                font-size: {font_size}px;
                padding: 10px 20px;
            }}

            QPushButton[objectName="transfer_btn"]:hover {{
                background-color: {self.adjust_color(colors['success'], 15)};
            }}

            /* Кнопка обмена (оранжевая) */
            QPushButton[objectName="exchange_btn"] {{
                background-color: {colors['warning']};
                font-size: {font_size}px;
                padding: 10px 20px;
            }}

            QPushButton[objectName="exchange_btn"]:hover {{
                background-color: {self.adjust_color(colors['warning'], 15)};
            }}

            /* Кнопка экспорта в PDF (фиолетовая) */
            QPushButton[objectName="export_btn"] {{
                background-color: #9C27B0;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
                min-width: 120px;
                font-size: {font_size}px;
            }}
            QPushButton[objectName="export_btn"]:hover {{
                background-color: #BA68C8;
            }}
            QPushButton[objectName="export_btn"]:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}

            /* Вторичные кнопки */
            QPushButton[objectName="secondary_btn"] {{
                background-color: {colors['secondary']};
                padding: 6px 12px;
            }}

            /* ТАБЫ */
            QTabWidget::pane {{
                border: 1px solid {colors['border']};
                background-color: {colors['surface']};
                border-radius: 6px;
                margin-top: 5px;
            }}

            QTabBar::tab {{
                background-color: {colors['surface']};
                color: {colors['text_secondary']};
                padding: 8px 16px;
                border: 1px solid {colors['border']};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-weight: bold;
                font-size: {font_size}px;
                min-width: 100px;
            }}

            QTabBar::tab:selected {{
                background-color: {colors['primary']};
                color: white;
                border-color: {colors['primary']};
            }}

            QTabBar::tab:hover:!selected {{
                background-color: {self.adjust_color(colors['primary'], 40)};
                color: white;
            }}

            /* ГРУППЫ */
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {colors['primary']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 12px;
                background-color: {colors['surface']};
                color: {colors['text']};
                font-size: {font_size}px;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                color: {colors['primary']};
                background-color: {colors['surface']};
                font-size: {font_size}px;
            }}

            /* ПОЛЯ ВВОДА */
            QLineEdit, QComboBox, QSpinBox {{
                padding: 6px 10px;
                border: 1px solid {colors['border']};
                border-radius: 4px;
                background-color: {colors['surface']};
                color: {colors['text']};
                font-size: {font_size}px;
                selection-background-color: {colors['primary']};
                min-height: 20px;
            }}

            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border-color: {colors['primary']};
                background-color: {self.adjust_color(colors['surface'], 5)};
            }}

            QComboBox::drop-down {{
                border: none;
                background-color: {colors['primary']};
                width: 20px;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}

            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid white;
                width: 0px;
                height: 0px;
            }}

            /* ТАБЛИЦЫ */
            QTableWidget {{
                gridline-color: {colors['border']};
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                font-size: {font_size}px;
                alternate-background-color: {self.adjust_color(colors['surface'], 5)};
            }}

            QTableWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {colors['border']};
            }}

            QTableWidget::item:selected {{
                background-color: {colors['primary']};
                color: white;
            }}

            QHeaderView::section {{
                background-color: {colors['primary']};
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
                font-size: {font_size}px;
            }}

            /* МЕНЮ */
            QMenuBar {{
                background-color: {colors['primary']};
                color: white;
                border: none;
                font-weight: bold;
                font-size: {font_size}px;
                padding: 4px;
            }}

            QMenuBar::item {{
                background-color: transparent;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                margin: 0 2px;
            }}

            QMenuBar::item:selected {{
                background-color: {self.adjust_color(colors['primary'], 20)};
            }}

            QMenu {{
                background-color: {colors['surface']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 6px;
            }}

            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
                font-size: {font_size}px;
            }}

            QMenu::item:selected {{
                background-color: {colors['primary']};
                color: white;
            }}

            /* СТАТУС БАР */
            QStatusBar {{
                background-color: {colors['surface']};
                color: {colors['text_secondary']};
                border-top: 1px solid {colors['border']};
                font-size: {font_size - 1}px;
                padding: 4px;
            }}

            /* CHECKBOX */
            QCheckBox {{
                font-size: {font_size}px;
                color: {colors['text']};
                spacing: 6px;
            }}

            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 1px solid {colors['border']};
                border-radius: 3px;
                background-color: {colors['surface']};
            }}

            QCheckBox::indicator:checked {{
                background-color: {colors['primary']};
                border: 1px solid {colors['primary']};
            }}

            /* SCROLLBAR */
            QScrollBar:vertical {{
                background-color: {colors['surface']};
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical {{
                background-color: {colors['primary']};
                border-radius: 6px;
                min-height: 20px;
            }}

            QScrollBar::handle:vertical:hover {{
                background-color: {self.adjust_color(colors['primary'], 15)};
            }}
        """

        return style

    def adjust_color(self, color, amount):
        """Осветлить или затемнить цвет"""
        if color.startswith('#'):
            color = color[1:]

        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)

        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))

        return f"#{r:02x}{g:02x}{b:02x}"

    def create_balance_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        total_balance_group = QGroupBox("Общий баланс (в USDT)")
        total_layout = QVBoxLayout(total_balance_group)
        self.total_balance_label = QLabel("Загрузка...")
        self.total_balance_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.total_balance_label.setStyleSheet("color: #2E8B57;")
        total_layout.addWidget(self.total_balance_label)
        layout.addWidget(total_balance_group)

        wallets_group = QGroupBox("Мои кошельки")
        wallets_layout = QVBoxLayout(wallets_group)

        self.wallets_table = QTableWidget()
        self.wallets_table.setColumnCount(5)
        self.wallets_table.setHorizontalHeaderLabels(["Валюта", "Баланс", "В USDT", "Адрес", "Курс USDT"])
        self.wallets_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        wallets_layout.addWidget(self.wallets_table)

        layout.addWidget(wallets_group)

        return widget

    def create_exchange_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        exchange_form = QGroupBox("🔄 Создать обмен P2P")
        form_layout = QFormLayout(exchange_form)

        self.exchange_from_currency = QComboBox()
        self.exchange_from_currency.currentIndexChanged.connect(self.on_from_currency_changed)
        form_layout.addRow("Отдаю валюту:", self.exchange_from_currency)

        self.exchange_from_amount = QLineEdit()
        self.exchange_from_amount.setPlaceholderText("0.00")
        self.exchange_from_amount.textChanged.connect(self.calculate_exchange)
        form_layout.addRow("Сумма отдачи:", self.exchange_from_amount)

        self.exchange_to_currency = QComboBox()
        self.exchange_to_currency.currentIndexChanged.connect(self.on_to_currency_changed)
        form_layout.addRow("Получаю валюту:", self.exchange_to_currency)

        self.exchange_to_amount = QLineEdit()
        self.exchange_to_amount.setPlaceholderText("0.00")
        self.exchange_to_amount.textChanged.connect(self.calculate_exchange_reverse)
        form_layout.addRow("Сумма получения:", self.exchange_to_amount)

        self.exchange_recipient = QLineEdit()
        self.exchange_recipient.setPlaceholderText("Телефон или ID пользователя")
        form_layout.addRow("С кем обмен:", self.exchange_recipient)

        self.exchange_rate_label = QLabel("Курс: -")
        form_layout.addRow("Курс обмена:", self.exchange_rate_label)

        layout.addWidget(exchange_form)

        exchange_btn = QPushButton("🔄 Создать обмен")
        exchange_btn.setObjectName("exchange_btn")
        exchange_btn.clicked.connect(self.create_exchange)
        layout.addWidget(exchange_btn)

        self.exchange_info = QLabel("")
        layout.addWidget(self.exchange_info)

        active_exchanges_group = QGroupBox("📋 Активные обмены")
        active_layout = QVBoxLayout(active_exchanges_group)

        self.exchanges_table = QTableWidget()
        self.exchanges_table.setColumnCount(6)
        self.exchanges_table.setHorizontalHeaderLabels([
            "Дата", "Тип", "С кем", "Отдаю", "Получаю", "Статус"
        ])
        self.exchanges_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        active_layout.addWidget(self.exchanges_table)

        layout.addWidget(active_exchanges_group)

        return widget

    def create_rates_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        rates_group = QGroupBox("📊 Актуальные курсы криптовалют")
        rates_layout = QVBoxLayout(rates_group)

        self.rates_table = QTableWidget()
        self.rates_table.setColumnCount(4)
        self.rates_table.setHorizontalHeaderLabels(["Валюта", "Код", "Курс к USDT", "Изменение"])
        self.rates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        rates_layout.addWidget(self.rates_table)

        layout.addWidget(rates_group)

        info_label = QLabel("💡 Курсы обновляются автоматически каждые 10 секунд")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)

        return widget

    def create_transfer_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        form_layout = QFormLayout()

        self.currency_combo = QComboBox()
        form_layout.addRow("Валюта:", self.currency_combo)

        self.recipient_input = QLineEdit()
        self.recipient_input.setPlaceholderText("Телефон или ID пользователя")
        form_layout.addRow("Получатель:", self.recipient_input)

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("0.00")
        self.amount_input.textChanged.connect(self.calculate_fee)
        form_layout.addRow("Сумма:", self.amount_input)

        self.fee_label = QLabel("0.00")
        form_layout.addRow("Комиссия (1%):", self.fee_label)

        self.total_label = QLabel("0.00")
        form_layout.addRow("Итого к списанию:", self.total_label)

        self.receives_label = QLabel("0.00")
        form_layout.addRow("Получает:", self.receives_label)

        layout.addLayout(form_layout)

        transfer_btn = QPushButton("📤 Перевести")
        transfer_btn.setObjectName("transfer_btn")
        transfer_btn.clicked.connect(self.make_transfer)
        layout.addWidget(transfer_btn)

        self.transfer_info = QLabel("")
        layout.addWidget(self.transfer_info)

        return widget

    def create_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Панель управления экспортом
        export_panel = QHBoxLayout()

        # Выбор периода
        export_panel.addWidget(QLabel("Период:"))
        self.export_period_combo = QComboBox()
        self.export_period_combo.addItem("📅 За неделю", 7)
        self.export_period_combo.addItem("📅 За месяц", 30)
        self.export_period_combo.addItem("📅 За 3 месяца", 90)
        self.export_period_combo.addItem("📅 За все время", 3650)  # 10 лет
        export_panel.addWidget(self.export_period_combo)

        # Кнопка экспорта
        self.export_btn = QPushButton("📊 Экспорт в PDF")
        self.export_btn.setObjectName("export_btn")
        self.export_btn.clicked.connect(self.export_transaction_history)
        export_panel.addWidget(self.export_btn)

        export_panel.addStretch()
        layout.addLayout(export_panel)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Дата", "Тип", "От кого", "Кому", "Валюта", "Сумма", "Статус"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.history_table)

        return widget

    def load_data(self):
        """Загрузка всех данных"""
        try:
            self.load_wallets()
            self.load_history()
            self.load_exchange_rates()
            self.load_exchanges()

            # Обновляем состояние кнопки экспорта
            if hasattr(self, 'export_btn'):
                self.export_btn.setEnabled(bool(self.user.telegram_id))

        except Exception as e:
            print(f"Error loading data: {e}")
            QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки данных: {str(e)}")

    def load_wallets(self):
        """Загрузка кошельков пользователя"""
        wallets = self.session_db.query(Wallet).filter_by(user_id=self.user_id).all()
        self.wallets_table.setRowCount(len(wallets))

        total_balance_usdt = 0

        for row, wallet in enumerate(wallets):
            self.wallets_table.setItem(row, 0, QTableWidgetItem(f"{wallet.currency.name} ({wallet.currency.code})"))
            self.wallets_table.setItem(row, 1, QTableWidgetItem(f"{wallet.balance:.8f}"))

            usdt_value = crypto_manager.convert_to_usdt(wallet.currency.code, wallet.balance)
            total_balance_usdt += usdt_value
            self.wallets_table.setItem(row, 2, QTableWidgetItem(f"{usdt_value:.2f} USDT"))

            self.wallets_table.setItem(row, 3, QTableWidgetItem(wallet.address))

            rate = crypto_manager.get_exchange_rate(wallet.currency.code)
            self.wallets_table.setItem(row, 4, QTableWidgetItem(f"1 {wallet.currency.code} = {rate:.2f} USDT"))

        self.total_balance_label.setText(f"{total_balance_usdt:.2f} USDT")

        self.load_transfer_currencies(wallets)
        self.load_exchange_currencies(wallets)

    def load_transfer_currencies(self, wallets):
        current_wallet_id = self.currency_combo.currentData() if self.currency_combo.currentIndex() >= 0 else None

        self.currency_combo.clear()

        for wallet in wallets:
            self.currency_combo.addItem(f"{wallet.currency.code} ({wallet.balance:.6f})", wallet.id)

        if current_wallet_id:
            index = self.currency_combo.findData(current_wallet_id)
            if index >= 0:
                self.currency_combo.setCurrentIndex(index)

        if self.currency_combo.currentIndex() == -1 and len(wallets) > 0:
            self.currency_combo.setCurrentIndex(0)

    def load_exchange_currencies(self, wallets):
        current_from = self.exchange_from_currency.currentData() if self.exchange_from_currency.currentIndex() >= 0 else None
        current_to = self.exchange_to_currency.currentData() if self.exchange_to_currency.currentIndex() >= 0 else None

        self.exchange_from_currency.clear()
        self.exchange_to_currency.clear()

        for wallet in wallets:
            self.exchange_from_currency.addItem(f"{wallet.currency.code} ({wallet.balance:.6f})", wallet.currency.code)
            self.exchange_to_currency.addItem(f"{wallet.currency.code} ({wallet.balance:.6f})", wallet.currency.code)

        if current_from:
            index = self.exchange_from_currency.findData(current_from)
            if index >= 0:
                self.exchange_from_currency.setCurrentIndex(index)

        if current_to:
            index = self.exchange_to_currency.findData(current_to)
            if index >= 0:
                self.exchange_to_currency.setCurrentIndex(index)

        if self.exchange_from_currency.currentIndex() == -1 and self.exchange_to_currency.currentIndex() == -1:
            if len(wallets) >= 2:
                self.exchange_from_currency.setCurrentIndex(0)
                self.exchange_to_currency.setCurrentIndex(1)

    def on_from_currency_changed(self):
        from_currency = self.exchange_from_currency.currentData()
        to_currency = self.exchange_to_currency.currentData()

        if from_currency and to_currency and from_currency == to_currency:
            for i in range(self.exchange_to_currency.count()):
                candidate = self.exchange_to_currency.itemData(i)
                if candidate != from_currency:
                    self.exchange_to_currency.setCurrentIndex(i)
                    break

        self.calculate_exchange()

    def on_to_currency_changed(self):
        from_currency = self.exchange_from_currency.currentData()
        to_currency = self.exchange_to_currency.currentData()

        if from_currency and to_currency and from_currency == to_currency:
            for i in range(self.exchange_from_currency.count()):
                candidate = self.exchange_from_currency.itemData(i)
                if candidate != to_currency:
                    self.exchange_from_currency.setCurrentIndex(i)
                    break

        self.calculate_exchange()

    def load_exchanges(self):
        exchanges = (self.session_db.query(Exchange)
                     .filter((Exchange.user_id_from == self.user_id) |
                             (Exchange.user_id_to == self.user_id))
                     .order_by(Exchange.created_date.desc())
                     .limit(20).all())

        self.exchanges_table.setRowCount(len(exchanges))

        for row, exchange in enumerate(exchanges):
            self.exchanges_table.setItem(row, 0, QTableWidgetItem(
                exchange.created_date.strftime("%d.%m.%Y %H:%M")))

            if exchange.user_id_from == self.user_id:
                type_text = "📤 Исходящий"
            else:
                type_text = "📥 Входящий"
            self.exchanges_table.setItem(row, 1, QTableWidgetItem(type_text))

            if exchange.user_id_from == self.user_id:
                partner = exchange.user_to.full_name
            else:
                partner = exchange.user_from.full_name
            self.exchanges_table.setItem(row, 2, QTableWidgetItem(partner))

            if exchange.user_id_from == self.user_id:
                give_text = f"{exchange.amount_from} {exchange.currency_from.code}"
            else:
                give_text = f"{exchange.amount_to} {exchange.currency_to.code}"
            self.exchanges_table.setItem(row, 3, QTableWidgetItem(give_text))

            if exchange.user_id_from == self.user_id:
                receive_text = f"{exchange.amount_to} {exchange.currency_to.code}"
            else:
                receive_text = f"{exchange.amount_from} {exchange.currency_from.code}"
            self.exchanges_table.setItem(row, 4, QTableWidgetItem(receive_text))

            status_item = QTableWidgetItem(exchange.status.value)
            if exchange.status == ExchangeStatus.COMPLETED:
                status_item.setForeground(QColor("#2E8B57"))
            elif exchange.status == ExchangeStatus.PENDING:
                status_item.setForeground(QColor("#FF8C00"))
            else:
                status_item.setForeground(QColor("#DC143C"))
            self.exchanges_table.setItem(row, 5, status_item)

    def load_exchange_rates(self):
        rates = crypto_manager.get_all_rates()
        self.rates_table.setRowCount(len(rates))

        for row, (currency_code, rate) in enumerate(rates.items()):
            currency_name = self.get_currency_name(currency_code)
            self.rates_table.setItem(row, 0, QTableWidgetItem(currency_name))

            self.rates_table.setItem(row, 1, QTableWidgetItem(currency_code))

            self.rates_table.setItem(row, 2, QTableWidgetItem(f"{rate:.2f} USDT"))

            base_rate = crypto_manager.base_rates.get(currency_code, rate)
            change_percent = ((rate - base_rate) / base_rate) * 100
            change_text = f"{change_percent:+.2f}%"
            change_item = QTableWidgetItem(change_text)

            if change_percent > 0:
                change_item.setForeground(QColor("#2E8B57"))
            elif change_percent < 0:
                change_item.setForeground(QColor("#DC143C"))
            else:
                change_item.setForeground(QColor("#666666"))

            self.rates_table.setItem(row, 3, change_item)

    def get_currency_name(self, code):
        names = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum',
            'TON': 'Toncoin',
            'USDT': 'Tether',
            'BNB': 'Binance Coin',
            'SOL': 'Solana',
            'XRP': 'Ripple',
            'ADA': 'Cardano',
            'DOGE': 'Dogecoin',
            'DOT': 'Polkadot'
        }
        return names.get(code, code)

    def load_history(self):
        try:
            transactions = (self.session_db.query(Transaction)
                            .filter((Transaction.user_id_from == self.user_id) |
                                    (Transaction.user_id_to == self.user_id))
                            .order_by(Transaction.created_date.desc())
                            .limit(50).all())

            self.history_table.setRowCount(len(transactions))

            for row, transaction in enumerate(transactions):
                self.history_table.setItem(row, 0, QTableWidgetItem(
                    transaction.created_date.strftime("%d.%m.%Y %H:%M")))

                type_text = "📤 Отправка" if transaction.user_id_from == self.user_id else "📥 Получение"
                self.history_table.setItem(row, 1, QTableWidgetItem(type_text))

                self.history_table.setItem(row, 2, QTableWidgetItem(
                    transaction.user_from.full_name if transaction.user_from else "System"))

                self.history_table.setItem(row, 3, QTableWidgetItem(
                    transaction.user_to.full_name if transaction.user_to else "System"))

                currency_code = transaction.currency_rel.code if transaction.currency_rel else "N/A"
                self.history_table.setItem(row, 4, QTableWidgetItem(currency_code))

                amount_item = QTableWidgetItem(f"{transaction.amount:.8f}")
                if transaction.user_id_from == self.user_id:
                    amount_item.setForeground(QColor("#DC143C"))
                else:
                    amount_item.setForeground(QColor("#2E8B57"))
                self.history_table.setItem(row, 5, amount_item)

                status_item = QTableWidgetItem(transaction.status)
                if transaction.status == 'completed':
                    status_item.setForeground(QColor("#2E8B57"))
                elif transaction.status == 'pending':
                    status_item.setForeground(QColor("#FF8C00"))
                else:
                    status_item.setForeground(QColor("#DC143C"))
                self.history_table.setItem(row, 6, status_item)
        except Exception as e:
            print(f"Error loading history: {e}")
            self.history_table.setRowCount(0)

    def calculate_fee(self):
        try:
            amount = float(self.amount_input.text() or 0)
            fee = amount * 0.01
            total = amount + fee
            receives = amount

            self.fee_label.setText(f"{fee:.8f}")
            self.total_label.setText(f"{total:.8f}")
            self.receives_label.setText(f"{receives:.8f}")
        except ValueError:
            self.fee_label.setText("0.00")
            self.total_label.setText("0.00")
            self.receives_label.setText("0.00")

    def calculate_exchange(self):
        try:
            from_currency = self.exchange_from_currency.currentData()
            to_currency = self.exchange_to_currency.currentData()
            amount = float(self.exchange_from_amount.text() or 0)

            if from_currency and to_currency and amount > 0:
                result_amount = crypto_manager.calculate_exchange_rate(from_currency, to_currency, amount)
                self.exchange_to_amount.setText(f"{result_amount:.8f}")

                rate = result_amount / amount
                self.exchange_rate_label.setText(f"Курс: 1 {from_currency} = {rate:.6f} {to_currency}")
            else:
                self.exchange_rate_label.setText("Курс: -")

        except ValueError:
            self.exchange_rate_label.setText("Курс: -")

    def calculate_exchange_reverse(self):
        try:
            from_currency = self.exchange_from_currency.currentData()
            to_currency = self.exchange_to_currency.currentData()
            amount = float(self.exchange_to_amount.text() or 0)

            if from_currency and to_currency and amount > 0:
                result_amount = crypto_manager.calculate_exchange_rate(to_currency, from_currency, amount)
                self.exchange_from_amount.setText(f"{result_amount:.8f}")

                rate = amount / result_amount
                self.exchange_rate_label.setText(f"Курс: 1 {from_currency} = {rate:.6f} {to_currency}")
            else:
                self.exchange_rate_label.setText("Курс: -")

        except ValueError:
            self.exchange_rate_label.setText("Курс: -")

    def update_rates_display(self):
        crypto_manager.update_exchange_rates()
        self.load_exchange_rates()
        self.load_wallets()
        self.calculate_exchange()

    def make_transfer(self):
        """Выполнение перевода - ТОЛЬКО СОЗДАНИЕ, БЕЗ СПИСАНИЯ"""
        try:
            if self.currency_combo.currentIndex() == -1:
                QMessageBox.warning(self, "Ошибка", "Выберите валюту для перевода!")
                return

            wallet_id = self.currency_combo.currentData()
            recipient_id = self.recipient_input.text()

            try:
                amount = float(self.amount_input.text())
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Введите корректную сумму!")
                return

            if not all([wallet_id, recipient_id, amount > 0]):
                QMessageBox.warning(self, "Ошибка", "Заполните все поля корректно!")
                return

            transaction_id = None

            # Используем транзакцию для создания перевода
            with transaction_session() as session:
                wallet = session.query(Wallet).get(wallet_id)
                total_amount = amount * 1.01

                if wallet.balance < total_amount:
                    raise ValueError(f"Недостаточно средств! Доступно: {wallet.balance:.8f}")

                # Поиск получателя
                recipient = (session.query(User)
                             .filter((User.phone == recipient_id) | (User.id == recipient_id))
                             .first())

                if not recipient:
                    raise ValueError("Получатель не найден!")

                if recipient.id == self.user_id:
                    raise ValueError("Нельзя переводить самому себе!")

                # Поиск кошелька получателя
                recipient_wallet = (session.query(Wallet)
                                    .filter_by(user_id=recipient.id, currency_id=wallet.currency_id)
                                    .first())

                if not recipient_wallet:
                    raise ValueError("У получателя нет кошелька для этой валюты!")

                # Создаем транзакцию PENDING
                transaction = Transaction(
                    type=TransactionType.TRANSFER,
                    user_id_from=self.user_id,
                    user_id_to=recipient.id,
                    amount=amount,
                    currency_id=wallet.currency_id,
                    status='pending'
                )
                session.add(transaction)
                session.flush()

                # Сохраняем ID транзакции
                transaction_id = transaction.id

            # Отправляем запрос на подтверждение в Telegram (в отдельном потоке)
            if self.user.telegram_id and transaction_id:
                def send_confirmation():
                    try:
                        from bot import telegram_bot
                        success = telegram_bot.send_confirmation_request(
                            self.user.telegram_id,
                            transaction_id
                        )

                        # Обновляем UI из основного потока
                        if success:
                            self.transfer_info.setText("✅ Запрос на подтверждение отправлен в Telegram!")
                            self.transfer_info.setStyleSheet("color: #2E8B57;")
                    except Exception as e:
                        print(f"Ошибка отправки подтверждения: {e}")

                threading.Thread(target=send_confirmation, daemon=True).start()
            else:
                raise ValueError("Telegram не привязан. Привяжите Telegram для подтверждения операций.")

            # Очистка полей
            self.recipient_input.clear()
            self.amount_input.clear()
            self.load_data()

            QMessageBox.information(self, "Ожидание подтверждения",
                                    "Запрос отправлен в Telegram. Средства будут переведены после подтверждения.")

        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при переводе: {str(e)}")

    def create_exchange(self):
        """Создание P2P обмена с использованием транзакции"""
        try:
            from_currency = self.exchange_from_currency.currentData()
            to_currency = self.exchange_to_currency.currentData()
            recipient_id = self.exchange_recipient.text()

            try:
                amount_from = float(self.exchange_from_amount.text())
                amount_to = float(self.exchange_to_amount.text())
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Введите корректные суммы!")
                return

            if not all([from_currency, to_currency, recipient_id, amount_from > 0, amount_to > 0]):
                QMessageBox.warning(self, "Ошибка", "Заполните все поля корректно!")
                return

            if from_currency == to_currency:
                QMessageBox.warning(self, "Ошибка", "Выберите разные валюты для обмена!")
                return

            exchange_id = None
            recipient_telegram_id = None

            # Используем транзакцию для создания обмена
            with transaction_session() as session:
                # Поиск получателя
                recipient = (session.query(User)
                             .filter((User.phone == recipient_id) | (User.id == recipient_id))
                             .first())

                if not recipient:
                    raise ValueError("Пользователь не найден!")

                if recipient.id == self.user_id:
                    raise ValueError("Нельзя обмениваться с самим собой!")

                # Сохраняем Telegram ID получателя ДО завершения транзакции
                recipient_telegram_id = recipient.telegram_id

                # Проверяем балансы
                from_wallet = (session.query(Wallet)
                               .filter_by(user_id=self.user_id)
                               .join(Currency)
                               .filter(Currency.code == from_currency)
                               .first())

                to_wallet = (session.query(Wallet)
                             .filter_by(user_id=recipient.id)
                             .join(Currency)
                             .filter(Currency.code == to_currency)
                             .first())

                if not from_wallet or from_wallet.balance < amount_from:
                    raise ValueError(f"Недостаточно {from_currency} для обмена!")

                if not to_wallet or to_wallet.balance < amount_to:
                    raise ValueError(f"У получателя недостаточно {to_currency} для обмена!")

                # Получаем объекты валют
                currency_from = session.query(Currency).filter_by(code=from_currency).first()
                currency_to = session.query(Currency).filter_by(code=to_currency).first()

                # Создаем обмен
                exchange = Exchange(
                    user_id_from=self.user_id,
                    user_id_to=recipient.id,
                    currency_from_id=currency_from.id,
                    currency_to_id=currency_to.id,
                    amount_from=amount_from,
                    amount_to=amount_to,
                    status=ExchangeStatus.PENDING
                )
                session.add(exchange)
                session.flush()

                # Сохраняем ID обмена
                exchange_id = exchange.id

            # Отправляем запрос на подтверждение в Telegram
            if recipient_telegram_id and exchange_id:
                def send_exchange_request():
                    try:
                        from bot import telegram_bot
                        success = telegram_bot.send_exchange_request(
                            recipient_telegram_id,
                            exchange_id
                        )

                        # Обновляем UI из основного потока
                        if success:
                            self.exchange_info.setText("✅ Запрос на обмен отправлен пользователю!")
                            self.exchange_info.setStyleSheet("color: #2E8B57;")
                    except Exception as e:
                        print(f"Ошибка отправки запроса обмена: {e}")

                threading.Thread(target=send_exchange_request, daemon=True).start()

                QMessageBox.information(self, "Ожидание подтверждения",
                                        "Запрос на обмен отправлен. Обмен будет выполнен после подтверждения получателем.")
            else:
                if not recipient_telegram_id:
                    raise ValueError("У получателя не привязан Telegram")
                else:
                    raise ValueError("Не удалось создать обмен")

            # Очистка полей
            self.exchange_from_amount.clear()
            self.exchange_to_amount.clear()
            self.exchange_recipient.clear()

            # Обновляем данные
            self.load_exchanges()

        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при создании обмена: {str(e)}")

    def link_telegram_account(self, telegram_id):
        """Привязка Telegram аккаунта"""
        if telegram_bot.link_telegram_account(self.user_id, telegram_id):
            self.session_db.refresh(self.user)
            self.statusBar().showMessage(f"Добро пожаловать, {self.user.full_name}! Телеgram: ✅")
            QMessageBox.information(self, "Успех", "Telegram аккаунт успешно привязан!")
            return True
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось привязать Telegram аккаунт")
            return False

    def show_telegram_link_dialog(self):
        dialog = TelegramLinkDialog(self)
        dialog.exec_()

    def export_transaction_history(self):
        """Упрощенный экспорт истории транзакций"""
        try:
            # Проверка Telegram
            if not self.user.telegram_id:
                QMessageBox.warning(self, "Ошибка",
                                    "Telegram не привязан!\n"
                                    "Привяжите Telegram в настройках.")
                return

            # Получаем период
            period_days = self.export_period_combo.currentData()
            period_text = self.export_period_combo.currentText()

            from datetime import datetime, timedelta
            from sqlalchemy import and_

            # Получаем транзакции
            session = self.session_db
            date_from = datetime.now() - timedelta(days=period_days)

            transactions = (session.query(Transaction)
                            .options(
                joinedload(Transaction.user_from),
                joinedload(Transaction.user_to),
                joinedload(Transaction.currency_rel)
            )
                            .filter(
                and_(
                    (Transaction.user_id_from == self.user_id) |
                    (Transaction.user_id_to == self.user_id),
                    Transaction.created_date >= date_from
                )
            )
                            .order_by(Transaction.created_date.desc())
                            .all())

            if not transactions:
                QMessageBox.information(self, "Информация",
                                        f"Нет транзакций за {period_text.lower()}.")
                return

            # Показываем что начинаем обработку
            QMessageBox.information(self, "📤 Экспорт",
                                    f"Начинаю экспорт истории...\n"
                                    f"Период: {period_text}\n"
                                    f"Транзакций: {len(transactions)}")

            # Подготавливаем данные
            transactions_data = []
            for t in transactions:
                if t.user_id_from == self.user_id:
                    trans_type = "Отправка"
                    counterparty = t.user_to.full_name if t.user_to else "Система"
                else:
                    trans_type = "Получение"
                    counterparty = t.user_from.full_name if t.user_from else "Система"

                status_map = {
                    'completed': '✅ Выполнено',
                    'pending': '⏳ Ожидание',
                    'cancelled': '❌ Отменено',
                    'failed': '❌ Ошибка'
                }
                status = status_map.get(t.status, t.status)

                transactions_data.append({
                    'date': t.created_date.strftime("%d.%m.%Y %H:%M"),
                    'type': trans_type,
                    'currency': t.currency_rel.code if t.currency_rel else "N/A",
                    'amount': t.amount,
                    'counterparty': counterparty,
                    'status': status
                })

            user_info = {
                'id': self.user.id,
                'name': self.user.full_name,
                'phone': self.user.phone,
                'role': self.user.get_role_display()
            }

            period_info = f"{period_text} (с {date_from.strftime('%d.%m.%Y')})"

            # Пробуем создать PDF
            try:
                from pdf_generation import PDFGenerator
                pdf_file = PDFGenerator.generate_transaction_history(
                    transactions_data, user_info, period_info
                )

                if not pdf_file or not os.path.exists(pdf_file):
                    QMessageBox.critical(self, "Ошибка", "Не удалось создать PDF файл")
                    return

                # Отправляем через Telegram
                from bot import telegram_bot

                caption = (f"📊 История транзакций\n\n"
                           f"👤 {self.user.full_name}\n"
                           f"📱 {self.user.phone}\n"
                           f"{period_text}\n"
                           f"📈 {len(transactions)} транзакций\n"
                           f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}")

                # Отправляем с обработкой исключений
                try:
                    success = telegram_bot.send_pdf_document(
                        self.user.telegram_id,
                        pdf_file,
                        caption
                    )

                    if success:
                        # Успех - показываем сообщение
                        QMessageBox.information(self, "✅ Успешно",
                                                f"Файл отправлен в Telegram!\n\n"
                                                f"Период: {period_text}\n"
                                                f"Транзакций: {len(transactions)}\n\n"
                                                f"Проверьте чат с ботом.")
                    else:
                        QMessageBox.warning(self, "❌ Ошибка",
                                            "Не удалось отправить файл.\n"
                                            "Возможные причины:\n"
                                            "• Нет интернета\n"
                                            "• Бот не запущен\n"
                                            "• Проблемы с Telegram API")

                except Exception as send_error:
                    QMessageBox.critical(self, "Ошибка отправки",
                                         f"Ошибка при отправке:\n{str(send_error)}")

            except ImportError:
                QMessageBox.critical(self, "Ошибка",
                                     "Библиотека reportlab не установлена!\n\n"
                                     "Установите командой:\n"
                                     "pip install reportlab")
            except Exception as pdf_error:
                QMessageBox.critical(self, "Ошибка создания PDF",
                                     f"Ошибка: {str(pdf_error)}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта",
                                 f"Ошибка: {str(e)}")

    def show_simple_message(self, title, message):
        """Простое сообщение без лишних кнопок"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

    def closeEvent(self, event):
        self.rates_timer.stop()
        self.session_db.close()
        event.accept()