"""SQLAlchemy database engine and session factory supporting PostgreSQL+pgvector and SQLite."""
from pathlib import Path
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.app.core.config import settings


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite:///"):
        db_path = Path(url.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.DATABASE_URL)

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables and optional PostgreSQL extensions if connected to Postgres."""
    from backend.app.models import models  # noqa: F401

    if settings.is_postgres:
        with engine.begin() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
            except Exception:
                pass
    Base.metadata.create_all(bind=engine)
