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


def test_settings_reject_chunk_overlap_greater_than_window() -> None:
    """Chunk overlap should stay smaller than the chunk window size."""

    with pytest.raises(ValidationError):
        Settings(chunk_max_tokens=8, chunk_overlap_tokens=8)


def test_settings_reject_blank_qdrant_collection() -> None:
    """Dense index collection names should not be blank."""

    with pytest.raises(ValidationError):
        Settings(qdrant_collection="   ")


def test_settings_reject_non_positive_retrieval_settings() -> None:
    """Retrieval limits and fusion constants must be positive."""

    with pytest.raises(ValidationError):
        Settings(retrieval_candidate_limit=0)

    with pytest.raises(ValidationError):
        Settings(rrf_smoothing_constant=0)


def test_settings_reject_evidence_package_limit_above_retrieval_pool() -> None:
    """Evidence packaging should not exceed the retrieved candidate pool."""

    with pytest.raises(ValidationError):
        Settings(retrieval_candidate_limit=2, evidence_package_limit=3)


def test_settings_emit_startup_warnings_for_fallback_prone_standard_config() -> None:
    """Startup warnings should explain when Standard will silently fall back."""

    settings = Settings(
        generator_backend="gemini_v1",
        embedding_backend="gemini_v1",
        chunking_strategy="deterministic_token_window_v1",
        gemini_api_key=None,
    )

    warnings = settings.startup_warnings()

    assert any("GEMINI_API_KEY" in warning for warning in warnings)
    assert any("CHUNKING_STRATEGY" in warning for warning in warnings)


def test_settings_reject_negative_provider_retry_backoff() -> None:
    """Provider retry backoff should stay non-negative."""

    with pytest.raises(ValidationError):
        Settings(provider_retry_backoff_ms=-1)
