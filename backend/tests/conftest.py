import sys
import os
from unittest.mock import MagicMock, patch

# ── Stub heavy ML libraries before any app import ──────────────────────────
# This prevents CI from failing due to missing sentence-transformers/torch.
# In production, the real packages are installed via requirements.txt.
if os.getenv("CI") or not os.path.exists(
    os.path.join(os.path.dirname(__file__), "..", ".venv")
):
    _st_mock = MagicMock()
    _st_mock.SentenceTransformer.return_value.encode.return_value = [0.0] * 768
    sys.modules.setdefault("sentence_transformers", _st_mock)
    sys.modules.setdefault("torch", MagicMock())
    sys.modules.setdefault("transformers", MagicMock())

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.api.deps import get_db
from app.main import app
from app.auth.router import get_current_user
from app.auth.rbac import Roles
from app.core.rate_limit import limiter

limiter.enabled = False

import os
from sqlalchemy.pool import StaticPool

os.environ.setdefault("TEST_DATABASE_URL", "sqlite:///:memory:")
SQLALCHEMY_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def reset_database(request):
    """Drop and recreate all tables before every test — perfect isolation."""
    if "no_db" in request.keywords:
        yield
        return
    from sqlalchemy import text
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(reset_database):
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


app.dependency_overrides[get_db] = override_get_db

def override_get_current_user():
    return {
        "user_id": "test-admin",
        "name": "Test Admin",
        "role": Roles.ADMIN,
        "cpse": "SYS",
        "permissions": ["*"]
    }


@pytest.fixture(autouse=True)
def setup_dependency_overrides():
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    # No need to clear, it just resets for every test



from unittest.mock import AsyncMock, patch
import pytest

@pytest.fixture(autouse=True)
def mock_redis():
    with patch('app.api.endpoints.jobs.get_redis_pool', new_callable=AsyncMock) as mock_pool:
        yield mock_pool
