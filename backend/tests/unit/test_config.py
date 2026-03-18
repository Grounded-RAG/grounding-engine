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
