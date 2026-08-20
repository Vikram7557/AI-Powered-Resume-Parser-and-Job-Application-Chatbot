"""
SQLAlchemy engine/session setup.

Default local target is MySQL (JD lists MySQL). Set DATABASE_URL in .env.
SQLite still works for a quick fallback: sqlite:///./app.db
"""
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine_kwargs = {"connect_args": connect_args} if connect_args else {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_database() -> None:
    """Create the MySQL database if the URL points at MySQL and it is missing."""
    if not DATABASE_URL.startswith("mysql"):
        return

    url = make_url(DATABASE_URL)
    db_name = url.database
    if not db_name:
        raise ValueError("DATABASE_URL must include a database name")
    if not db_name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe database name: {db_name}")

    admin_engine = create_engine(
        url.set(database=""),
        isolation_level="AUTOCOMMIT",
    )
    try:
        with admin_engine.connect() as conn:
            conn.execute(
                text(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
        print(f"MySQL database ready: {db_name}")
    finally:
        admin_engine.dispose()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
