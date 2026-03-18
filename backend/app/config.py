"""Application settings placeholders for upcoming Phase 0 configuration work."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Base backend settings loaded from environment variables."""

    app_name: str = "Grounded Backend"
    app_env: str = "development"
    api_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached application settings object."""

    return Settings()
