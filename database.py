# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# --- DB URL ---
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

# --- SQLAlchemy setup ---
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- Initialize DB ---
def init_db():
    from models import User, Transaction, Log  # 遅延インポートで循環防止
    Base.metadata.create_all(bind=engine)


# --- Utility: Return engine instance ---
def get_db_engine():
    """FastAPI起動時やスクリプト用にEngineインスタンスを返す"""
    return engine
