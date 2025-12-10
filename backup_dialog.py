from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QHeaderView, QGroupBox,
                             QProgressBar, QComboBox, QLineEdit, QCheckBox,
                             QFormLayout, QSplitter, QTextEdit, QWidget)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from backup_manager import backup_manager
import threading
from datetime import datetime


class BackupDialog(QDialog):
    backup_created = pyqtSignal(str)
    backup_restored = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_backups()
        self.load_disk_info()

        # Таймер для обновления информации
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.load_disk_info)
        self.update_timer.start(30000)  # Обновляем каждые 30 секунд

    def init_ui(self):
        self.setWindowTitle("📦 Управление бэкапами")
        self.setGeometry(300, 200, 900, 600)
        self.setModal(True)

        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("📦 Управление бэкапами на Яндекс.Диске")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2196F3; margin-bottom: 10px;")
        layout.addWidget(title)

        # Информация о диске
        self.disk_info_group = self.create_disk_info_group()
        layout.addWidget(self.disk_info_group)

        # Основная часть
        splitter = QSplitter(Qt.Horizontal)

        # Левая часть - список бэкапов
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        backups_label = QLabel("📋 Список бэкапов:")
        backups_label.setFont(QFont("Arial", 12, QFont.Bold))
        left_layout.addWidget(backups_label)

        self.backups_table = QTableWidget()
        self.backups_table.setColumnCount(5)
        self.backups_table.setHorizontalHeaderLabels([
            "Имя", "Размер", "Дата", "Время", "Действия"
        ])
        self.backups_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.backups_table.cellClicked.connect(self.on_backup_cell_clicked)
        left_layout.addWidget(self.backups_table)

        # Кнопки управления бэкапами
        backup_buttons = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.load_backups)
        backup_buttons.addWidget(refresh_btn)

        create_btn = QPushButton("➕ Создать бэкап")
        create_btn.clicked.connect(self.create_backup)
        create_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        backup_buttons.addWidget(create_btn)

        left_layout.addLayout(backup_buttons)

        splitter.addWidget(left_widget)

        # Правая часть - детали бэкапа
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        details_label = QLabel("📊 Детали бэкапа:")
        details_label.setFont(QFont("Arial", 12, QFont.Bold))
        right_layout.addWidget(details_label)

        self.backup_details = QTextEdit()
        self.backup_details.setReadOnly(True)
        self.backup_details.setStyleSheet("""
            QTextEdit {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                font-family: monospace;
            }
        """)
        right_layout.addWidget(self.backup_details)

        # Кнопки для выбранного бэкапа
        self.restore_btn = QPushButton("🔄 Восстановить")
        self.restore_btn.clicked.connect(self.restore_backup)
        self.restore_btn.setEnabled(False)
        self.restore_btn.setStyleSheet("background-color: #FF9800; color: white;")
        right_layout.addWidget(self.restore_btn)

        self.delete_btn = QPushButton("🗑️ Удалить")
        self.delete_btn.clicked.connect(self.delete_backup)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("background-color: #f44336; color: white;")
        right_layout.addWidget(self.delete_btn)

        splitter.addWidget(right_widget)
        splitter.setSizes([500, 400])

        layout.addWidget(splitter)

        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Настройки бэкапа
        settings_group = self.create_settings_group()
        layout.addWidget(settings_group)

        # Кнопки закрытия
        buttons_layout = QHBoxLayout()

        apply_btn = QPushButton("💾 Применить настройки")
        apply_btn.clicked.connect(self.apply_settings)
        buttons_layout.addWidget(apply_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def create_disk_info_group(self):
        """Создание группы с информацией о диске"""
        group = QGroupBox("💽 Информация о Яндекс.Диске")
        layout = QHBoxLayout(group)

        self.disk_info_label = QLabel("Загрузка информации...")
        self.disk_info_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.disk_info_label)

        layout.addStretch()

        return group

    def create_settings_group(self):
        """Создание группы с настройками"""
        group = QGroupBox("⚙️ Настройки автоматического бэкапа")
        layout = QFormLayout(group)

        self.auto_backup_check = QCheckBox("Автоматический бэкап")
        self.auto_backup_check.setChecked(backup_manager.settings['auto_backup'])
        layout.addRow(self.auto_backup_check)

        self.interval_combo = QComboBox()
        self.interval_combo.addItem("Каждый час", 1)
        self.interval_combo.addItem("Каждые 3 часа", 3)
        self.interval_combo.addItem("Каждые 6 часов", 6)
        self.interval_combo.addItem("Каждые 12 часов", 12)
        self.interval_combo.addItem("Раз в сутки", 24)

        # Устанавливаем текущий интервал
        current_interval = backup_manager.settings['backup_interval_hours']
        index = self.interval_combo.findData(current_interval)
        if index >= 0:
            self.interval_combo.setCurrentIndex(index)

        layout.addRow("Интервал:", self.interval_combo)

        self.keep_backups_combo = QComboBox()
        for i in [3, 5, 7, 10, 15, 30]:
            self.keep_backups_combo.addItem(str(i), i)

        # Устанавливаем текущее значение
        current_keep = backup_manager.settings['keep_last_backups']
        index = self.keep_backups_combo.findData(current_keep)
        if index >= 0:
            self.keep_backups_combo.setCurrentIndex(index)

        layout.addRow("Хранить бэкапов:", self.keep_backups_combo)

        self.backup_on_start_check = QCheckBox("Бэкап при запуске")
        self.backup_on_start_check.setChecked(backup_manager.settings['backup_on_start'])
        layout.addRow(self.backup_on_start_check)

        self.backup_on_exit_check = QCheckBox("Бэкап при выходе")
        self.backup_on_exit_check.setChecked(backup_manager.settings['backup_on_exit'])
        layout.addRow(self.backup_on_exit_check)

        return group

    def load_disk_info(self):
        """Загрузка информации о Яндекс.Диске"""
        try:
            info = backup_manager.get_disk_info()
            if info:
                total_gb = info['total_space'] / (1024 ** 3)
                used_gb = info['used_space'] / (1024 ** 3)
                free_gb = info['free_space'] / (1024 ** 3)

                used_percent = (used_gb / total_gb) * 100 if total_gb > 0 else 0

                disk_info = f"""
                💽 Яндекс.Диск:
                📊 Всего: {total_gb:.1f} ГБ
                📈 Использовано: {used_gb:.1f} ГБ ({used_percent:.1f}%)
                📉 Свободно: {free_gb:.1f} ГБ
                """

                self.disk_info_label.setText(disk_info)
        except Exception as e:
            self.disk_info_label.setText(f"❌ Ошибка загрузки информации: {str(e)}")

    def load_backups(self):
        """Загрузка списка бэкапов"""
        try:
            backups = backup_manager.get_backup_list()

            self.backups_table.setRowCount(len(backups))
            self.selected_backup = None

            for row, backup in enumerate(backups):
                # Имя файла
                name_item = QTableWidgetItem(backup['name'])
                self.backups_table.setItem(row, 0, name_item)

                # Размер
                size_mb = backup['size'] / (1024 * 1024)
                size_item = QTableWidgetItem(f"{size_mb:.1f} МБ")
                self.backups_table.setItem(row, 1, size_item)

                # Дата и время
                modified = backup['modified']
                if isinstance(modified, str):
                    dt = datetime.fromisoformat(modified.replace('Z', '+00:00'))
                else:
                    dt = modified

                date_item = QTableWidgetItem(dt.strftime("%d.%m.%Y"))
                self.backups_table.setItem(row, 2, date_item)

                time_item = QTableWidgetItem(dt.strftime("%H:%M:%S"))
                self.backups_table.setItem(row, 3, time_item)

                # Действия
                actions_item = QTableWidgetItem("Нажмите для выбора")
                actions_item.setForeground(QColor("#2196F3"))
                self.backups_table.setItem(row, 4, actions_item)

            # Сбрасываем выбранный бэкап
            self.selected_backup = None
            self.restore_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.backup_details.setText("Выберите бэкап для просмотра деталей")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список бэкапов: {str(e)}")

    def on_backup_cell_clicked(self, row, column):
        """Обработка выбора бэкапа"""
        if column == 4:  # Колонка "Действия"
            backup_name = self.backups_table.item(row, 0).text()
            self.select_backup(backup_name, row)

    def select_backup(self, backup_name, row):
        """Выбор бэкапа для операций"""
        self.selected_backup = backup_name

        # Выделяем строку
        for col in range(self.backups_table.columnCount()):
            item = self.backups_table.item(row, col)
            if item:
                item.setBackground(QColor("#E3F2FD"))

        # Включаем кнопки
        self.restore_btn.setEnabled(True)
        self.delete_btn.setEnabled(True)

        # Загружаем детали
        self.load_backup_details(backup_name)

    def load_backup_details(self, backup_name):
        """Загрузка деталей выбранного бэкапа"""
        try:
            info = backup_manager.get_backup_info(backup_name)

            if info:
                details = f"""
📋 **Информация о бэкапе:**
├─ 📄 Имя: {info['name']}
├─ 📏 Размер: {info['size'] / (1024 * 1024):.1f} МБ
├─ 📅 Создан: {info['created']}
├─ ✏️ Изменен: {info['modified']}

📊 **Метаданные:**
"""

                metadata = info.get('metadata', {})
                for key, value in metadata.items():
                    if key == 'backup_date':
                        try:
                            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            value = dt.strftime("%d.%m.%Y %H:%M:%S")
                        except:
                            pass

                    details += f"├─ {key}: {value}\n"

                self.backup_details.setText(details)
            else:
                self.backup_details.setText("Информация о бэкапе не найдена")

        except Exception as e:
            self.backup_details.setText(f"❌ Ошибка загрузки деталей: {str(e)}")

    def create_backup(self):
        """Создание нового бэкапа"""
        reply = QMessageBox.question(
            self, "Создание бэкапа",
            "Создать новый бэкап базы данных?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Показываем прогресс бар
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Неопределенный прогресс

            def backup_thread():
                try:
                    backup_name = backup_manager.create_backup(
                        "Ручное создание бэкапа"
                    )

                    if backup_name:
                        self.backup_created.emit(backup_name)

                        # Обновляем UI в основном потоке
                        self.load_backups()

                        QMessageBox.information(
                            self, "Успех",
                            f"Бэкап создан успешно!\nИмя файла: {backup_name}"
                        )
                    else:
                        QMessageBox.warning(
                            self, "Ошибка",
                            "Не удалось создать бэкап!"
                        )

                except Exception as e:
                    QMessageBox.critical(
                        self, "Ошибка",
                        f"Ошибка при создании бэкапа: {str(e)}"
                    )

                finally:
                    # Скрываем прогресс бар
                    self.progress_bar.setVisible(False)

            # Запускаем в отдельном потоке
            threading.Thread(target=backup_thread, daemon=True).start()

    def restore_backup(self):
        """Восстановление из бэкапа"""
        if not self.selected_backup:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите бэкап!")
            return

        reply = QMessageBox.warning(
            self, "Восстановление",
            f"Восстановить базу данных из бэкапа:\n{self.selected_backup}?\n\n"
            "⚠️ ВНИМАНИЕ: Текущая база данных будет заменена!",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Показываем прогресс бар
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)

            def restore_thread():
                try:
                    success, error_msg = backup_manager.restore_backup(self.selected_backup)

                    if success:
                        self.backup_restored.emit(self.selected_backup)

                        QMessageBox.information(
                            self, "Успех",
                            f"База данных восстановлена из бэкапа!\n{self.selected_backup}\n\n"
                            "Приложение будет перезапущено для применения изменений."
                        )

                        # Закрываем диалог
                        self.accept()

                        # Закрываем основное окно приложения
                        if self.parent():
                            self.parent().close()
                    else:
                        QMessageBox.warning(
                            self, "Ошибка",
                            f"Не удалось восстановить базу данных!\n{error_msg}"
                        )

                except Exception as e:
                    QMessageBox.critical(
                        self, "Ошибка",
                        f"Ошибка при восстановлении: {str(e)}"
                    )

                finally:
                    # Скрываем прогресс бар
                    self.progress_bar.setVisible(False)

            # Запускаем в отдельном потоке
            threading.Thread(target=restore_thread, daemon=True).start()

    def delete_backup(self):
        """Удаление бэкапа"""
        if not self.selected_backup:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите бэкап!")
            return

        reply = QMessageBox.warning(
            self, "Удаление",
            f"Удалить бэкап:\n{self.selected_backup}?\n\n"
            "Это действие нельзя отменить!",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Используем yadisk_backup напрямую
                from yadisk_backup import yadisk_backup

                # Удаляем файл с Яндекс.Диска
                remote_path = f"{yadisk_backup.app_folder}/{self.selected_backup}"

                if yadisk_backup.disk.exists(remote_path):
                    yadisk_backup.disk.remove(remote_path, permanently=True)

                    QMessageBox.information(
                        self, "Успех",
                        f"Бэкап удален: {self.selected_backup}"
                    )

                    # Обновляем список
                    self.load_backups()
                else:
                    QMessageBox.warning(
                        self, "Ошибка",
                        "Бэкап не найден на Яндекс.Диске!"
                    )

            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка",
                    f"Ошибка при удалении бэкапа: {str(e)}"
                )

    def apply_settings(self):
        """Применение настроек"""
        try:
            settings = {
                'auto_backup': self.auto_backup_check.isChecked(),
                'backup_interval_hours': self.interval_combo.currentData(),
                'keep_last_backups': self.keep_backups_combo.currentData(),
                'backup_on_start': self.backup_on_start_check.isChecked(),
                'backup_on_exit': self.backup_on_exit_check.isChecked()
            }

            backup_manager.update_settings(**settings)

            QMessageBox.information(
                self, "Настройки применены",
                "Настройки бэкапов успешно обновлены!"
            )

        except Exception as e:
            QMessageBox.critical(
                self, "Ошибка",
                f"Ошибка применения настроек: {str(e)}"
            )

    def closeEvent(self, event):
        """Обработка закрытия диалога"""
        self.update_timer.stop()
        event.accept()