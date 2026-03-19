"""Database engine, session, and metadata primitives."""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Base declarative model class for SQLAlchemy models."""


@lru_cache
def get_async_engine() -> AsyncEngine:
    """Create and cache the async SQLAlchemy engine."""

    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Create and cache the async session factory."""

    return async_sessionmaker(
        bind=get_async_engine(),
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session for request-scoped use."""

    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def ping_database() -> bool:
    """Check whether the database is reachable."""

    try:
        async with get_async_engine().connect() as connection:
            await connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False


async def dispose_database() -> None:
    """Dispose the cached engine and clear DB-related caches."""

    engine = get_async_engine()
    await engine.dispose()
    get_session_factory.cache_clear()
    get_async_engine.cache_clear()
