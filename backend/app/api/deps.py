from typing import Generator
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.connection import SessionLocal

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

def get_redis_pool(request: Request):
    """Get the arq Redis connection pool attached to the app state."""
    return getattr(request.app.state, "redis_pool", None)
