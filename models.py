from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class TransactionType(enum.Enum):
    TRANSFER = "TRANSFER"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    EXCHANGE = "EXCHANGE"


class ExchangeStatus(enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class UserStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"


class UserRole(enum.Enum):
    """Роли пользователей в системе"""
    USER = "USER"  # Обычный пользователь
    MODERATOR = "MODERATOR"  # Модератор
    ADMIN = "ADMIN"  # Администратор


class SessionStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    LOGGED_OUT = "LOGGED_OUT"


class Theme(enum.Enum):
    LIGHT = "light"
    DARK = "dark"
    BLUE = "blue"
    GREEN = "green"
    PURPLE = "purple"
    ORANGE = "orange"
    MODERN = "modern"


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    role = Column(Enum(UserRole), default=UserRole.USER)  # Изменено с two_factor_enabled на role
    registration_date = Column(DateTime, default=func.now())
    last_login = Column(DateTime)
    telegram_id = Column(String(50), unique=True)

    # Relationships
    wallets = relationship("Wallet", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    sent_transactions = relationship("Transaction", foreign_keys="Transaction.user_id_from", back_populates="user_from")
    received_transactions = relationship("Transaction", foreign_keys="Transaction.user_id_to", back_populates="user_to")
    notifications = relationship("Notification", back_populates="user")
    sent_exchanges = relationship("Exchange", foreign_keys="Exchange.user_id_from", back_populates="user_from")
    received_exchanges = relationship("Exchange", foreign_keys="Exchange.user_id_to", back_populates="user_to")
    interface = relationship("UserInterface", uselist=False, back_populates="user")

    def has_telegram_linked(self):
        return bool(self.telegram_id)

    def can_receive_notifications(self):
        return bool(self.telegram_id)

    def is_admin(self):
        return self.role == UserRole.ADMIN

    def is_moderator(self):
        return self.role == UserRole.MODERATOR

    def is_user(self):
        return self.role == UserRole.USER

    def get_role_display(self):
        """Получить отображаемое название роли"""
        role_names = {
            UserRole.USER: "Пользователь",
            UserRole.MODERATOR: "Модератор",
            UserRole.ADMIN: "Администратор"
        }
        return role_names.get(self.role, "Пользователь")

class Session(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    created_date = Column(DateTime, default=func.now())
    last_activity = Column(DateTime, default=func.now())
    status = Column(Enum(SessionStatus), default=SessionStatus.ACTIVE)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    token = Column(String(255))

    # Relationships
    user = relationship("User", back_populates="sessions")


class Currency(Base):
    __tablename__ = 'currencies'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    min_deposit = Column(Float, default=0.0)
    min_withdrawal = Column(Float, default=0.0)

    # Relationships
    wallets = relationship("Wallet", back_populates="currency")
    exchange_rates = relationship("ExchangeRate", back_populates="currency")


class Wallet(Base):
    __tablename__ = 'wallets'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    currency_id = Column(Integer, ForeignKey('currencies.id'))
    address = Column(String(255), unique=True, nullable=False)
    balance = Column(Float, default=0.0)

    # Relationships
    user = relationship("User", back_populates="wallets")
    currency = relationship("Currency", back_populates="wallets")


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    type = Column(Enum(TransactionType), nullable=False)
    user_id_from = Column(Integer, ForeignKey('users.id'))
    user_id_to = Column(Integer, ForeignKey('users.id'))
    amount = Column(Float, nullable=False)
    currency_id = Column(Integer, ForeignKey('currencies.id'))
    created_date = Column(DateTime, default=func.now())
    status = Column(String(20), default='pending')

    # Relationships
    user_from = relationship("User", foreign_keys=[user_id_from], back_populates="sent_transactions")
    user_to = relationship("User", foreign_keys=[user_id_to], back_populates="received_transactions")
    currency_rel = relationship("Currency")
    commission = relationship("Commission", uselist=False, back_populates="transaction")
    notifications = relationship("Notification", back_populates="transaction")

    def requires_confirmation(self):
        return self.amount > 0.1

    def can_be_confirmed(self):
        return self.status == 'pending'


class Exchange(Base):
    __tablename__ = 'exchanges'

    id = Column(Integer, primary_key=True)
    user_id_from = Column(Integer, ForeignKey('users.id'))
    user_id_to = Column(Integer, ForeignKey('users.id'))
    currency_from_id = Column(Integer, ForeignKey('currencies.id'))
    currency_to_id = Column(Integer, ForeignKey('currencies.id'))
    amount_from = Column(Float, nullable=False)
    amount_to = Column(Float, nullable=False)
    status = Column(Enum(ExchangeStatus), default=ExchangeStatus.PENDING)
    created_date = Column(DateTime, default=func.now())
    completed_date = Column(DateTime)

    # Relationships
    user_from = relationship("User", foreign_keys=[user_id_from], back_populates="sent_exchanges")
    user_to = relationship("User", foreign_keys=[user_id_to], back_populates="received_exchanges")
    currency_from = relationship("Currency", foreign_keys=[currency_from_id])
    currency_to = relationship("Currency", foreign_keys=[currency_to_id])
    notifications = relationship("Notification", back_populates="exchange")


class Commission(Base):
    __tablename__ = 'commissions'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey('transactions.id'))
    amount = Column(Float, nullable=False)
    type = Column(String(50))

    # Relationships
    transaction = relationship("Transaction", back_populates="commission")


class ExchangeRate(Base):
    __tablename__ = 'exchange_rates'

    id = Column(Integer, primary_key=True)
    currency_id = Column(Integer, ForeignKey('currencies.id'))
    rate_to_usdt = Column(Float, nullable=False)
    last_updated = Column(DateTime, default=func.now())

    # Relationships
    currency = relationship("Currency", back_populates="exchange_rates")


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False)  # transaction, exchange, system, security
    user_id = Column(Integer, ForeignKey('users.id'))
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=True)
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    created_date = Column(DateTime, default=func.now())
    is_read = Column(Boolean, default=False)
    priority = Column(Integer, default=1)  # 1-low, 2-medium, 3-high

    # Relationships
    user = relationship("User", back_populates="notifications")
    transaction = relationship("Transaction", back_populates="notifications")
    exchange = relationship("Exchange", back_populates="notifications")


class UserInterface(Base):
    __tablename__ = 'user_interface'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    theme = Column(Enum(Theme), default=Theme.LIGHT)
    language = Column(String(10), default='ru')
    notifications_enabled = Column(Boolean, default=True)
    auto_login = Column(Boolean, default=False)
    font_size = Column(Integer, default=12)
    primary_color = Column(String(7), default='#2E8B57')  # SeaGreen
    secondary_color = Column(String(7), default='#4682B4')  # SteelBlue
    background_color = Column(String(7), default='#FFFFFF')  # White
    text_color = Column(String(7), default='#333333')  # Dark Gray

    # Relationships
    user = relationship("User", back_populates="interface")