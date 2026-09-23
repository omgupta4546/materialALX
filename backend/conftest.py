import os

os.environ.setdefault("USE_SQLITE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./platform.db")
os.environ.setdefault("TEST_DATABASE_URL", "sqlite:///./platform.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
