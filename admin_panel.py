from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QLineEdit, QComboBox, QMessageBox, QGroupBox,
                             QFormLayout, QHeaderView, QTabWidget, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from database import db
from models import User, UserRole, UserStatus, Transaction, Exchange, Currency
from transaction_utils import transaction_session
from backup_manager import backup_manager  # Импортируем менеджер бэкапов
from datetime import datetime


class AdminPanelDialog(QDialog):
    def __init__(self, admin_user_id, parent=None):
        super().__init__(parent)
        self.admin_user_id = admin_user_id
        self.selected_user_id = None
        self.init_ui()
        self.load_users()
        self.load_transactions()
        self.load_currencies()

        # Загружаем информацию о последнем бэкапе
        self.load_latest_backup_info()

    def init_ui(self):
        self.setWindowTitle("🛡️ Панель администратора")
        self.setGeometry(300, 200, 1000, 600)
        self.setModal(True)

        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("🛡️ Панель администратора")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2E8B57; margin-bottom: 10px;")
        layout.addWidget(title)

        # Группа восстановления из бэкапа
        backup_group = self.create_backup_group()
        layout.addWidget(backup_group)

        # Простые табы
        tabs = QTabWidget()

        # Вкладка пользователей
        users_tab = self.create_users_tab()
        tabs.addTab(users_tab, "👥 Пользователи")

        # Вкладка операций пользователя
        user_operations_tab = self.create_user_operations_tab()
        tabs.addTab(user_operations_tab, "📊 Операции пользователя")

        # Вкладка транзакций
        transactions_tab = self.create_transactions_tab()
        tabs.addTab(transactions_tab, "💸 Все транзакции")

        # Вкладка валют
        currencies_tab = self.create_currencies_tab()
        tabs.addTab(currencies_tab, "💰 Валюты")

        layout.addWidget(tabs)

        # Простые кнопки
        buttons_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.refresh_all)
        buttons_layout.addWidget(refresh_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def create_backup_group(self):
        """Создание группы восстановления из бэкапа"""
        group = QGroupBox("💾 Восстановление из бэкапа (Яндекс.Диск)")
        layout = QVBoxLayout(group)

        # Информация о последнем бэкапе
        backup_info_layout = QHBoxLayout()

        self.backup_info_label = QLabel("Загрузка информации о бэкапах...")
        self.backup_info_label.setStyleSheet("font-weight: bold;")
        backup_info_layout.addWidget(self.backup_info_label)

        backup_info_layout.addStretch()

        # Кнопка восстановления
        self.restore_backup_btn = QPushButton("🔄 Восстановить из последнего бэкапа")
        self.restore_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #FFB74D;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.restore_backup_btn.clicked.connect(self.restore_from_latest_backup)
        self.restore_backup_btn.setEnabled(False)

        # Кнопка ручного бэкапа
        manual_backup_btn = QPushButton("💾 Создать бэкап сейчас")
        manual_backup_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        manual_backup_btn.clicked.connect(self.create_manual_backup)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.restore_backup_btn)
        buttons_layout.addWidget(manual_backup_btn)

        layout.addLayout(backup_info_layout)
        layout.addLayout(buttons_layout)

        return group

    def load_latest_backup_info(self):
        """Загрузка информации о последнем бэкапе"""
        try:
            latest_backup = backup_manager.get_latest_backup()

            if latest_backup:
                backup_name = latest_backup['name']
                modified = latest_backup['modified']

                if isinstance(modified, str):
                    dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                else:
                    dt = modified

                backup_time = dt.strftime("%d.%m.%Y %H:%M:%S")
                size_mb = latest_backup['size'] / (1024 * 1024)

                info_text = f"📅 Последний бэкап: {backup_time} ({size_mb:.1f} МБ)"

                # Получаем больше информации
                backup_info = backup_manager.get_backup_info(backup_name)
                if backup_info and 'metadata' in backup_info:
                    metadata = backup_info['metadata']
                    if 'description' in metadata:
                        info_text += f"\n📝 Описание: {metadata['description']}"

                self.backup_info_label.setText(info_text)
                self.restore_backup_btn.setEnabled(True)
                self.restore_backup_btn.setText(f"🔄 Восстановить из бэкапа ({backup_time})")
            else:
                self.backup_info_label.setText("⚠️ Бэкапы не найдены")
                self.restore_backup_btn.setEnabled(False)
                self.restore_backup_btn.setText("🔄 Восстановить из последнего бэкапа")

        except Exception as e:
            self.backup_info_label.setText(f"❌ Ошибка загрузки информации: {str(e)}")
            self.restore_backup_btn.setEnabled(False)

    def restore_from_latest_backup(self):
        """Восстановление из последнего бэкапа"""
        reply = QMessageBox.warning(
            self, "Восстановление из бэкапа",
            "⚠️ ВНИМАНИЕ: Вы собираетесь восстановить базу данных из последнего бэкапа!\n\n"
            "Это действие:\n"
            "• Заменит текущую базу данных\n"
            "• Может привести к потере данных, созданных после бэкапа\n"
            "• Потребует перезапуска приложения\n\n"
            "Вы уверены, что хотите продолжить?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Подтверждение
            reply2 = QMessageBox.warning(
                self, "Подтверждение",
                "Это ОПАСНОЕ действие! Текущая база данных будет заменена.\n\n"
                "Для отмены нажмите НЕТ.\n"
                "Для продолжения нажмите ДА.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply2 == QMessageBox.Yes:
                try:
                    # Показываем прогресс
                    QMessageBox.information(
                        self, "Восстановление",
                        "Начинаю восстановление из последнего бэкапа...\n"
                        "Это может занять несколько секунд."
                    )

                    # Выполняем восстановление
                    success, backup_name, error = backup_manager.restore_latest_backup()

                    if success:
                        QMessageBox.information(
                            self, "✅ Восстановление успешно",
                            f"База данных восстановлена из бэкапа:\n{backup_name}\n\n"
                            "Приложение будет закрыто для применения изменений.\n"
                            "Запустите приложение заново."
                        )

                        # Закрываем диалог и приложение
                        self.accept()
                        if self.parent():
                            self.parent().close()
                    else:
                        QMessageBox.critical(
                            self, "❌ Ошибка восстановления",
                            f"Не удалось восстановить базу данных:\n{error}"
                        )

                except Exception as e:
                    QMessageBox.critical(
                        self, "❌ Критическая ошибка",
                        f"Ошибка при восстановлении:\n{str(e)}"
                    )

    def create_manual_backup(self):
        """Создание ручного бэкапа"""
        reply = QMessageBox.question(
            self, "Создание бэкапа",
            "Создать бэкап базы данных сейчас?\n\n"
            "Бэкап будет сохранен на Яндекс.Диск.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Показываем прогресс
                progress_dialog = QMessageBox(
                    QMessageBox.Information,
                    "Создание бэкапа",
                    "Создаю бэкап базы данных...",
                    QMessageBox.NoButton,
                    self
                )
                progress_dialog.show()

                # Создаем бэкап
                backup_name = backup_manager.create_backup(
                    "Ручной бэкап из админ-панели"
                )

                progress_dialog.close()

                if backup_name:
                    QMessageBox.information(
                        self, "✅ Бэкап создан",
                        f"Бэкап успешно создан и загружен на Яндекс.Диск:\n{backup_name}"
                    )

                    # Обновляем информацию о бэкапах
                    self.load_latest_backup_info()
                else:
                    QMessageBox.warning(
                        self, "❌ Ошибка",
                        "Не удалось создать бэкап!"
                    )

            except Exception as e:
                QMessageBox.critical(
                    self, "❌ Ошибка",
                    f"Ошибка при создании бэкапа:\n{str(e)}"
                )

    def create_users_tab(self):
        """Создание вкладки пользователей"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Простой поиск
        search_group = QGroupBox("🔍 Поиск")
        search_layout = QHBoxLayout(search_group)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Телефон, ФИО или ID...")
        self.search_input.textChanged.connect(self.filter_users)
        search_layout.addWidget(self.search_input)

        layout.addWidget(search_group)

        # Таблица пользователей
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(6)
        self.users_table.setHorizontalHeaderLabels([
            "ID", "Телефон", "ФИО", "Роль", "Статус", "Действия"
        ])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.cellClicked.connect(self.on_user_cell_clicked)
        layout.addWidget(self.users_table)

        # Кнопки управления пользователем
        user_actions = QHBoxLayout()

        self.user_details_btn = QPushButton("👁️ Просмотр")
        self.user_details_btn.clicked.connect(self.show_user_details)
        self.user_details_btn.setEnabled(False)
        user_actions.addWidget(self.user_details_btn)

        self.view_operations_btn = QPushButton("📊 Смотреть операции")
        self.view_operations_btn.clicked.connect(self.view_user_operations)
        self.view_operations_btn.setEnabled(False)
        user_actions.addWidget(self.view_operations_btn)

        self.change_role_btn = QPushButton("👑 Изменить роль")
        self.change_role_btn.clicked.connect(self.show_change_role_dialog)
        self.change_role_btn.setEnabled(False)
        user_actions.addWidget(self.change_role_btn)

        self.block_user_btn = QPushButton("🚫 Заблокировать")
        self.block_user_btn.clicked.connect(self.block_user)
        self.block_user_btn.setEnabled(False)
        user_actions.addWidget(self.block_user_btn)

        self.unblock_user_btn = QPushButton("✅ Разблокировать")
        self.unblock_user_btn.clicked.connect(self.unblock_user)
        self.unblock_user_btn.setEnabled(False)
        user_actions.addWidget(self.unblock_user_btn)

        layout.addLayout(user_actions)

        return widget

    def create_user_operations_tab(self):
        """Создание вкладки операций пользователя"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Поиск пользователя по ID
        search_group = QGroupBox("🔍 Поиск пользователя по ID")
        search_layout = QHBoxLayout(search_group)

        self.user_id_input = QLineEdit()
        self.user_id_input.setPlaceholderText("Введите ID пользователя...")
        search_layout.addWidget(QLabel("ID пользователя:"))

        search_layout.addWidget(self.user_id_input)

        search_btn = QPushButton("🔍 Найти")
        search_btn.clicked.connect(self.load_user_operations)
        search_layout.addWidget(search_btn)

        layout.addWidget(search_group)

        # Информация о пользователе
        self.user_info_label = QLabel("Введите ID пользователя для просмотра операций")
        self.user_info_label.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(self.user_info_label)

        # Табы для транзакций и обменов
        operations_tabs = QTabWidget()

        # Вкладка транзакций пользователя
        user_transactions_tab = QWidget()
        user_transactions_layout = QVBoxLayout(user_transactions_tab)

        self.user_transactions_table = QTableWidget()
        self.user_transactions_table.setColumnCount(7)
        self.user_transactions_table.setHorizontalHeaderLabels([
            "ID", "Дата", "Тип", "Направление", "Сумма", "Валюта", "Статус"
        ])
        self.user_transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        user_transactions_layout.addWidget(self.user_transactions_table)

        operations_tabs.addTab(user_transactions_tab, "💸 Транзакции")

        # Вкладка обменов пользователя
        user_exchanges_tab = QWidget()
        user_exchanges_layout = QVBoxLayout(user_exchanges_tab)

        self.user_exchanges_table = QTableWidget()
        self.user_exchanges_table.setColumnCount(8)
        self.user_exchanges_table.setHorizontalHeaderLabels([
            "ID", "Дата", "Тип", "С кем", "Отдает", "Получает", "Статус", "Завершен"
        ])
        self.user_exchanges_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        user_exchanges_layout.addWidget(self.user_exchanges_table)

        operations_tabs.addTab(user_exchanges_tab, "🔄 Обмены")

        layout.addWidget(operations_tabs)

        # Статистика
        stats_group = QGroupBox("📊 Статистика операций")
        stats_layout = QHBoxLayout(stats_group)

        self.total_transactions_label = QLabel("Транзакций: 0")
        stats_layout.addWidget(self.total_transactions_label)

        self.total_exchanges_label = QLabel("Обменов: 0")
        stats_layout.addWidget(self.total_exchanges_label)

        self.total_sent_label = QLabel("Отправлено: 0")
        stats_layout.addWidget(self.total_sent_label)

        self.total_received_label = QLabel("Получено: 0")
        stats_layout.addWidget(self.total_received_label)

        stats_layout.addStretch()
        layout.addWidget(stats_group)

        return widget

    def create_transactions_tab(self):
        """Создание вкладки всех транзакций"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Простая таблица транзакций
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(7)
        self.transactions_table.setHorizontalHeaderLabels([
            "ID", "Дата", "Тип", "От кого", "Кому", "Сумма", "Статус"
        ])
        self.transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.transactions_table)

        # Кнопка обновления транзакций
        refresh_transactions_btn = QPushButton("🔄 Обновить транзакции")
        refresh_transactions_btn.clicked.connect(self.load_transactions)
        layout.addWidget(refresh_transactions_btn)

        return widget

    def create_currencies_tab(self):
        """Создание вкладки валют"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Таблица валют
        self.currencies_table = QTableWidget()
        self.currencies_table.setColumnCount(5)
        self.currencies_table.setHorizontalHeaderLabels([
            "Код", "Название", "Курс USDT", "Мин. депозит", "Мин. вывод"
        ])
        self.currencies_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.currencies_table)

        # Простые действия
        actions_layout = QHBoxLayout()

        update_rates_btn = QPushButton("📈 Обновить курсы")
        update_rates_btn.clicked.connect(self.update_exchange_rates)
        actions_layout.addWidget(update_rates_btn)

        add_currency_btn = QPushButton("➕ Добавить валюту")
        add_currency_btn.clicked.connect(self.add_currency)
        actions_layout.addWidget(add_currency_btn)

        layout.addLayout(actions_layout)

        return widget

    # ===================== ОСНОВНЫЕ МЕТОДЫ =====================

    def load_users(self):
        """Загрузка пользователей"""
        try:
            session = db.get_session()
            users = session.query(User).order_by(User.id).all()

            self.users_table.setRowCount(len(users))

            for row, user in enumerate(users):
                # ID
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user.id)))

                # Телефон
                self.users_table.setItem(row, 1, QTableWidgetItem(user.phone))

                # ФИО
                self.users_table.setItem(row, 2, QTableWidgetItem(user.full_name))

                # Роль
                role_item = QTableWidgetItem(user.get_role_display())
                if user.role == UserRole.ADMIN:
                    role_item.setForeground(QColor("#FF0000"))
                elif user.role == UserRole.MODERATOR:
                    role_item.setForeground(QColor("#FF8C00"))
                self.users_table.setItem(row, 3, role_item)

                # Статус
                status_item = QTableWidgetItem(user.status.value)
                if user.status == UserStatus.ACTIVE:
                    status_item.setForeground(QColor("#2E8B57"))
                else:
                    status_item.setForeground(QColor("#DC143C"))
                self.users_table.setItem(row, 4, status_item)

                # Действия (просто текст)
                actions_item = QTableWidgetItem("Нажмите для выбора")
                actions_item.setForeground(QColor("#1E90FF"))
                self.users_table.setItem(row, 5, actions_item)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки пользователей: {str(e)}")
        finally:
            session.close()

    def load_user_operations(self):
        """Загрузка операций пользователя по ID"""
        user_id_str = self.user_id_input.text().strip()

        if not user_id_str:
            QMessageBox.warning(self, "Ошибка", "Введите ID пользователя!")
            return

        try:
            user_id = int(user_id_str)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "ID должен быть числом!")
            return

        try:
            session = db.get_session()

            # Получаем информацию о пользователе
            user = session.query(User).get(user_id)
            if not user:
                QMessageBox.warning(self, "Ошибка", "Пользователь не найден!")
                return

            # Обновляем информацию о пользователе
            self.user_info_label.setText(
                f"👤 Пользователь: {user.full_name} (ID: {user.id})\n"
                f"📱 Телефон: {user.phone} | 👑 Роль: {user.get_role_display()} | "
                f"📊 Статус: {user.status.value}"
            )

            # Загружаем транзакции пользователя
            transactions = session.query(Transaction).filter(
                (Transaction.user_id_from == user_id) |
                (Transaction.user_id_to == user_id)
            ).order_by(Transaction.created_date.desc()).all()

            self.user_transactions_table.setRowCount(len(transactions))

            total_sent = 0
            total_received = 0

            for row, transaction in enumerate(transactions):
                # ID
                self.user_transactions_table.setItem(row, 0, QTableWidgetItem(str(transaction.id)))

                # Дата
                date_str = transaction.created_date.strftime("%d.%m.%Y %H:%M") if transaction.created_date else "-"
                self.user_transactions_table.setItem(row, 1, QTableWidgetItem(date_str))

                # Тип
                type_text = "Перевод"
                self.user_transactions_table.setItem(row, 2, QTableWidgetItem(type_text))

                # Направление
                if transaction.user_id_from == user_id:
                    direction = "📤 Отправка"
                    total_sent += transaction.amount
                else:
                    direction = "📥 Получение"
                    total_received += transaction.amount

                self.user_transactions_table.setItem(row, 3, QTableWidgetItem(direction))

                # Сумма
                amount_item = QTableWidgetItem(f"{transaction.amount:.6f}")
                if transaction.user_id_from == user_id:
                    amount_item.setForeground(QColor("#f44336"))  # Красный для отправки
                else:
                    amount_item.setForeground(QColor("#4CAF50"))  # Зеленый для получения
                self.user_transactions_table.setItem(row, 4, amount_item)

                # Валюта
                currency_code = transaction.currency_rel.code if transaction.currency_rel else "N/A"
                self.user_transactions_table.setItem(row, 5, QTableWidgetItem(currency_code))

                # Статус
                status_item = QTableWidgetItem(transaction.status)
                if transaction.status == 'completed':
                    status_item.setForeground(QColor("#2E8B57"))
                elif transaction.status == 'pending':
                    status_item.setForeground(QColor("#FF9800"))
                else:
                    status_item.setForeground(QColor("#DC143C"))
                self.user_transactions_table.setItem(row, 6, status_item)

            # Загружаем обмены пользователя
            exchanges = session.query(Exchange).filter(
                (Exchange.user_id_from == user_id) |
                (Exchange.user_id_to == user_id)
            ).order_by(Exchange.created_date.desc()).all()

            self.user_exchanges_table.setRowCount(len(exchanges))

            for row, exchange in enumerate(exchanges):
                # ID
                self.user_exchanges_table.setItem(row, 0, QTableWidgetItem(str(exchange.id)))

                # Дата
                date_str = exchange.created_date.strftime("%d.%m.%Y %H:%M") if exchange.created_date else "-"
                self.user_exchanges_table.setItem(row, 1, QTableWidgetItem(date_str))

                # Тип
                if exchange.user_id_from == user_id:
                    exchange_type = "📤 Исходящий"
                else:
                    exchange_type = "📥 Входящий"
                self.user_exchanges_table.setItem(row, 2, QTableWidgetItem(exchange_type))

                # С кем обменивался
                if exchange.user_id_from == user_id:
                    partner = exchange.user_to
                    partner_text = f"{partner.full_name} (ID: {partner.id})" if partner else "N/A"
                else:
                    partner = exchange.user_from
                    partner_text = f"{partner.full_name} (ID: {partner.id})" if partner else "N/A"
                self.user_exchanges_table.setItem(row, 3, QTableWidgetItem(partner_text))

                # Отдает
                from_currency = session.query(Currency).get(exchange.currency_from_id)
                give_text = f"{exchange.amount_from:.6f} {from_currency.code}" if from_currency else "N/A"
                self.user_exchanges_table.setItem(row, 4, QTableWidgetItem(give_text))

                # Получает
                to_currency = session.query(Currency).get(exchange.currency_to_id)
                receive_text = f"{exchange.amount_to:.6f} {to_currency.code}" if to_currency else "N/A"
                self.user_exchanges_table.setItem(row, 5, QTableWidgetItem(receive_text))

                # Статус
                status_item = QTableWidgetItem(exchange.status.value)
                if exchange.status.value == 'COMPLETED':
                    status_item.setForeground(QColor("#2E8B57"))
                elif exchange.status.value == 'PENDING':
                    status_item.setForeground(QColor("#FF9800"))
                else:
                    status_item.setForeground(QColor("#f44336"))
                self.user_exchanges_table.setItem(row, 6, status_item)

                # Дата завершения
                completed_date = exchange.completed_date.strftime("%d.%m %H:%M") if exchange.completed_date else "-"
                self.user_exchanges_table.setItem(row, 7, QTableWidgetItem(completed_date))

            # Обновляем статистику
            self.total_transactions_label.setText(f"Транзакций: {len(transactions)}")
            self.total_exchanges_label.setText(f"Обменов: {len(exchanges)}")
            self.total_sent_label.setText(f"Отправлено: {total_sent:.2f}")
            self.total_received_label.setText(f"Получено: {total_received:.2f}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки операций: {str(e)}")
        finally:
            session.close()

    def load_transactions(self):
        """Загрузка всех транзакций"""
        try:
            session = db.get_session()
            transactions = session.query(Transaction).order_by(
                Transaction.created_date.desc()
            ).limit(100).all()

            self.transactions_table.setRowCount(len(transactions))

            for row, transaction in enumerate(transactions):
                # ID
                self.transactions_table.setItem(row, 0, QTableWidgetItem(str(transaction.id)))

                # Дата
                date_str = transaction.created_date.strftime("%d.%m.%Y %H:%M") if transaction.created_date else "-"
                self.transactions_table.setItem(row, 1, QTableWidgetItem(date_str))

                # Тип
                self.transactions_table.setItem(row, 2, QTableWidgetItem(transaction.type.value))

                # От кого
                from_user = session.query(User).get(transaction.user_id_from)
                self.transactions_table.setItem(row, 3, QTableWidgetItem(
                    f"{from_user.full_name} (ID: {from_user.id})" if from_user else "Система"
                ))

                # Кому
                to_user = session.query(User).get(transaction.user_id_to)
                self.transactions_table.setItem(row, 4, QTableWidgetItem(
                    f"{to_user.full_name} (ID: {to_user.id})" if to_user else "Система"
                ))

                # Сумма
                self.transactions_table.setItem(row, 5, QTableWidgetItem(f"{transaction.amount:.2f}"))

                # Статус
                status_item = QTableWidgetItem(transaction.status)
                if transaction.status == 'completed':
                    status_item.setForeground(QColor("#2E8B57"))
                elif transaction.status == 'pending':
                    status_item.setForeground(QColor("#FF9800"))
                else:
                    status_item.setForeground(QColor("#DC143C"))
                self.transactions_table.setItem(row, 6, status_item)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки транзакций: {str(e)}")
        finally:
            session.close()

    def load_currencies(self):
        """Загрузка валют"""
        try:
            from crypto_manager import crypto_manager

            self.currencies_table.setRowCount(len(crypto_manager.current_rates))

            for row, (currency_code, rate) in enumerate(crypto_manager.current_rates.items()):
                # Код
                self.currencies_table.setItem(row, 0, QTableWidgetItem(currency_code))

                # Название
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
                name = names.get(currency_code, currency_code)
                self.currencies_table.setItem(row, 1, QTableWidgetItem(name))

                # Курс
                self.currencies_table.setItem(row, 2, QTableWidgetItem(f"{rate:.2f} USDT"))

                # Мин. значения (заглушки)
                self.currencies_table.setItem(row, 3, QTableWidgetItem("0.001"))
                self.currencies_table.setItem(row, 4, QTableWidgetItem("0.002"))

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки валют: {str(e)}")

    def filter_users(self):
        """Простая фильтрация"""
        search_text = self.search_input.text().lower()

        for row in range(self.users_table.rowCount()):
            show_row = False

            for col in [0, 1, 2]:  # ID, телефон, ФИО
                item = self.users_table.item(row, col)
                if item and search_text in item.text().lower():
                    show_row = True
                    break

            self.users_table.setRowHidden(row, not show_row)

    def on_user_cell_clicked(self, row, column):
        """Выбор пользователя"""
        if column == 5:  # Колонка "Действия"
            user_id = int(self.users_table.item(row, 0).text())
            self.select_user(user_id, row)

    def select_user(self, user_id, row):
        """Выбор пользователя для действий"""
        self.selected_user_id = user_id

        # Получаем статус пользователя
        status_item = self.users_table.item(row, 4)
        status = status_item.text()

        # Включаем/выключаем кнопки
        self.user_details_btn.setEnabled(True)
        self.view_operations_btn.setEnabled(True)
        self.change_role_btn.setEnabled(True)
        self.block_user_btn.setEnabled(status == 'ACTIVE')
        self.unblock_user_btn.setEnabled(status == 'BLOCKED')

    def view_user_operations(self):
        """Просмотр операций выбранного пользователя"""
        if not self.selected_user_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите пользователя!")
            return

        # Переходим на вкладку операций пользователя
        for i in range(self.parent().layout().count()):
            widget = self.parent().layout().itemAt(i).widget()
            if isinstance(widget, QTabWidget):
                widget.setCurrentIndex(1)
                break

        # Устанавливаем ID пользователя и загружаем операции
        self.user_id_input.setText(str(self.selected_user_id))
        self.load_user_operations()

    # ===================== ДЕЙСТВИЯ С ПОЛЬЗОВАТЕЛЯМИ =====================

    def show_user_details(self):
        """Просмотр деталей пользователя"""
        if not self.selected_user_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите пользователя!")
            return

        try:
            session = db.get_session()
            user = session.query(User).get(self.selected_user_id)

            if user:
                # Простой диалог с информацией
                info = f"""
                👤 **Информация о пользователе**

                **ID:** {user.id}
                **Телефон:** {user.phone}
                **ФИО:** {user.full_name}
                **Telegram ID:** {user.telegram_id or 'Не привязан'}
                **Роль:** {user.get_role_display()}
                **Статус:** {user.status.value}
                **Регистрация:** {user.registration_date.strftime('%d.%m.%Y') if user.registration_date else '-'}
                **Последний вход:** {user.last_login.strftime('%d.%m.%Y %H:%M') if user.last_login else 'Никогда'}

                **Кошельки:**
                """

                # Добавляем информацию о кошельках
                for wallet in user.wallets:
                    info += f"\n• {wallet.currency.code}: {wallet.balance:.6f}"

                QMessageBox.information(self, "Детали пользователя", info)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных: {str(e)}")
        finally:
            session.close()

    def show_change_role_dialog(self):
        """Диалог изменения роли"""
        if not self.selected_user_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите пользователя!")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Изменение роли")
        dialog.setGeometry(400, 300, 300, 150)

        layout = QVBoxLayout()

        label = QLabel("Выберите новую роль:")
        layout.addWidget(label)

        role_combo = QComboBox()
        role_combo.addItem("Пользователь", UserRole.USER.value)
        role_combo.addItem("Модератор", UserRole.MODERATOR.value)
        role_combo.addItem("Администратор", UserRole.ADMIN.value)
        layout.addWidget(role_combo)

        buttons_layout = QHBoxLayout()

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(lambda: self.save_user_role(dialog, role_combo))
        buttons_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)
        dialog.setLayout(layout)
        dialog.exec_()

    def save_user_role(self, dialog, role_combo):
        """Сохранение новой роли"""
        try:
            new_role = UserRole(role_combo.currentData())

            with transaction_session() as session:
                user = session.query(User).get(self.selected_user_id)
                if user:
                    # Проверяем, что не меняем роль последнему админу
                    if user.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
                        admin_count = session.query(User).filter_by(role=UserRole.ADMIN).count()
                        if admin_count <= 1:
                            QMessageBox.warning(self, "Ошибка",
                                                "Нельзя изменить роль последнему администратору!")
                            return

                    user.role = new_role
                    session.commit()

                    QMessageBox.information(self, "Успех",
                                            f"Роль пользователя изменена на: {role_combo.currentText()}")

                    self.load_users()
                    dialog.accept()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка изменения роли: {str(e)}")

    def block_user(self):
        """Блокировка пользователя"""
        if not self.selected_user_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите пользователя!")
            return

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Заблокировать пользователя ID {self.selected_user_id}?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                with transaction_session() as session:
                    user = session.query(User).get(self.selected_user_id)
                    if user and user.status == UserStatus.ACTIVE:
                        user.status = UserStatus.BLOCKED
                        session.commit()

                        QMessageBox.information(self, "Успех", "Пользователь заблокирован!")
                        self.load_users()

            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка блокировки: {str(e)}")

    def unblock_user(self):
        """Разблокировка пользователя"""
        if not self.selected_user_id:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите пользователя!")
            return

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Разблокировать пользователя ID {self.selected_user_id}?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                with transaction_session() as session:
                    user = session.query(User).get(self.selected_user_id)
                    if user and user.status == UserStatus.BLOCKED:
                        user.status = UserStatus.ACTIVE
                        session.commit()

                        QMessageBox.information(self, "Успех", "Пользователь разблокирован!")
                        self.load_users()

            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка разблокировки: {str(e)}")

    def update_exchange_rates(self):
        """Обновление курсов валют"""
        try:
            from crypto_manager import crypto_manager
            crypto_manager.update_exchange_rates()
            self.load_currencies()
            QMessageBox.information(self, "Успех", "Курсы валют обновлены!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка обновления: {str(e)}")

    def add_currency(self):
        """Добавление новой валюты"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавление валюты")
        dialog.setGeometry(400, 300, 300, 200)

        layout = QVBoxLayout()

        form_layout = QFormLayout()

        name_input = QLineEdit()
        name_input.setPlaceholderText("Bitcoin")
        form_layout.addRow("Название:", name_input)

        code_input = QLineEdit()
        code_input.setPlaceholderText("BTC")
        form_layout.addRow("Код:", code_input)

        rate_input = QLineEdit()
        rate_input.setPlaceholderText("85000.0")
        form_layout.addRow("Курс к USDT:", rate_input)

        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(lambda: self.save_new_currency(dialog, name_input, code_input, rate_input))
        buttons_layout.addWidget(add_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)
        dialog.setLayout(layout)
        dialog.exec_()

    def save_new_currency(self, dialog, name_input, code_input, rate_input):
        """Сохранение новой валюты"""
        try:
            name = name_input.text().strip()
            code = code_input.text().strip().upper()
            rate = float(rate_input.text())

            if not all([name, code]):
                QMessageBox.warning(self, "Ошибка", "Заполните все поля!")
                return

            with transaction_session() as session:
                # Проверяем существование
                existing = session.query(Currency).filter_by(code=code).first()
                if existing:
                    QMessageBox.warning(self, "Ошибка", "Такая валюта уже существует!")
                    return

                # Добавляем валюту
                currency = Currency(
                    name=name,
                    code=code,
                    min_deposit=0.001,
                    min_withdrawal=0.002
                )
                session.add(currency)
                session.flush()

                # Обновляем курсы в crypto_manager
                from crypto_manager import crypto_manager
                crypto_manager.base_rates[code] = rate
                crypto_manager.current_rates[code] = rate

                QMessageBox.information(self, "Успех", f"Валюта {code} добавлена!")
                self.load_currencies()
                dialog.accept()

        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите корректное число для курса!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка добавления: {str(e)}")

    def refresh_all(self):
        """Обновление всех данных"""
        self.load_users()
        self.load_transactions()
        self.load_currencies()
        QMessageBox.information(self, "Успех", "Данные обновлены!")