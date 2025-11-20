from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class TransactionType(enum.Enum):
    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


class UserStatus(enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"
    PENDING = "pending"


class SessionStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    phone = Column(String(20), unique=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.ACTIVE)
    registration_date = Column(DateTime, default=func.now())
    last_login = Column(DateTime)
    telegram_id = Column(String(50), unique=True)
    two_factor_enabled = Column(Boolean, default=False)

    # Relationships
    wallets = relationship("Wallet", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    sent_transactions = relationship("Transaction", foreign_keys="Transaction.user_id_from", back_populates="user_from")
    received_transactions = relationship("Transaction", foreign_keys="Transaction.user_id_to", back_populates="user_to")
    notifications = relationship("Notification", back_populates="user")

    def has_telegram_linked(self):
        return bool(self.telegram_id)

    def can_receive_notifications(self):
        return bool(self.telegram_id)


class Session(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    created_date = Column(DateTime, default=func.now())
    status = Column(Enum(SessionStatus), default=SessionStatus.PENDING)
    confirmation_code = Column(String(10))
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
    type = Column(String(50), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    transaction_id = Column(Integer, ForeignKey('transactions.id'), nullable=True)
    message = Column(Text, nullable=False)
    created_date = Column(DateTime, default=func.now())
    is_read = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="notifications")
    transaction = relationship("Transaction", back_populates="notifications")


class UserInterface(Base):
    __tablename__ = 'user_interface'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    theme = Column(String(20), default='light')
    language = Column(String(10), default='ru')
    notifications_enabled = Column(Boolean, default=True)

    # Relationships
    user = relationship("User")