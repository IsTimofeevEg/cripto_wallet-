import telebot
from telebot import types
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text
from models import User, Transaction, Wallet, Commission, Exchange, ExchangeStatus, TransactionType
from database import db
from datetime import datetime
import logging
import os
import time
import random


class TelegramBot:
    def __init__(self, token):
        self.bot = telebot.TeleBot(token)
        self.pending_confirmations = {}
        self.setup_handlers()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
                        "Вы будете получать уведомления о операциях.\n\n"
                        "Доступные команды:\n"
                        "/link - получить код привязки\n"
                        "/login - получить код для входа\n"
                        "/help - помощь"
                    )
                else:
                    self.bot.send_message(
                        chat_id,
                        f"🔗 Ваш ID для привязки: `{user_id}`\n\n"
                        "Скопируйте этот код в приложении в разделе 'Привязать Telegram'\n\n"
                        "Или используйте /login для получения кода входа",
                        parse_mode='Markdown'
                    )
            finally:
                session.close()

        @self.bot.message_handler(commands=['link'])
        def link_command(message):
            chat_id = message.chat.id
            user_id = message.from_user.id

            self.bot.send_message(
                chat_id,
                f"🔗 Ваш код для привязки: `{user_id}`\n\n"
                "Используйте этот код в приложении для привязки аккаунта.",
                parse_mode='Markdown'
            )

        @self.bot.message_handler(commands=['login'])
        def login_command(message):
            """Отправка кода подтверждения для входа"""
            chat_id = message.chat.id
            user_id = message.from_user.id

            session = db.get_session()
            try:
                user = session.query(User).filter_by(telegram_id=str(user_id)).first()
                if user:
                    # Генерируем код
                    code = str(random.randint(100000, 999999))

                    # Отправляем код
                    self.bot.send_message(
                        chat_id,
                        f"🔐 Ваш код для входа: `{code}`\n\n"
                        f"👤 Пользователь: {user.full_name}\n"
                        f"📱 Телефон: {user.phone}\n"
                        f"🕐 Время: {datetime.now().strftime('%H:%M:%S')}\n\n"
                        f"Код действителен 5 минут.\n"
                        f"*Не сообщайте этот код никому!*",
                        parse_mode='Markdown'
                    )

                    # Отправляем уведомление о попытке входа
                    self.bot.send_message(
                        chat_id,
                        f"⚠️ *Предупреждение безопасности*\n\n"
                        f"Запрос на вход в аккаунт:\n"
                        f"📍 IP: Неизвестен (через бота)\n"
                        f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                        f"Если это не вы, немедленно смените пароль и обратитесь в поддержку.",
                        parse_mode='Markdown'
                    )
                else:
                    self.bot.send_message(
                        chat_id,
                        "❌ Ваш Telegram не привязан к аккаунту.\n"
                        "Используйте код привязки из приложения или команду /link"
                    )
            finally:
                session.close()

        @self.bot.message_handler(commands=['help'])
        def help_command(message):
            help_text = (
                "🤖 *Crypto Wallet Bot - Помощь*\n\n"
                "Доступные команды:\n"
                "/start - Начало работы\n"
                "/link - Получить код для привязки аккаунта\n"
                "/login - Получить код для входа в приложение\n"
                "/help - Эта справка\n\n"
                "Бот используется для:\n"
                "• Подтверждения операций\n"
                "• Уведомлений о входах\n"
                "• Безопасной авторизации\n\n"
                "Все операции требуют подтверждения через этого бота."
            )
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
            # Проверяем время сообщения (не старше 2 минут)
            if time.time() - call.message.date > 120:
                self.bot.answer_callback_query(call.id, "❌ Время подтверждения истекло")
                return

            if data.startswith('confirm_'):
                transaction_id = int(data.split('_')[1])
                self.confirm_transaction(chat_id, message_id, transaction_id, call.id)

            elif data.startswith('cancel_'):
                transaction_id = int(data.split('_')[1])
                self.cancel_transaction(chat_id, message_id, transaction_id, call.id)

            elif data.startswith('exchange_accept_'):
                exchange_id = int(data.split('_')[2])
                self.accept_exchange(chat_id, message_id, exchange_id, call.id)

            elif data.startswith('exchange_reject_'):
                exchange_id = int(data.split('_')[2])
                self.reject_exchange(chat_id, message_id, exchange_id, call.id)

        except Exception as e:
            logging.error(f"Error handling callback: {e}")
            try:
                self.bot.answer_callback_query(call.id, "❌ Произошла ошибка")
            except:
                pass

    def confirm_transaction(self, chat_id, message_id, transaction_id, callback_id):
        """Подтверждение транзакции с использованием транзакции БД"""
        session = db.get_session()
        try:
            # Начинаем транзакцию
            session.begin()

            # Блокируем строки для обновления
            transaction = (session.query(Transaction)
                           .with_for_update()
                           .options(
                joinedload(Transaction.user_from),
                joinedload(Transaction.user_to),
                joinedload(Transaction.currency_rel)
            )
                           .filter_by(id=transaction_id)
                           .first())

            if not transaction:
                session.rollback()
                self.bot.answer_callback_query(callback_id, "❌ Транзакция не найдена")
                return

            if transaction.status != 'pending':
                session.rollback()
                self.bot.answer_callback_query(callback_id, "❌ Транзакция уже обработана")
                return

            # Блокируем кошельки для обновления
            from_wallet = (session.query(Wallet)
                           .with_for_update()
                           .filter_by(
                user_id=transaction.user_id_from,
                currency_id=transaction.currency_id
            ).first())

            to_wallet = (session.query(Wallet)
                         .with_for_update()
                         .filter_by(
                user_id=transaction.user_id_to,
                currency_id=transaction.currency_id
            ).first())

            if not from_wallet or not to_wallet:
                session.rollback()
                self.bot.answer_callback_query(callback_id, "❌ Ошибка кошельков")
                return

            # Проверяем балансы внутри транзакции
            commission = transaction.amount * 0.01
            total_amount = transaction.amount + commission

            if from_wallet.balance < total_amount:
                transaction.status = 'failed'
                session.commit()
                self.bot.answer_callback_query(callback_id, "❌ Недостаточно средств")
                return

            # Выполняем перевод
            from_wallet.balance -= total_amount
            to_wallet.balance += transaction.amount
            transaction.status = 'completed'

            # Сохраняем комиссию
            commission_record = Commission(
                transaction_id=transaction.id,
                amount=commission,
                type='transfer'
            )
            session.add(commission_record)

            # Создаем уведомления
            db.create_notification(
                user_id=transaction.user_id_from,
                type='transaction',
                title='Перевод подтвержден',
                message=f'Ваш перевод на сумму {transaction.amount:.6f} {transaction.currency_rel.code} подтвержден',
                transaction_id=transaction.id,
                priority=2
            )

            db.create_notification(
                user_id=transaction.user_id_to,
                type='transaction',
                title='Получен перевод',
                message=f'Вы получили перевод {transaction.amount:.6f} {transaction.currency_rel.code} от {transaction.user_from.full_name}',
                transaction_id=transaction.id,
                priority=2
            )

            # Фиксируем транзакцию
            session.commit()

            # Обновляем сообщение
            try:
                self.bot.edit_message_text(
                    "✅ **Перевод выполнен успешно**\n\n"
                    f"💸 Сумма: {transaction.amount:.6f} {transaction.currency_rel.code}\n"
                    f"👤 Отправитель: {transaction.user_from.full_name}\n"
                    f"👤 Получатель: {transaction.user_to.full_name}\n"
                    f"💰 Комиссия: {commission:.6f} {transaction.currency_rel.code}\n"
                    f"🆔 Транзакция: #{transaction.id}\n\n"
                    f"📊 Баланс списан: {total_amount:.6f}",
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
                    f"💰 Получен перевод!\n\n"
                    f"Сумма: {transaction.amount:.6f} {transaction.currency_rel.code}\n"
                    f"От: {transaction.user_from.full_name}\n"
                    f"Транзакция: #{transaction.id}"
                )

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
            session.begin()

            transaction = (session.query(Transaction)
                           .with_for_update()
                           .filter_by(id=transaction_id)
                           .first())

            if transaction and transaction.status == 'pending':
                transaction.status = 'cancelled'
                session.commit()

                try:
                    self.bot.edit_message_text(
                        "❌ **Перевод отменен**\n\n"
                        f"Транзакция #{transaction_id} отменена пользователем.",
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

    def accept_exchange(self, chat_id, message_id, exchange_id, callback_id):
        """Принятие обмена с использованием транзакции"""
        session = db.get_session()
        try:
            # Начинаем транзакцию
            session.begin()

            # Блокируем обмен и связанные данные
            exchange = (session.query(Exchange)
                        .with_for_update()
                        .options(
                joinedload(Exchange.user_from),
                joinedload(Exchange.user_to),
                joinedload(Exchange.currency_from),
                joinedload(Exchange.currency_to)
            )
                        .filter_by(id=exchange_id)
                        .first())

            if not exchange:
                session.rollback()
                self.bot.answer_callback_query(callback_id, "❌ Обмен не найден")
                return

            if exchange.status != ExchangeStatus.PENDING:
                session.rollback()
                self.bot.answer_callback_query(callback_id, "❌ Обмен уже обработан")
                return

            # Блокируем ВСЕ кошельки для обновления
            # Кошелек отправителя (отдает валюту from)
            from_wallet_send = (session.query(Wallet)
                                .with_for_update()
                                .filter_by(
                user_id=exchange.user_id_from,
                currency_id=exchange.currency_from_id
            ).first())

            # Кошелек отправителя (получает валюту to)
            from_wallet_receive = (session.query(Wallet)
                                   .with_for_update()
                                   .filter_by(
                user_id=exchange.user_id_from,
                currency_id=exchange.currency_to_id
            ).first())

            # Кошелек получателя (отдает валюту to)
            to_wallet_send = (session.query(Wallet)
                              .with_for_update()
                              .filter_by(
                user_id=exchange.user_id_to,
                currency_id=exchange.currency_to_id
            ).first())

            # Кошелек получателя (получает валюту from)
            to_wallet_receive = (session.query(Wallet)
                                 .with_for_update()
                                 .filter_by(
                user_id=exchange.user_id_to,
                currency_id=exchange.currency_from_id
            ).first())

            # Проверяем существование кошельков, создаем если нет
            if not from_wallet_send:
                session.rollback()
                self.bot.answer_callback_query(callback_id,
                                               f"❌ У отправителя нет кошелька {exchange.currency_from.code}")
                return

            if not to_wallet_send:
                session.rollback()
                self.bot.answer_callback_query(callback_id, f"❌ У вас нет кошелька {exchange.currency_to.code}")
                return

            # Создаем кошельки для получения если их нет
            if not from_wallet_receive:
                from_wallet_receive = Wallet(
                    user_id=exchange.user_id_from,
                    currency_id=exchange.currency_to_id,
                    address=f"{exchange.currency_to.code}_address_{exchange.user_id_from}_{exchange.currency_to_id}",
                    balance=0
                )
                session.add(from_wallet_receive)

            if not to_wallet_receive:
                to_wallet_receive = Wallet(
                    user_id=exchange.user_id_to,
                    currency_id=exchange.currency_from_id,
                    address=f"{exchange.currency_from.code}_address_{exchange.user_id_to}_{exchange.currency_from_id}",
                    balance=0
                )
                session.add(to_wallet_receive)

            # Проверяем балансы
            if from_wallet_send.balance < exchange.amount_from:
                exchange.status = ExchangeStatus.REJECTED
                session.commit()
                self.bot.answer_callback_query(callback_id,
                                               f"❌ У отправителя недостаточно {exchange.currency_from.code}")
                return

            if to_wallet_send.balance < exchange.amount_to:
                exchange.status = ExchangeStatus.REJECTED
                session.commit()
                self.bot.answer_callback_query(callback_id, f"❌ У вас недостаточно {exchange.currency_to.code}")
                return

            # ВЫПОЛНЯЕМ ОБМЕН В ТРАНЗАКЦИИ
            # 1. Отправитель отдает валюту from
            from_wallet_send.balance -= exchange.amount_from

            # 2. Получатель получает валюту from
            to_wallet_receive.balance += exchange.amount_from

            # 3. Получатель отдает валюту to
            to_wallet_send.balance -= exchange.amount_to

            # 4. Отправитель получает валюту to
            from_wallet_receive.balance += exchange.amount_to

            # Обновляем статус обмена
            exchange.status = ExchangeStatus.COMPLETED
            exchange.completed_date = datetime.now()

            # Создаем уведомления
            from database import db as database_db

            # Уведомляем отправителя
            database_db.create_notification(
                user_id=exchange.user_id_from,
                type='exchange',
                title='Обмен подтвержден',
                message=f'Ваш обмен с {exchange.user_to.full_name} подтвержден: '
                        f'{exchange.amount_from:.6f} {exchange.currency_from.code} ↔ '
                        f'{exchange.amount_to:.6f} {exchange.currency_to.code}',
                exchange_id=exchange.id,
                priority=2
            )

            # Уведомляем получателя
            database_db.create_notification(
                user_id=exchange.user_id_to,
                type='exchange',
                title='Обмен выполнен',
                message=f'Обмен с {exchange.user_from.full_name} выполнен: '
                        f'Вы получили {exchange.amount_from:.6f} {exchange.currency_from.code}, '
                        f'отдали {exchange.amount_to:.6f} {exchange.currency_to.code}',
                exchange_id=exchange.id,
                priority=2
            )

            # Фиксируем транзакцию
            session.commit()

            # Обновляем сообщение
            try:
                self.bot.edit_message_text(
                    "✅ **Обмен выполнен успешно**\n\n"
                    f"💱 Обмен завершен!\n"
                    f"👤 От: {exchange.user_from.full_name}\n"
                    f"👤 Кому: {exchange.user_to.full_name}\n"
                    f"💸 {exchange.amount_from:.6f} {exchange.currency_from.code} ↔ {exchange.amount_to:.6f} {exchange.currency_to.code}\n"
                    f"📊 Курс: 1 {exchange.currency_from.code} = {exchange.amount_to / exchange.amount_from:.6f} {exchange.currency_to.code}\n"
                    f"🆔 Обмен: #{exchange.id}\n\n"
                    f"✅ Средства успешно переведены на кошельки.",
                    chat_id=chat_id,
                    message_id=message_id,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.warning(f"Could not edit message: {e}")

            self.bot.answer_callback_query(callback_id, "✅ Обмен выполнен")

            # Уведомляем инициатора обмена
            if exchange.user_from.telegram_id:
                self.send_notification(
                    exchange.user_from.telegram_id,
                    f"✅ Ваш обмен подтвержден!\n\n"
                    f"С {exchange.user_to.full_name}\n"
                    f"💸 Вы отдали: {exchange.amount_from:.6f} {exchange.currency_from.code}\n"
                    f"💸 Вы получили: {exchange.amount_to:.6f} {exchange.currency_to.code}\n"
                    f"🆔 Обмен: #{exchange.id}"
                )

        except Exception as e:
            session.rollback()
            logging.error(f"Error accepting exchange: {e}", exc_info=True)
            try:
                self.bot.answer_callback_query(callback_id, "❌ Ошибка при обмене")
            except:
                pass
        finally:
            session.close()

    def reject_exchange(self, chat_id, message_id, exchange_id, callback_id):
        """Отклонение обмена"""
        session = db.get_session()
        try:
            session.begin()

            exchange = (session.query(Exchange)
                        .with_for_update()
                        .filter_by(id=exchange_id)
                        .first())

            if exchange and exchange.status == ExchangeStatus.PENDING:
                exchange.status = ExchangeStatus.REJECTED
                session.commit()

                try:
                    self.bot.edit_message_text(
                        "❌ **Обмен отклонен**\n\n"
                        f"Обмен #{exchange_id} отклонен получателем.",
                        chat_id=chat_id,
                        message_id=message_id,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logging.warning(f"Could not edit message: {e}")

                self.bot.answer_callback_query(callback_id, "❌ Обмен отклонен")

                # Уведомляем инициатора обмена
                if exchange.user_from.telegram_id:
                    self.send_notification(
                        exchange.user_from.telegram_id,
                        f"❌ Ваш обмен отклонен\n\n"
                        f"С {exchange.user_to.full_name}\n"
                        f"🆔 Обмен: #{exchange.id}\n"
                        f"💸 {exchange.amount_from:.6f} {exchange.currency_from.code} ↔ "
                        f"{exchange.amount_to:.6f} {exchange.currency_to.code}"
                    )
            else:
                self.bot.answer_callback_query(callback_id, "❌ Обмен не найден")

        except Exception as e:
            session.rollback()
            logging.error(f"Error rejecting exchange: {e}")
            try:
                self.bot.answer_callback_query(callback_id, "❌ Ошибка при отклонении")
            except:
                pass
        finally:
            session.close()

    def send_confirmation_request(self, user_telegram_id, transaction_id):
        """Отправка запроса на подтверждение перевода"""
        try:
            session = db.get_session()
            try:
                # Получаем транзакцию с нужными отношениями
                transaction = (session.query(Transaction)
                               .options(
                    joinedload(Transaction.user_from),
                    joinedload(Transaction.user_to),
                    joinedload(Transaction.currency_rel)
                )
                               .filter_by(id=transaction_id)
                               .first())

                if not transaction:
                    logging.error(f"Transaction {transaction_id} not found")
                    return False

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
                    f"💳 Комиссия: {transaction.amount * 0.01:.6f} (1%)\n"
                    f"💰 Итого к списанию: {transaction.amount * 1.01:.6f}\n\n"
                    f"🆔 Транзакция: #{transaction.id}\n"
                    f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                )

                self.bot.send_message(
                    user_telegram_id,
                    message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return True

            finally:
                session.close()

        except Exception as e:
            logging.error(f"Error sending confirmation: {e}")
            return False

    def send_pdf_document(self, user_telegram_id, pdf_file_path, caption=""):
        """Отправка PDF документа с обработкой ошибок"""
        try:
            if not user_telegram_id:
                return False

            # Проверяем существование файла
            if not os.path.exists(pdf_file_path):
                logging.error(f"PDF file not found: {pdf_file_path}")
                return False

            # Проверяем размер файла (Telegram ограничивает 50MB)
            file_size = os.path.getsize(pdf_file_path)
            if file_size > 50 * 1024 * 1024:  # 50MB
                logging.error(f"File too large: {file_size} bytes")
                return False

            # Отправляем файл
            with open(pdf_file_path, 'rb') as pdf_file:
                self.bot.send_document(
                    user_telegram_id,
                    pdf_file,
                    caption=caption,
                    parse_mode='Markdown'
                )

            logging.info(f"PDF sent successfully to {user_telegram_id}")
            return True

        except Exception as e:
            logging.error(f"Error sending PDF to {user_telegram_id}: {e}")
            return False

    def send_exchange_request(self, user_telegram_id, exchange_id):
        """Отправка запроса на подтверждение обмена"""
        try:
            session = db.get_session()
            try:
                # Получаем обмен с нужными отношениями
                exchange = (session.query(Exchange)
                            .options(
                    joinedload(Exchange.user_from),
                    joinedload(Exchange.user_to),
                    joinedload(Exchange.currency_from),
                    joinedload(Exchange.currency_to)
                )
                            .filter_by(id=exchange_id)
                            .first())

                if not exchange:
                    logging.error(f"Exchange {exchange_id} not found")
                    return False

                keyboard = types.InlineKeyboardMarkup()
                keyboard.row(
                    types.InlineKeyboardButton(
                        "✅ Принять",
                        callback_data=f"exchange_accept_{exchange.id}"
                    ),
                    types.InlineKeyboardButton(
                        "❌ Отклонить",
                        callback_data=f"exchange_reject_{exchange.id}"
                    )
                )

                message = (
                    "🔄 **Запрос на обмен P2P**\n\n"
                    f"👤 От: {exchange.user_from.full_name}\n"
                    f"📧 Телефон: {exchange.user_from.phone}\n"
                    f"💸 Вы получаете: {exchange.amount_from:.6f} {exchange.currency_from.code}\n"
                    f"💸 Вы отдаете: {exchange.amount_to:.6f} {exchange.currency_to.code}\n"
                    f"📊 Курс: 1 {exchange.currency_from.code} = {exchange.amount_to / exchange.amount_from:.6f} {exchange.currency_to.code}\n\n"
                    f"🆔 Обмен: #{exchange.id}\n"
                    f"🕐 {datetime.now().strftime('%H:%M:%S')}\n\n"
                    f"*При принятии средства будут автоматически обменены*"
                )

                self.bot.send_message(
                    user_telegram_id,
                    message,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return True

            finally:
                session.close()

        except Exception as e:
            logging.error(f"Error sending exchange request: {e}")
            return False

    def send_notification(self, user_telegram_id, message):
        """Отправка уведомления пользователю"""
        try:
            if not user_telegram_id:
                return False

            self.bot.send_message(user_telegram_id, message, parse_mode='Markdown')
            return True
        except Exception as e:
            logging.error(f"Error sending notification to {user_telegram_id}: {e}")
            return False



    def link_telegram_account(self, user_id, telegram_id):
        """Привязка Telegram аккаунта к пользователю с транзакцией"""
        session = db.get_session()
        try:
            session.begin()

            user = session.query(User).get(user_id)
            if not user:
                session.rollback()
                return False

            # Проверяем не привязан ли этот Telegram к другому пользователю
            existing_user = session.query(User).filter_by(telegram_id=str(telegram_id)).first()
            if existing_user and existing_user.id != user_id:
                session.rollback()
                return False

            user.telegram_id = str(telegram_id)
            session.commit()

            self.send_notification(
                telegram_id,
                "✅ Ваш Telegram аккаунт успешно привязан к крипто-кошельку!\n\n"
                "Теперь вы будете получать уведомления о:\n"
                "• Подтверждении операций\n"
                "• Входах в аккаунт\n"
                "• Полученных переводах\n\n"
                "Для безопасности все операции требуют подтверждения через этого бота."
            )
            return True
        except Exception as e:
            session.rollback()
            logging.error(f"Error linking telegram account: {e}")
            return False
        finally:
            session.close()

    def run(self):
        """Запуск бота"""
        logging.info("Telegram бот запущен...")
        try:
            self.bot.polling(none_stop=True, interval=0, timeout=60)
        except Exception as e:
            logging.error(f"Bot polling error: {e}")
            time.sleep(5)
            self.run()


# Создаем экземпляр бота
telegram_bot = TelegramBot("token")