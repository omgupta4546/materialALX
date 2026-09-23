"""
Background Worker Configuration Module

Settings specifically for asynchronous workers (e.g., Celery or RQ) processing
heavy workloads like dataset imports, AI embeddings, and deduplication scans.
"""
import os
from pydantic_settings import BaseSettings

class WorkerConfig(BaseSettings):
    # Redis configuration for task queue state and message brokering
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Database connection for saving background job results
    DATABASE_URL: str = "sqlite:///./antigravity.db"
    
    # Storage settings for processing large file uploads
    STORAGE_BACKEND: str = "local"
    STORAGE_PATH: str = "./data/raw"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore"
    }

# Global worker config instance
worker_config = WorkerConfig()
