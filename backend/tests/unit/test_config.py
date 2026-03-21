"""Unit tests for application settings."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_normalize_log_level() -> None:
    """Lowercase log levels should normalize to uppercase."""

    settings = Settings(log_level="debug")

    assert settings.log_level == "DEBUG"


def test_settings_reject_invalid_environment() -> None:
    """Unexpected environments should fail validation."""

    with pytest.raises(ValidationError):
        Settings(app_env="local")


def test_settings_validate_database_drivers() -> None:
    """Database settings should enforce the expected drivers."""

    settings = Settings(
        database_url="postgresql+asyncpg://grounded:grounded@localhost:5433/grounded",
        alembic_database_url="postgresql+psycopg://grounded:grounded@localhost:5433/grounded",
    )

    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.alembic_database_url.startswith("postgresql+psycopg://")


def test_settings_reject_invalid_database_driver() -> None:
    """Database URL should reject unsupported drivers."""

    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///tmp.db")


def test_settings_require_non_empty_api_key_salt() -> None:
    """Security settings should reject an empty API key salt."""

    with pytest.raises(ValidationError):
        Settings(api_key_salt="   ")


def test_settings_reject_placeholder_api_key_salt_outside_dev() -> None:
    """Production-like environments should not accept the public placeholder salt."""

    with pytest.raises(ValidationError):
        Settings(app_env="production", api_key_salt="replace-in-local-env")


def test_settings_reject_non_positive_upload_limit() -> None:
    """Upload limits should fail validation when they are not positive."""

    with pytest.raises(ValidationError):
        Settings(document_upload_max_bytes=0)
