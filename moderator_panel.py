from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QHeaderView, QLineEdit, QTabWidget,
                             QWidget, QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor
from database import db
from models import User, UserStatus, Transaction, Exchange, Currency
from transaction_utils import transaction_session
from datetime import datetime, timedelta


class ModeratorPanelDialog(QDialog):
    def __init__(self, moderator_user_id, parent=None):
        super().__init__(parent)
        self.moderator_user_id = moderator_user_id
        self.init_ui()
        self.load_recent_activity()

    def init_ui(self):
        self.setWindowTitle("🛡️ Панель модератора")
        self.setGeometry(300, 200, 900, 600)
        self.setModal(True)

        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("🛡️ Панель модератора")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #FF8C00; margin-bottom: 10px;")
        layout.addWidget(title)

        # Табы
        tabs = QTabWidget()

        # Вкладка мониторинга
        monitor_tab = self.create_monitor_tab()
        tabs.addTab(monitor_tab, "📊 Мониторинг")

        # Вкладка операций пользователя
        user_operations_tab = self.create_user_operations_tab()
        tabs.addTab(user_operations_tab, "👤 Операции пользователя")

        layout.addWidget(tabs)

        # Кнопки
        buttons_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.refresh_all)
        buttons_layout.addWidget(refresh_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def create_monitor_tab(self):
        """Создание вкладки мониторинга"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Блокировка пользователя
        block_group = QGroupBox("🚫 Блокировка пользователя")
        block_layout = QHBoxLayout(block_group)

        self.user_id_input = QLineEdit()
        self.user_id_input.setPlaceholderText("ID пользователя")
        block_layout.addWidget(QLabel("ID пользователя:"))
        block_layout.addWidget(self.user_id_input)

        block_btn = QPushButton("🚫 Заблокировать")
        block_btn.clicked.connect(self.block_user_by_id)
        block_btn.setStyleSheet("background-color: #f44336; color: white;")
        block_layout.addWidget(block_btn)

        unblock_btn = QPushButton("✅ Разблокировать")
        unblock_btn.clicked.connect(self.unblock_user_by_id)
        unblock_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        block_layout.addWidget(unblock_btn)

        layout.addWidget(block_group)

        # Последние транзакции
        transactions_label = QLabel("📊 Последние транзакции (20):")
        transactions_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(transactions_label)

        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(7)
        self.transactions_table.setHorizontalHeaderLabels([
            "ID", "Дата", "Тип", "От кого", "Кому", "Сумма", "Статус"
        ])
        self.transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.transactions_table)

        # Последние пользователи
        users_label = QLabel("👤 Последние пользователи (10):")
        users_label.setFont(QFont("Arial", 12, QFont.Bold))
        users_label.setStyleSheet("margin-top: 20px;")
        layout.addWidget(users_label)

        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels([
            "ID", "Телефон", "ФИО", "Роль", "Статус"
        ])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.users_table)

        return widget

    def create_user_operations_tab(self):
        """Создание вкладки операций пользователя (только последние 30 дней)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Поиск пользователя по ID
        search_group = QGroupBox("🔍 Поиск пользователя по ID (только последние 30 дней)")
        search_layout = QHBoxLayout(search_group)

        self.user_operations_id_input = QLineEdit()
        self.user_operations_id_input.setPlaceholderText("Введите ID пользователя...")
        search_layout.addWidget(QLabel("ID пользователя:"))

        search_layout.addWidget(self.user_operations_id_input)

        search_btn = QPushButton("🔍 Найти")
        search_btn.clicked.connect(self.load_user_operations_30_days)
        search_layout.addWidget(search_btn)

        layout.addWidget(search_group)

        # Информация о пользователе
        self.user_operations_info_label = QLabel("Введите ID пользователя для просмотра операций за последние 30 дней")
        self.user_operations_info_label.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(self.user_operations_info_label)

        # Табы для транзакций и обменов
        operations_tabs = QTabWidget()

        # Вкладка транзакций пользователя
        user_transactions_tab = QWidget()
        user_transactions_layout = QVBoxLayout(user_transactions_tab)

        self.user_operations_transactions_table = QTableWidget()
        self.user_operations_transactions_table.setColumnCount(6)
        self.user_operations_transactions_table.setHorizontalHeaderLabels([
            "Дата", "Тип", "Направление", "Сумма", "Валюта", "Статус"
        ])
        self.user_operations_transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        user_transactions_layout.addWidget(self.user_operations_transactions_table)

        operations_tabs.addTab(user_transactions_tab, "💸 Транзакции")

        # Вкладка обменов пользователя
        user_exchanges_tab = QWidget()
        user_exchanges_layout = QVBoxLayout(user_exchanges_tab)

        self.user_operations_exchanges_table = QTableWidget()
        self.user_operations_exchanges_table.setColumnCount(6)
        self.user_operations_exchanges_table.setHorizontalHeaderLabels([
            "Дата", "Тип", "С кем", "Отдает", "Получает", "Статус"
        ])
        self.user_operations_exchanges_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        user_exchanges_layout.addWidget(self.user_operations_exchanges_table)

        operations_tabs.addTab(user_exchanges_tab, "🔄 Обмены")

        layout.addWidget(operations_tabs)

        # Статистика за 30 дней
        stats_group = QGroupBox("📊 Статистика за 30 дней")
        stats_layout = QHBoxLayout(stats_group)

        self.user_total_transactions_label = QLabel("Транзакций: 0")
        stats_layout.addWidget(self.user_total_transactions_label)

        self.user_total_exchanges_label = QLabel("Обменов: 0")
        stats_layout.addWidget(self.user_total_exchanges_label)

        self.user_total_sent_label = QLabel("Отправлено: 0")
        stats_layout.addWidget(self.user_total_sent_label)

        self.user_total_received_label = QLabel("Получено: 0")
        stats_layout.addWidget(self.user_total_received_label)

        stats_layout.addStretch()
        layout.addWidget(stats_group)

        return widget

    # ===================== МЕТОДЫ МОНИТОРИНГА =====================

    def load_recent_activity(self):
        """Загрузка последней активности"""
        try:
            session = db.get_session()

            # Загружаем последние 20 транзакций
            transactions = session.query(Transaction).order_by(
                Transaction.created_date.desc()
            ).limit(20).all()

            self.transactions_table.setRowCount(len(transactions))

            for row, transaction in enumerate(transactions):
                # ID
                self.transactions_table.setItem(row, 0, QTableWidgetItem(str(transaction.id)))

                # Дата
                date_str = transaction.created_date.strftime("%d.%m %H:%M") if transaction.created_date else "-"
                self.transactions_table.setItem(row, 1, QTableWidgetItem(date_str))

                # Тип
                type_text = "Перевод" if transaction.type.value == 'TRANSFER' else transaction.type.value
                self.transactions_table.setItem(row, 2, QTableWidgetItem(type_text))

                # От кого
                from_user = session.query(User).get(transaction.user_id_from)
                self.transactions_table.setItem(row, 3, QTableWidgetItem(
                    from_user.full_name[:15] if from_user else "Система"
                ))

                # Кому
                to_user = session.query(User).get(transaction.user_id_to)
                self.transactions_table.setItem(row, 4, QTableWidgetItem(
                    to_user.full_name[:15] if to_user else "Система"
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

            # Загружаем последних 10 пользователей
            users = session.query(User).order_by(
                User.registration_date.desc()
            ).limit(10).all()

            self.users_table.setRowCount(len(users))

            for row, user in enumerate(users):
                # ID
                self.users_table.setItem(row, 0, QTableWidgetItem(str(user.id)))

                # Телефон
                self.users_table.setItem(row, 1, QTableWidgetItem(user.phone))

                # ФИО
                self.users_table.setItem(row, 2, QTableWidgetItem(user.full_name[:20]))

                # Роль
                role_text = "Админ" if user.role.value == 'ADMIN' else \
                    "Модератор" if user.role.value == 'MODERATOR' else "Пользователь"
                role_item = QTableWidgetItem(role_text)
                if user.role.value == "ADMIN":
                    role_item.setForeground(QColor("#FF0000"))
                elif user.role.value == "MODERATOR":
                    role_item.setForeground(QColor("#FF8C00"))
                self.users_table.setItem(row, 3, role_item)

                # Статус
                status_item = QTableWidgetItem(user.status.value)
                if user.status == UserStatus.ACTIVE:
                    status_item.setForeground(QColor("#2E8B57"))
                else:
                    status_item.setForeground(QColor("#DC143C"))
                self.users_table.setItem(row, 4, status_item)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных: {str(e)}")
        finally:
            session.close()

    def block_user_by_id(self):
        """Блокировка пользователя по ID"""
        user_id = self.user_id_input.text().strip()

        if not user_id:
            QMessageBox.warning(self, "Ошибка", "Введите ID пользователя!")
            return

        try:
            user_id_int = int(user_id)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "ID должен быть числом!")
            return

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Заблокировать пользователя ID {user_id}?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                with transaction_session() as session:
                    user = session.query(User).get(user_id_int)
                    if not user:
                        QMessageBox.warning(self, "Ошибка", "Пользователь не найден!")
                        return

                    if user.role.value == 'ADMIN':
                        QMessageBox.warning(self, "Ошибка", "Нельзя заблокировать администратора!")
                        return

                    if user.status == UserStatus.BLOCKED:
                        QMessageBox.warning(self, "Ошибка", "Пользователь уже заблокирован!")
                        return

                    user.status = UserStatus.BLOCKED
                    session.commit()

                    QMessageBox.information(self, "Успех", "Пользователь заблокирован!")
                    self.load_recent_activity()
                    self.user_id_input.clear()

            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка блокировки: {str(e)}")

    def unblock_user_by_id(self):
        """Разблокировка пользователя по ID"""
        user_id = self.user_id_input.text().strip()

        if not user_id:
            QMessageBox.warning(self, "Ошибка", "Введите ID пользователя!")
            return

        try:
            user_id_int = int(user_id)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "ID должен быть числом!")
            return

        reply = QMessageBox.question(self, "Подтверждение",
                                     f"Разблокировать пользователя ID {user_id}?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                with transaction_session() as session:
                    user = session.query(User).get(user_id_int)
                    if not user:
                        QMessageBox.warning(self, "Ошибка", "Пользователь не найден!")
                        return

                    if user.status != UserStatus.BLOCKED:
                        QMessageBox.warning(self, "Ошибка", "Пользователь не заблокирован!")
                        return

                    user.status = UserStatus.ACTIVE
                    session.commit()

                    QMessageBox.information(self, "Успех", "Пользователь разблокирован!")
                    self.load_recent_activity()
                    self.user_id_input.clear()

            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка разблокировки: {str(e)}")

    # ===================== МЕТОДЫ ОПЕРАЦИЙ ПОЛЬЗОВАТЕЛЯ (30 дней) =====================

    def load_user_operations_30_days(self):
        """Загрузка операций пользователя за последние 30 дней"""
        user_id_str = self.user_operations_id_input.text().strip()

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

            # Рассчитываем дату 30 дней назад
            thirty_days_ago = datetime.now() - timedelta(days=30)

            # Обновляем информацию о пользователе
            self.user_operations_info_label.setText(
                f"👤 Пользователь: {user.full_name} (ID: {user.id})\n"
                f"📱 Телефон: {user.phone} | 👑 Роль: {user.get_role_display()} | "
                f"📊 Статус: {user.status.value}\n"
                f"📅 Период: Последние 30 дней"
            )

            # Загружаем транзакции пользователя за последние 30 дней
            transactions = session.query(Transaction).filter(
                ((Transaction.user_id_from == user_id) |
                 (Transaction.user_id_to == user_id)) &
                (Transaction.created_date >= thirty_days_ago)
            ).order_by(Transaction.created_date.desc()).all()

            self.user_operations_transactions_table.setRowCount(len(transactions))

            total_sent = 0
            total_received = 0

            for row, transaction in enumerate(transactions):
                # Дата
                date_str = transaction.created_date.strftime("%d.%m.%Y %H:%M") if transaction.created_date else "-"
                self.user_operations_transactions_table.setItem(row, 0, QTableWidgetItem(date_str))

                # Тип
                type_text = "Перевод"
                self.user_operations_transactions_table.setItem(row, 1, QTableWidgetItem(type_text))

                # Направление
                if transaction.user_id_from == user_id:
                    direction = "📤 Отправка"
                    total_sent += transaction.amount
                else:
                    direction = "📥 Получение"
                    total_received += transaction.amount

                self.user_operations_transactions_table.setItem(row, 2, QTableWidgetItem(direction))

                # Сумма
                amount_item = QTableWidgetItem(f"{transaction.amount:.6f}")
                if transaction.user_id_from == user_id:
                    amount_item.setForeground(QColor("#f44336"))  # Красный для отправки
                else:
                    amount_item.setForeground(QColor("#4CAF50"))  # Зеленый для получения
                self.user_operations_transactions_table.setItem(row, 3, amount_item)

                # Валюта
                currency_code = transaction.currency_rel.code if transaction.currency_rel else "N/A"
                self.user_operations_transactions_table.setItem(row, 4, QTableWidgetItem(currency_code))

                # Статус
                status_item = QTableWidgetItem(transaction.status)
                if transaction.status == 'completed':
                    status_item.setForeground(QColor("#2E8B57"))
                elif transaction.status == 'pending':
                    status_item.setForeground(QColor("#FF9800"))
                else:
                    status_item.setForeground(QColor("#DC143C"))
                self.user_operations_transactions_table.setItem(row, 5, status_item)

            # Загружаем обмены пользователя за последние 30 дней
            exchanges = session.query(Exchange).filter(
                ((Exchange.user_id_from == user_id) |
                 (Exchange.user_id_to == user_id)) &
                (Exchange.created_date >= thirty_days_ago)
            ).order_by(Exchange.created_date.desc()).all()

            self.user_operations_exchanges_table.setRowCount(len(exchanges))

            for row, exchange in enumerate(exchanges):
                # Дата
                date_str = exchange.created_date.strftime("%d.%m.%Y %H:%M") if exchange.created_date else "-"
                self.user_operations_exchanges_table.setItem(row, 0, QTableWidgetItem(date_str))

                # Тип
                if exchange.user_id_from == user_id:
                    exchange_type = "📤 Исходящий"
                else:
                    exchange_type = "📥 Входящий"
                self.user_operations_exchanges_table.setItem(row, 1, QTableWidgetItem(exchange_type))

                # С кем обменивался
                if exchange.user_id_from == user_id:
                    partner = exchange.user_to
                    partner_text = f"{partner.full_name[:20]}..." if partner else "N/A"
                else:
                    partner = exchange.user_from
                    partner_text = f"{partner.full_name[:20]}..." if partner else "N/A"
                self.user_operations_exchanges_table.setItem(row, 2, QTableWidgetItem(partner_text))

                # Отдает
                from_currency = session.query(Currency).get(exchange.currency_from_id)
                give_text = f"{exchange.amount_from:.2f} {from_currency.code}" if from_currency else "N/A"
                self.user_operations_exchanges_table.setItem(row, 3, QTableWidgetItem(give_text))

                # Получает
                to_currency = session.query(Currency).get(exchange.currency_to_id)
                receive_text = f"{exchange.amount_to:.2f} {to_currency.code}" if to_currency else "N/A"
                self.user_operations_exchanges_table.setItem(row, 4, QTableWidgetItem(receive_text))

                # Статус
                status_item = QTableWidgetItem(exchange.status.value)
                if exchange.status.value == 'COMPLETED':
                    status_item.setForeground(QColor("#2E8B57"))
                elif exchange.status.value == 'PENDING':
                    status_item.setForeground(QColor("#FF9800"))
                else:
                    status_item.setForeground(QColor("#f44336"))
                self.user_operations_exchanges_table.setItem(row, 5, status_item)

            # Обновляем статистику
            self.user_total_transactions_label.setText(f"Транзакций: {len(transactions)}")
            self.user_total_exchanges_label.setText(f"Обменов: {len(exchanges)}")
            self.user_total_sent_label.setText(f"Отправлено: {total_sent:.2f}")
            self.user_total_received_label.setText(f"Получено: {total_received:.2f}")

            # Если нет операций за 30 дней
            if len(transactions) == 0 and len(exchanges) == 0:
                QMessageBox.information(self, "Информация",
                                        f"У пользователя {user.full_name} нет операций за последние 30 дней.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки операций: {str(e)}")
        finally:
            session.close()

    # ===================== ОБЩИЕ МЕТОДЫ =====================

    def refresh_all(self):
        """Обновление всех данных"""
        self.load_recent_activity()
        QMessageBox.information(self, "Успех", "Данные обновлены!")