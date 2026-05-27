"""ARQ worker settings for backend background jobs."""

from __future__ import annotations

from urllib.parse import urlparse

from arq.connections import RedisSettings

from app.config import get_settings
from app.tasks.ingestion_task import ingest_document


def get_redis_settings() -> RedisSettings:
    """Parse the configured Redis URL into ARQ connection settings."""

    parsed = urlparse(get_settings().redis_url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
    )


class WorkerSettings:
    functions = [ingest_document]
    redis_settings = get_redis_settings()
    max_jobs = 10
    job_timeout = 600
