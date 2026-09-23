"""
AI Pipeline Configuration Module

Centralized configuration for AI models, LLM providers, and embeddings.
Ensures the AI components stay agnostic to the rest of the web app.
"""
import os
from pydantic_settings import BaseSettings

class AIConfig(BaseSettings):
    # Provider Selection
    AI_PROVIDER: str = "local"
    
    # Model Configurations
    LLM_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    VECTOR_DIMENSION: int = 1536
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Global AI config instance
ai_config = AIConfig()
