from sqlalchemy.orm import Session
from contextlib import contextmanager
from database import db
import logging

logger = logging.getLogger(__name__)


@contextmanager
def transaction_session():
    """Контекстный менеджер для транзакций"""
    session = db.get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Transaction failed: {e}")
        raise
    finally:
        session.close()


def execute_in_transaction(func, *args, **kwargs):
    """Выполнить функцию в транзакции"""
    with transaction_session() as session:
        return func(session, *args, **kwargs)


def register_user_transaction(session, phone, full_name, telegram_id):
    """Регистрация пользователя в транзакции"""
    from models import User, Wallet, Currency, UserInterface

    # Проверяем существование пользователя
    existing_user = session.query(User).filter_by(phone=phone).first()
    if existing_user:
        raise ValueError("Пользователь с таким телефоном уже существует")

    # Проверяем Telegram ID
    existing_tg_user = session.query(User).filter_by(telegram_id=telegram_id).first()
    if existing_tg_user:
        raise ValueError("Telegram ID уже привязан к другому аккаунту")

    # Создаем пользователя
    user = User(
        phone=phone,
        full_name=full_name,
        telegram_id=telegram_id
    )
    session.add(user)
    session.flush()

    # Создаем кошельки для всех валют
    currencies = session.query(Currency).all()
    for currency in currencies:
        wallet = Wallet(
            user_id=user.id,
            currency_id=currency.id,
            address=f"{currency.code}_address_{user.id}_{currency.id}",
            balance=10.0
        )
        session.add(wallet)

    # Создаем настройки интерфейса
    ui_settings = UserInterface(user_id=user.id)
    session.add(ui_settings)

    return user.id