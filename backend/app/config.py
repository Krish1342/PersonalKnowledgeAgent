from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root: backend/
PROJECT_ROOT = Path(__file__).parent.parent.resolve()


class Settings(BaseSettings):
    """Application settings managed via environment variables."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Vector database path (ChromaDB)
    VECTOR_DB_PATH: str = str(PROJECT_ROOT / "data" / "vector_store")

    # SQLite database path (Episodic/Procedural memory)
    SQLITE_DB_PATH: str = str(PROJECT_ROOT / "data" / "episodic.db")

    # Embedding model name (Sentence-Transformers)
    MODEL_NAME: str = "all-MiniLM-L6-v2"

    # Groq API key for LLM
    GROQ_API_KEY: str = ""

    # Groq model name
    GROQ_MODEL_NAME: str = "llama-3.1-8b-instant"

    # Clerk Authentication
    CLERK_PUBLISHABLE_KEY: Optional[str] = None
    CLERK_SECRET_KEY: Optional[str] = None

    # CORS settings for deployment
    CORS_ORIGINS: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002"  # Comma-separated list
    )

    # Environment
    ENVIRONMENT: str = "development"  # development, staging, production

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == "production"


# Singleton instance
settings = Settings()
