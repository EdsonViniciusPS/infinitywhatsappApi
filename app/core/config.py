"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Infinity WhatsApp API"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Security
    JWT_SECRET_KEY: str = "dev-secret-key-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    ADMIN_MASTER_KEY: str = "dev-admin-master-key"
    EVOLUTION_WEBHOOK_SECRET: str = "dev-webhook-secret"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://infinity:infinity@localhost:5432/infinity_api"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Evolution API
    EVOLUTION_API_URL: str = "http://localhost:8080"
    EVOLUTION_API_KEY: str = "dev-evolution-key"
    EVOLUTION_TIMEOUT_SECONDS: float = 30.0

    # Google Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-4-hydrogen"
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    GEMINI_PROJECT_ID: str = "projects/457161151634"
    GEMINI_PROJECT_NUMBER: str = "457161151634"
    GEMINI_KEY_NAME: str = "infinityWhatsapp"
    GEMINI_CONVERSATION_TTL_SECONDS: int = 86400

    # Backups
    BACKUP_DIR: str = "backups"
    BACKUP_RETENTION_DAYS: int = 7
    BACKUP_INTERVAL_SECONDS: int = 21600
    MAINTENANCE_ENABLED: bool = True
    MAINTENANCE_INTERVAL_SECONDS: int = 604800
    LOG_RETENTION_DAYS: int = 7


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
