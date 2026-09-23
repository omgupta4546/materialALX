"""
Backend Configuration Module

Centralized configuration for the FastAPI application.
Leverages Pydantic BaseSettings to read from the environment and validate types.
"""
import os
from pydantic_settings import BaseSettings


def _is_placeholder_value(value: str | None) -> bool:
    if not value:
        return True
    lowered = value.lower()
    return any(marker in lowered for marker in ["*", "your_", "example", "placeholder", "changeme"])


def _resolve_database_url() -> str:
    test_url = os.getenv("TEST_DATABASE_URL")
    if test_url and not _is_placeholder_value(test_url):
        return test_url

    configured = os.getenv("DATABASE_URL")
    if configured and not _is_placeholder_value(configured):
        return configured

    return "sqlite:///./platform.db"


def _resolve_redis_url() -> str:
    configured = os.getenv("REDIS_URL")
    if configured and not _is_placeholder_value(configured):
        return configured
    return "redis://localhost:6379/0"


class Settings(BaseSettings):
    # API Settings
    API_BASE_URL: str = "http://localhost:8000"

    # Database Settings
    DATABASE_URL: str = "sqlite:///./platform.db"
    VECTOR_DIMENSION: int = 1536

    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Provider Settings
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    AI_PROVIDER: str = "local"
    EMBEDDING_MODEL: str = "all-mpnet-base-v2"

    # Security
    JWT_SECRET: str = "dev-secret-key"

    # Storage
    STORAGE_BACKEND: str = "local"
    STORAGE_PATH: str = "./data/raw"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }

    def __init__(self, **values):
        super().__init__(**values)
        if _is_placeholder_value(self.DATABASE_URL):
            self.DATABASE_URL = _resolve_database_url()
        if _is_placeholder_value(self.REDIS_URL):
            self.REDIS_URL = _resolve_redis_url()


# Global settings instance
settings = Settings()
