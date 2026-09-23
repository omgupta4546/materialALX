"""
database/connection.py — Production-grade PostgreSQL connection layer.

Features:
  - Connection pooling (QueuePool) sized for concurrent API + worker load
  - pgvector extension registration
  - Environment-driven configuration
  - Async-compatible session factory
  - Health-check utility
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

load_dotenv()

log = logging.getLogger(__name__)


def _is_placeholder_value(value: str | None) -> bool:
    if not value:
        return True
    lowered = value.lower()
    return any(marker in lowered for marker in ["*", "your_", "example", "placeholder", "changeme"])


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE URL
# Priority: explicit test URL → explicit app URL → SQLite fallback for local/dev
# ─────────────────────────────────────────────────────────────────────────────

if os.getenv("PYTEST_CURRENT_TEST"):
    _DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
else:
    _DATABASE_URL = os.getenv("DATABASE_URL")

if _is_placeholder_value(_DATABASE_URL):
    _DATABASE_URL = os.getenv("TEST_DATABASE_URL") or "sqlite:///./platform.db"

if not _DATABASE_URL:
    _use_sqlite = os.getenv("USE_SQLITE", "true").lower() in {"1", "true", "yes", "on"}
    if _use_sqlite:
        _DATABASE_URL = "sqlite:///./platform.db"
    else:
        _PG_HOST     = os.getenv("POSTGRES_HOST",     "localhost")
        _PG_PORT     = os.getenv("POSTGRES_PORT",     "5432")
        _PG_DB       = os.getenv("POSTGRES_DB",       "platform")
        _PG_USER     = os.getenv("POSTGRES_USER",     "postgres")
        _PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
        _DATABASE_URL = f"postgresql://{_PG_USER}:{_PG_PASSWORD}@{_PG_HOST}:{_PG_PORT}/{_PG_DB}"

DATABASE_URL: str = _DATABASE_URL

# ─────────────────────────────────────────────────────────────────────────────
# ENGINE — QueuePool for production concurrency
# ─────────────────────────────────────────────────────────────────────────────

_is_sqlite = DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {
    "echo": os.getenv("SQL_ECHO", "false").lower() == "true",
    "future": True,  # SQLAlchemy 2.0 style
}

if not _is_sqlite:
    _engine_kwargs.update({
        "poolclass": QueuePool,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),       # persistent connections
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")), # burst headroom
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")), # sec before giving up
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),# recycle stale conns
        "pool_pre_ping": True,                                    # validate before use
        # "connect_args": {
        #     "options": "-c statement_timeout=30000"               # 30s query timeout
        # },
    })
else:
    # SQLite: no pool, for local dev/CI only
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# pgvector — register vector type on every new connection
# ─────────────────────────────────────────────────────────────────────────────

if not _is_sqlite:
    try:
        from pgvector.psycopg2 import register_vector

        @event.listens_for(engine, "connect")
        def _register_vector(dbapi_connection, connection_record):
            register_vector(dbapi_connection)

    except ImportError:
        log.warning("pgvector psycopg2 adapter not found — vector ops will be unavailable")


# ─────────────────────────────────────────────────────────────────────────────
# SESSION FACTORY
# ─────────────────────────────────────────────────────────────────────────────

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # avoid lazy-load after commit in background tasks
)


# ─────────────────────────────────────────────────────────────────────────────
# DEPENDENCY — for FastAPI Depends()
# ─────────────────────────────────────────────────────────────────────────────

def get_db() -> Generator[Session, None, None]:
    """Yield a database session scoped to a single HTTP request."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TRANSACTION CONTEXT MANAGER — for background tasks / scripts
# ─────────────────────────────────────────────────────────────────────────────

@contextmanager
def transaction() -> Generator[Session, None, None]:
    """
    Context manager that commits on success and rolls back on any exception.

    Usage::

        with transaction() as db:
            db.add(some_model)
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────────────────────

def check_db_health() -> dict:
    """Return connectivity status, pgvector availability, and pool stats."""
    result = {
        "status": "unknown",
        "database_url_host": DATABASE_URL.split("@")[-1].split("/")[0] if "@" in DATABASE_URL else "local",
        "pgvector": False,
        "pool_size": getattr(engine.pool, "size", lambda: None)(),
        "checked_out": getattr(engine.pool, "checkedout", lambda: None)(),
    }
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            # Check pgvector extension
            try:
                row = conn.execute(
                    text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
                ).fetchone()
                result["pgvector"] = row is not None
            except Exception:
                result["pgvector"] = False
        result["status"] = "ok"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    return result
