"""
Configuration management using Pydantic Settings.
Supports environment-based config with .env file override.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Application
    APP_NAME: str = "Personal Knowledge Agent"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development, staging, production
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Logging
    LOG_FORMAT: str = "json"  # json or text

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/knowledge_agent"

    # Vector Store
    VECTOR_STORE_PATH: str = "./data/vector_store"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses LRU cache to avoid reloading settings multiple times.
    """
    return Settings()
