from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor


class BalanceWidget(QWidget):
    def __init__(self, currency, balance, usd_balance, parent=None):
        super().__init__(parent)
        self.init_ui(currency, balance, usd_balance)

    def init_ui(self, currency, balance, usd_balance):
        layout = QHBoxLayout()

        # Валюта
        currency_label = QLabel(currency)
        currency_label.setFont(QFont("Arial", 12, QFont.Bold))
        currency_label.setFixedWidth(80)

        # Баланс
        balance_label = QLabel(f"{balance:.8f}")
        balance_label.setFont(QFont("Arial", 11))

        # В USD
        usd_label = QLabel(f"${usd_balance:.2f}")
        usd_label.setFont(QFont("Arial", 10))
        usd_label.setStyleSheet("color: #666;")
        usd_label.setAlignment(Qt.AlignRight)

        layout.addWidget(currency_label)
        layout.addWidget(balance_label)
        layout.addStretch()
        layout.addWidget(usd_label)

        self.setLayout(layout)