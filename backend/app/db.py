from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


database_url = make_url(settings.database_url)
if database_url.drivername.startswith("sqlite"):
    raise RuntimeError("SQLite is not supported. Configure PostgreSQL via DATABASE_URL.")

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
