from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker
from models import Base, Session, Notification, UserInterface, User, UserRole
from datetime import datetime, timedelta
import os
import shutil


class Database:
    def __init__(self, db_url="sqlite:///crypto_wallet.db"):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.func = func

    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        print("Таблицы базы данных проверены/созданы")
        self.migrate_user_roles()

    def migrate_user_roles(self):
        """Миграция для добавления ролей пользователей"""
        session = self.get_session()
        try:
            # Проверяем, есть ли колонка two_factor_enabled
            result = session.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result]

            if 'two_factor_enabled' in columns and 'role' not in columns:
                print("Выполняем миграцию ролей пользователей...")
                # Добавляем колонку role
                session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(10) DEFAULT 'USER'"))
                # Переносим данные из two_factor_enabled в role
                session.execute(text("""
                                     UPDATE users
                                     SET role = :admin
                                     WHERE two_factor_enabled = 1
                                     """), {'admin': UserRole.ADMIN.value})
                # Удаляем старую колонку
                session.execute(text("ALTER TABLE users DROP COLUMN two_factor_enabled"))
                session.commit()
                print("Миграция ролей завершена успешно")
            elif 'role' not in columns:
                # Просто добавляем колонку role
                session.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(10) DEFAULT 'USER'"))
                session.commit()

        except Exception as e:
            session.rollback()
            print(f"Ошибка миграции: {e}")
        finally:
            session.close()

    def get_session(self):
        return self.SessionLocal()

    def create_user_session(self, user_id, ip_address="", user_agent=""):
        """Создание новой сессии пользователя"""
        session = self.get_session()
        try:
            user_session = Session(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                status='ACTIVE'
            )
            session.add(user_session)
            session.commit()
            return user_session
        except Exception as e:
            session.rollback()
            print(f"Error creating user session: {e}")
            return None
        finally:
            session.close()

    def update_session_activity(self, session_id):
        """Обновление времени последней активности сессии"""
        session = self.get_session()
        try:
            user_session = session.query(Session).get(session_id)
            if user_session:
                user_session.last_activity = datetime.now()
                session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error updating session activity: {e}")
        finally:
            session.close()

    def cleanup_expired_sessions(self, hours=24):
        """Очистка просроченных сессий"""
        session = self.get_session()
        try:
            expiry_time = datetime.now() - timedelta(hours=hours)
            expired_sessions = session.query(Session).filter(
                Session.last_activity < expiry_time
            ).all()

            for user_session in expired_sessions:
                user_session.status = 'EXPIRED'

            session.commit()
            print(f"Обновлено {len(expired_sessions)} просроченных сессий")
        except Exception as e:
            session.rollback()
            print(f"Error cleaning up sessions: {e}")
        finally:
            session.close()

    def create_notification(self, user_id, type, title, message, transaction_id=None, exchange_id=None, priority=1):
        """Создание уведомления"""
        session = self.get_session()
        try:
            notification = Notification(
                user_id=user_id,
                type=type,
                title=title,
                message=message,
                transaction_id=transaction_id,
                exchange_id=exchange_id,
                priority=priority
            )
            session.add(notification)
            session.commit()
            return notification
        except Exception as e:
            session.rollback()
            print(f"Error creating notification: {e}")
            return None
        finally:
            session.close()

    def get_user_notifications(self, user_id, unread_only=False, limit=50):
        """Получение уведомлений пользователя"""
        session = self.get_session()
        try:
            query = session.query(Notification).filter_by(user_id=user_id)
            if unread_only:
                query = query.filter_by(is_read=False)
            return query.order_by(Notification.created_date.desc()).limit(limit).all()
        except Exception as e:
            print(f"Error getting notifications: {e}")
            return []
        finally:
            session.close()

    def mark_notification_read(self, notification_id):
        """Пометить уведомление как прочитанное"""
        session = self.get_session()
        try:
            notification = session.query(Notification).get(notification_id)
            if notification:
                notification.is_read = True
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error marking notification as read: {e}")
            return False
        finally:
            session.close()

    def get_user_interface(self, user_id):
        """Получение настроек интерфейса пользователя"""
        session = self.get_session()
        try:
            ui = session.query(UserInterface).filter_by(user_id=user_id).first()
            if not ui:
                ui = UserInterface(user_id=user_id)
                session.add(ui)
                session.commit()
            return ui
        except Exception as e:
            session.rollback()
            print(f"Error getting user interface: {e}")
            return None
        finally:
            session.close()

    def update_user_interface(self, user_id, **kwargs):
        """Обновление настроек интерфейса пользователя"""
        session = self.get_session()
        try:
            ui = session.query(UserInterface).filter_by(user_id=user_id).first()
            if not ui:
                ui = UserInterface(user_id=user_id)
                session.add(ui)

            for key, value in kwargs.items():
                if hasattr(ui, key):
                    setattr(ui, key, value)

            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error updating user interface: {e}")
            return False
        finally:
            session.close()

    def execute_transaction(self, func, *args, **kwargs):
        """Выполнить функцию в транзакции"""
        session = self.get_session()
        try:
            result = func(session, *args, **kwargs)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def backup_database(self):
        """Создание резервной копии базы данных"""
        try:
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{backup_dir}/crypto_wallet_backup_{timestamp}.db"

            if os.path.exists("crypto_wallet.db"):
                shutil.copy2("crypto_wallet.db", backup_file)

            # Очистка старых бэкапов (храним только последние 7)
            if os.path.exists(backup_dir):
                backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
                if len(backups) > 7:
                    for old_backup in backups[:-7]:
                        os.remove(os.path.join(backup_dir, old_backup))

            print(f"Backup created: {backup_file}")
            return True

        except Exception as e:
            print(f"Backup failed: {e}")
            return False


# Создаем экземпляр базы данных
db = Database()