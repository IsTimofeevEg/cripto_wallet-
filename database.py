from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import os


class Database:
    def __init__(self, db_url="sqlite:///crypto_demo.db"):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        print("✅ Таблицы базы данных созданы")

    def get_session(self):
        return self.SessionLocal()


# Создаем экземпляр базы данных
db = Database()