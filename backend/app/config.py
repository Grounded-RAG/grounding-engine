"""Application settings for the Grounded backend."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

AppEnv = Literal["development", "test", "staging", "production"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_name: str = "Grounded Backend"
    app_version: str = "0.1.0"
    app_env: AppEnv = "development"
    log_level: LogLevel = "INFO"
    api_base_url: AnyHttpUrl = "http://localhost:8000"
    database_url: str = "postgresql+asyncpg://grounded:grounded@localhost:5433/grounded"
    alembic_database_url: str = (
        "postgresql+psycopg://grounded:grounded@localhost:5433/grounded"
    )

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize log level values before validation."""

        if isinstance(value, str):
            return value.upper()
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        """Ensure the runtime database URL uses the async driver."""

        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use the postgresql+asyncpg driver.")
        return value

    @field_validator("alembic_database_url")
    @classmethod
    def validate_alembic_database_url(cls, value: str) -> str:
        """Ensure the Alembic URL uses the sync psycopg driver."""

        if not value.startswith("postgresql+psycopg://"):
            raise ValueError(
                "ALEMBIC_DATABASE_URL must use the postgresql+psycopg driver."
            )
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
