from sqlalchemy.orm import Session
from models import ExchangeRate, Currency, Wallet
from database import db
from datetime import datetime
import random


class CryptoManager:
    def __init__(self):
        self.base_rates = {
            'BTC': 85000.0,
            'ETH': 3000.0,
            'TON': 5.5,
            'USDT': 1.0,
            'BNB': 400.0,
            'SOL': 120.0,
            'XRP': 0.6,
            'ADA': 0.5,
            'DOGE': 0.1,
            'DOT': 7.0
        }
        self.current_rates = self.base_rates.copy()

    def initialize_currencies(self):
        """Инициализация криптовалют в базе данных"""
        session = db.get_session()
        try:
            currencies_data = [
                {'name': 'Bitcoin', 'code': 'BTC', 'min_deposit': 0.0001, 'min_withdrawal': 0.0002},
                {'name': 'Ethereum', 'code': 'ETH', 'min_deposit': 0.001, 'min_withdrawal': 0.002},
                {'name': 'Toncoin', 'code': 'TON', 'min_deposit': 0.1, 'min_withdrawal': 0.2},
                {'name': 'Tether', 'code': 'USDT', 'min_deposit': 1.0, 'min_withdrawal': 2.0},
                {'name': 'Binance Coin', 'code': 'BNB', 'min_deposit': 0.01, 'min_withdrawal': 0.02},
                {'name': 'Solana', 'code': 'SOL', 'min_deposit': 0.01, 'min_withdrawal': 0.02},
                {'name': 'Ripple', 'code': 'XRP', 'min_deposit': 1.0, 'min_withdrawal': 2.0},
                {'name': 'Cardano', 'code': 'ADA', 'min_deposit': 1.0, 'min_withdrawal': 2.0},
                {'name': 'Dogecoin', 'code': 'DOGE', 'min_deposit': 1.0, 'min_withdrawal': 2.0},
                {'name': 'Polkadot', 'code': 'DOT', 'min_deposit': 0.1, 'min_withdrawal': 0.2},
            ]

            for currency_data in currencies_data:
                currency = session.query(Currency).filter_by(code=currency_data['code']).first()
                if not currency:
                    currency = Currency(**currency_data)
                    session.add(currency)
                    print(f"✅ Добавлена валюта: {currency_data['name']} ({currency_data['code']})")

            session.commit()

            # Теперь инициализируем курсы валют
            self.initialize_exchange_rates()
            print("✅ Все валюты и курсы инициализированы")

        except Exception as e:
            print(f"❌ Ошибка инициализации валют: {e}")
            session.rollback()
        finally:
            session.close()

    def initialize_exchange_rates(self):
        """Инициализация курсов валют"""
        session = db.get_session()
        try:
            for currency_code, rate in self.base_rates.items():
                currency = session.query(Currency).filter_by(code=currency_code).first()
                if currency:
                    exchange_rate = session.query(ExchangeRate).filter_by(currency_id=currency.id).first()
                    if not exchange_rate:
                        exchange_rate = ExchangeRate(
                            currency_id=currency.id,
                            rate_to_usdt=rate
                        )
                        session.add(exchange_rate)
                        print(f"✅ Курс {currency_code}: 1 {currency_code} = {rate:.2f} USDT")

            session.commit()
        except Exception as e:
            print(f"❌ Ошибка инициализации курсов: {e}")
            session.rollback()
        finally:
            session.close()

    def update_exchange_rates(self):
        """Обновление курсов валют"""
        session = db.get_session()
        try:
            for currency_code, base_rate in self.base_rates.items():
                change_percent = random.uniform(-0.05, 0.05)
                current_rate = base_rate * (1 + change_percent)
                self.current_rates[currency_code] = current_rate

                currency = session.query(Currency).filter_by(code=currency_code).first()
                if currency:
                    exchange_rate = session.query(ExchangeRate).filter_by(currency_id=currency.id).first()
                    if exchange_rate:
                        exchange_rate.rate_to_usdt = current_rate
                        exchange_rate.last_updated = datetime.now()
                    else:
                        exchange_rate = ExchangeRate(
                            currency_id=currency.id,
                            rate_to_usdt=current_rate
                        )
                        session.add(exchange_rate)

            session.commit()
            print("✅ Курсы валют обновлены")

        except Exception as e:
            print(f"❌ Ошибка обновления курсов: {e}")
            session.rollback()
        finally:
            session.close()

    def get_exchange_rate(self, currency_code):
        """Получение текущего курса валюты"""
        session = db.get_session()
        try:
            currency = session.query(Currency).filter_by(code=currency_code).first()
            if currency:
                exchange_rate = session.query(ExchangeRate).filter_by(currency_id=currency.id).first()
                if exchange_rate:
                    return exchange_rate.rate_to_usdt
            return self.current_rates.get(currency_code, 1.0)
        except Exception as e:
            print(f"❌ Ошибка получения курса {currency_code}: {e}")
            return 1.0
        finally:
            session.close()

    def convert_to_usdt(self, currency_code, amount):
        """Конвертация суммы в USDT"""
        rate = self.get_exchange_rate(currency_code)
        return amount * rate

    def get_all_rates(self):
        """Получение всех курсов валют"""
        session = db.get_session()
        try:
            rates = {}
            exchange_rates = session.query(ExchangeRate).join(Currency).all()
            for er in exchange_rates:
                rates[er.currency.code] = er.rate_to_usdt
            return rates
        except Exception as e:
            print(f"❌ Ошибка получения курсов: {e}")
            return self.current_rates.copy()
        finally:
            session.close()


# Создаем экземпляр менеджера
crypto_manager = CryptoManager()