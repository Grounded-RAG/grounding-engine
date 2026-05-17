"""Regression tests for Alembic configuration."""

from configparser import ConfigParser
from pathlib import Path


def test_alembic_ini_includes_logging_sections() -> None:
    """The Alembic config should include the logging sections env.py expects."""

    config = ConfigParser()
    config.read(Path("backend/alembic.ini"))

    assert config.has_section("loggers")
    assert config.has_section("handlers")
    assert config.has_section("formatters")


def test_alembic_template_exists() -> None:
    """Alembic should include the revision template required for autogenerate."""

    assert Path("backend/alembic/script.py.mako").is_file()
