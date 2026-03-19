"""Unit tests for database helpers."""

import asyncio

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.config import get_settings
from app.core.database import (
    dispose_database,
    get_async_engine,
    get_db_session,
    get_session_factory,
)


def test_get_async_engine_uses_configured_url(monkeypatch) -> None:
    """The async engine should reflect the configured database URL."""

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://grounded:grounded@localhost:5433/grounded_test",
    )
    get_settings.cache_clear()
    get_async_engine.cache_clear()
    get_session_factory.cache_clear()

    engine = get_async_engine()

    assert isinstance(engine, AsyncEngine)
    assert "grounded_test" in engine.url.render_as_string(hide_password=False)

    asyncio.run(dispose_database())
    get_settings.cache_clear()


def test_get_db_session_yields_async_session(monkeypatch) -> None:
    """The DB dependency should yield an async session object."""

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://grounded:grounded@localhost:5433/grounded_test",
    )
    get_settings.cache_clear()
    get_async_engine.cache_clear()
    get_session_factory.cache_clear()

    async def run_test() -> None:
        session_generator = get_db_session()
        session = await anext(session_generator)

        assert isinstance(session, AsyncSession)

        await session_generator.aclose()
        await dispose_database()

    asyncio.run(run_test())
    get_settings.cache_clear()
