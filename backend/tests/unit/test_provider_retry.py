"""Unit tests for provider retry helpers."""

from __future__ import annotations

import urllib.error

import pytest

from app.core.provider_retry import run_with_retries


@pytest.mark.asyncio()
async def test_run_with_retries_retries_retryable_errors_until_success() -> None:
    """Retryable provider failures should be retried before succeeding."""

    attempts = {"count": 0}

    async def flaky_operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise urllib.error.URLError("temporary network failure")
        return "ok"

    result = await run_with_retries(
        flaky_operation,
        max_retries=2,
        backoff_ms=0,
    )

    assert result == "ok"
    assert attempts["count"] == 3


@pytest.mark.asyncio()
async def test_run_with_retries_does_not_retry_non_retryable_errors() -> None:
    """Permanent provider failures should surface immediately."""

    attempts = {"count": 0}

    async def invalid_operation() -> str:
        attempts["count"] += 1
        raise ValueError("bad payload")

    with pytest.raises(ValueError, match="bad payload"):
        await run_with_retries(
            invalid_operation,
            max_retries=3,
            backoff_ms=0,
        )

    assert attempts["count"] == 1
