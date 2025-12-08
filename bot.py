import telebot
from telebot import types
from sqlalchemy.orm import Session
from models import User, Transaction, Wallet, Commission, Exchange, ExchangeStatus, TransactionType
from database import db
from crypto_manager import crypto_manager
from datetime import datetime
import logging
import time


class TelegramBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.setup_handlers()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        print("🤖 Telegram бот инициализирован")

    def setup_handlers(self):
        """Настройка обработчиков команд"""

        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            chat_id = message.chat.id
            user_id = message.from_user.id

            session = db.get_session()
            try:
                user = session.query(User).filter_by(telegram_id=str(user_id)).first()
                if user:
                    self.bot.send_message(
                        chat_id,
                        "✅ Ваш Telegram аккаунт привязан к крипто-кошельку!\n\n"
                        "Доступные команды:\n"
                        "/balance - Посмотреть баланс\n"
                        "/transactions - История операций\n"
                        "/rates - Текущие курсы\n"
                        "/help - Помощь"
                    )
                else:
                    self.bot.send_message(
                        chat_id,
                        f"🔗 Ваш ID для привязки: `{user_id}`\n\n"
                        "Чтобы привязать аккаунт, используйте этот ID в демо-скрипте",
                        parse_mode='Markdown'
                    )
            finally:
                session.close()

        @self.bot.message_handler(commands=['balance'])
        def balance_command(message):
            chat_id = message.chat.id
            user_id = message.from_user.id

            session = db.get_session()
            try:
                user = session.query(User).filter_by(telegram_id=str(user_id)).first()
                if user:
                    wallets = session.query(Wallet).filter_by(user_id=user.id).all()

                    balance_text = "💰 **Ваш баланс:**\n\n"
                    total_usdt = 0

                    for wallet in wallets:
                        # Получаем реальный курс из базы
                        usdt_value = crypto_manager.convert_to_usdt(wallet.currency.code, wallet.balance)
                        total_usdt += usdt_value
                        balance_text += f"• {wallet.currency.code}: {wallet.balance:.6f} (${usdt_value:.2f})\n"

                    balance_text += f"\n💵 **Общий баланс: ${total_usdt:.2f}**"

                    self.bot.send_message(chat_id, balance_text, parse_mode='Markdown')
                else:
                    self.bot.send_message(chat_id, "❌ Аккаунт не привязан. Используйте /start")
            finally:
                session.close()

        @self.bot.message_handler(commands=['rates'])
        def rates_command(message):
            """Показать текущие курсы валют"""
            chat_id = message.chat.id

            try:
                rates = crypto_manager.get_all_rates()
                rates_text = "📈 **Текущие курсы к USDT:**\n\n"

                for currency_code, rate in sorted(rates.items()):
                    if currency_code != 'USDT':  # USDT всегда 1:1
                        rates_text += f"• 1 {currency_code} = ${rate:.2f}\n"

                rates_text += "\n• 1 USDT = $1.00"

                self.bot.send_message(chat_id, rates_text, parse_mode='Markdown')
            except Exception as e:
                self.bot.send_message(chat_id, "❌ Ошибка получения курсов")

        @self.bot.message_handler(commands=['transactions'])
        def transactions_command(message):
            chat_id = message.chat.id
            user_id = message.from_user.id

            session = db.get_session()
            try:
                user = session.query(User).filter_by(telegram_id=str(user_id)).first()
                if user:
                    transactions = session.query(Transaction).filter(
                        (Transaction.user_id_from == user.id) |
                        (Transaction.user_id_to == user.id)
                    ).order_by(Transaction.created_date.desc()).limit(10).all()

                    if transactions:
                        transactions_text = "📊 **Последние операции:**\n\n"
                        for tx in transactions:
                            direction = "➡️ Отправка" if tx.user_id_from == user.id else "⬅️ Получение"
                            other_user = tx.user_from if tx.user_id_to == user.id else tx.user_to
                            usdt_value = crypto_manager.convert_to_usdt(tx.currency_rel.code, tx.amount)

                            transactions_text += f"• {direction}: {tx.amount:.6f} {tx.currency_rel.code} (${usdt_value:.2f})\n"
                            transactions_text += f"  👤 {other_user.full_name}\n"
                            transactions_text += f"  📊 Статус: {tx.status}\n"
                            transactions_text += f"  📅 {tx.created_date.strftime('%d.%m %H:%M')}\n\n"
                    else:
                        transactions_text = "📭 Операций пока нет"

                    self.bot.send_message(chat_id, transactions_text, parse_mode='Markdown')
                else:
                    self.bot.send_message(chat_id, "❌ Аккаунт не привязан")
            finally:
                session.close()

        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            help_text = """
🤖 **Крипто Бот - Демо версия**

Доступные команды:
/start - Начало работы
/balance - Баланс кошельков  
/transactions - История операций
/rates - Текущие курсы валют
/help - Эта справка

Для тестирования функций используйте демо-скрипт.
            """
            self.bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

        @self.bot.callback_query_handler(func=lambda call: True)
        def callback_handler(call):
            self.handle_callback(call)

    def handle_callback(self, call):
        """Обработка нажатий на кнопки"""
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        data = call.data

        try:
            if data.startswith('confirm_'):
                transaction_id = int(data.split('_')[1])
                self.confirm_transaction(chat_id, message_id, transaction_id, call.id)

            elif data.startswith('cancel_'):
                transaction_id = int(data.split('_')[1])
                self.cancel_transaction(chat_id, message_id, transaction_id, call.id)

        except Exception as e:
            logging.error(f"Error handling callback: {e}")
            try:
                self.bot.answer_callback_query(call.id, "❌ Произошла ошибка")
            except:
                pass

    def confirm_transaction(self, chat_id, message_id, transaction_id, callback_id):
        """Подтверждение транзакции"""
        session = db.get_session()
        try:
            transaction = session.query(Transaction).get(transaction_id)
            if not transaction:
                self.bot.answer_callback_query(callback_id, "❌ Транзакция не найдена")
                return

            if transaction.status != 'pending':
                self.bot.answer_callback_query(callback_id, "❌ Транзакция уже обработана")
                return

            # Обновляем статус транзакции
            transaction.status = 'completed'

            # Обновляем балансы
            from_wallet = session.query(Wallet).filter_by(
                user_id=transaction.user_id_from,
                currency_id=transaction.currency_id
            ).first()

            to_wallet = session.query(Wallet).filter_by(
                user_id=transaction.user_id_to,
                currency_id=transaction.currency_id
            ).first()

            if from_wallet and to_wallet:
                commission = transaction.amount * 0.01
                total_amount = transaction.amount + commission

                if from_wallet.balance >= total_amount:
                    from_wallet.balance -= total_amount
                    to_wallet.balance += transaction.amount

                    # Сохраняем комиссию
                    commission_record = Commission(
                        transaction_id=transaction.id,
                        amount=commission,
                        type='transfer'
                    )
                    session.add(commission_record)

                    session.commit()

                    # Обновляем сообщение
                    try:
                        self.bot.edit_message_text(
                            "✅ **Перевод подтвержден**\n\n"
                            f"💸 Сумма: {transaction.amount:.6f}\n"
                            f"👤 Получатель: {transaction.user_to.full_name}\n"
                            f"💰 Комиссия: {commission:.6f}\n"
                            f"🆔 Транзакция: #{transaction.id}",
                            chat_id=chat_id,
                            message_id=message_id,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logging.warning(f"Could not edit message: {e}")

                    self.bot.answer_callback_query(callback_id, "✅ Перевод выполнен")

                    # Уведомляем получателя
                    if transaction.user_to.telegram_id:
                        self.send_notification(
                            transaction.user_to.telegram_id,
                            f"💰 Вы получили перевод: {transaction.amount:.6f} "
                            f"от {transaction.user_from.full_name}"
                        )
                else:
                    transaction.status = 'failed'
                    session.commit()
                    self.bot.answer_callback_query(callback_id, "❌ Недостаточно средств")
            else:
                transaction.status = 'failed'
                session.commit()
                self.bot.answer_callback_query(callback_id, "❌ Ошибка кошельков")

        except Exception as e:
            session.rollback()
            logging.error(f"Error confirming transaction: {e}")
            try:
                self.bot.answer_callback_query(callback_id, "❌ Ошибка при подтверждении")
            except:
                pass
        finally:
            session.close()

    def cancel_transaction(self, chat_id, message_id, transaction_id, callback_id):
        """Отмена транзакции"""
        session = db.get_session()
        try:
            transaction = session.query(Transaction).get(transaction_id)
            if transaction and transaction.status == 'pending':
                transaction.status = 'cancelled'
                session.commit()

                try:
                    self.bot.edit_message_text(
                        "❌ **Перевод отменен**\n\n"
                        f"Транзакция #{transaction_id} отменена.",
                        chat_id=chat_id,
                        message_id=message_id,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logging.warning(f"Could not edit message: {e}")

                self.bot.answer_callback_query(callback_id, "❌ Перевод отменен")
            else:
                self.bot.answer_callback_query(callback_id, "❌ Транзакция не найдена")

        except Exception as e:
            session.rollback()
            logging.error(f"Error cancelling transaction: {e}")
            try:
                self.bot.answer_callback_query(callback_id, "❌ Ошибка при отмене")
            except:
                pass
        finally:
            session.close()

    def send_confirmation_request(self, user_telegram_id, transaction):
        """Отправка запроса на подтверждение перевода"""
        try:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.row(
                types.InlineKeyboardButton(
                    "✅ Подтвердить",
                    callback_data=f"confirm_{transaction.id}"
                ),
                types.InlineKeyboardButton(
                    "❌ Отменить",
                    callback_data=f"cancel_{transaction.id}"
                )
            )

            message = (
                "🔐 **Требуется подтверждение перевода**\n\n"
                f"💸 Сумма: `{transaction.amount:.6f}` {transaction.currency_rel.code}\n"
                f"👤 Получатель: {transaction.user_to.full_name}\n"
                f"📧 Телефон: {transaction.user_to.phone}\n"
                f"💳 Комиссия: {transaction.amount * 0.01:.6f} (1%)\n\n"
                f"🆔 Транзакция: #{transaction.id}"
            )

            self.bot.send_message(
                user_telegram_id,
                message,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            return True

        except Exception as e:
            logging.error(f"Error sending confirmation: {e}")
            return False

    def send_notification(self, user_telegram_id, message):
        """Отправка уведомления пользователю"""
        try:
            self.bot.send_message(user_telegram_id, message)
            return True
        except Exception as e:
            logging.error(f"Error sending notification: {e}")
            return False

    def link_telegram_account(self, user_id, telegram_id):
        """Привязка Telegram аккаунта к пользователю"""
        session = db.get_session()
        try:
            user = session.query(User).get(user_id)
            if user:
                user.telegram_id = str(telegram_id)
                session.commit()

                self.send_notification(
                    telegram_id,
                    "✅ Ваш Telegram аккаунт успешно привязан к крипто-кошельку!\n\n"
                    "Теперь вы будете получать уведомления о операциях.\n"
                    "Используйте /balance для просмотра баланса."
                )
                return True
            return False
        except Exception as e:
            session.rollback()
            logging.error(f"Error linking telegram account: {e}")
            return False
        finally:
            session.close()

    def run(self):
        """Запуск бота"""
        logging.info("Telegram бот запущен...")
        print("Бот запущен. Нажмите Ctrl+C для остановки.")
        try:
            self.bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            logging.error(f"Bot polling error: {e}")
            time.sleep(5)
            self.run()


# Создаем экземпляр бота
telegram_bot = TelegramBot("6847168416:AAEVe2HNzr0Kini3d2nYriFvCgWO5yf67oQ")