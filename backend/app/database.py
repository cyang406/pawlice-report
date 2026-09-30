import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

database_url = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://pawlice:pawlice@127.0.0.1:3306/pawlice_report",
)
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    """Return a naive UTC value, which MySQL DATETIME can store unchanged."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_db():
    with SessionLocal() as session:
        yield session

