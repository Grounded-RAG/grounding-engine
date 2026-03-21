"""Application settings for the Grounded backend."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, ValidationInfo, field_validator
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
    document_upload_max_bytes: int = 25 * 1024 * 1024
    api_key_salt: str = "replace-in-local-env"
    s3_endpoint_url: AnyHttpUrl = "http://localhost:9000"
    s3_bucket: str = "grounded-documents"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_secure: bool = False

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

    @field_validator("document_upload_max_bytes")
    @classmethod
    def validate_document_upload_max_bytes(cls, value: int) -> int:
        """Ensure the upload size limit is a positive number of bytes."""

        if value <= 0:
            raise ValueError("DOCUMENT_UPLOAD_MAX_BYTES must be greater than zero.")
        return value

    @field_validator("api_key_salt")
    @classmethod
    def validate_api_key_salt(cls, value: str, info: ValidationInfo) -> str:
        """Ensure the API key salt is not empty or an unsafe placeholder."""

        normalized = value.strip()
        if not normalized:
            raise ValueError("API_KEY_SALT must not be empty.")

        app_env = (info.data.get("app_env") or "development").lower()
        if normalized == "replace-in-local-env" and app_env not in {
            "development",
            "test",
        }:
            raise ValueError(
                "API_KEY_SALT must be set to a secure non-default value outside "
                "development and test."
            )
        return normalized

    @field_validator("s3_bucket", "s3_access_key", "s3_secret_key")
    @classmethod
    def validate_storage_settings(cls, value: str, info: ValidationInfo) -> str:
        """Ensure required storage settings are not blank."""

        if not value.strip():
            field_name = info.field_name.upper()
            raise ValueError(f"{field_name} must not be empty.")
        return value

    @field_validator("s3_secure")
    @classmethod
    def validate_storage_tls_setting(
        cls,
        value: bool,
        info: ValidationInfo,
    ) -> bool:
        """Keep the secure flag aligned with the configured endpoint scheme."""

        endpoint = info.data.get("s3_endpoint_url")
        if endpoint is not None and value != (endpoint.scheme == "https"):
            raise ValueError(
                "S3_SECURE must match the scheme used by S3_ENDPOINT_URL."
            )
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
