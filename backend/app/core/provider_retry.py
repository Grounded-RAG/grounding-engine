"""Shared retry helpers for external provider-backed Standard requests."""

from __future__ import annotations

import asyncio
import urllib.error
from collections.abc import Awaitable, Callable
from typing import TypeVar


T = TypeVar("T")
_RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}


def is_retryable_provider_error(exc: Exception) -> bool:
    """Return whether an external provider error should be retried."""

    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in _RETRYABLE_STATUS_CODES
    return isinstance(exc, urllib.error.URLError | TimeoutError)


async def run_with_retries(
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    backoff_ms: int,
    should_retry: Callable[[Exception], bool] = is_retryable_provider_error,
) -> T:
    """Run one async provider operation with bounded exponential backoff."""

    attempt = 0
    while True:
        try:
            return await operation()
        except Exception as exc:
            if attempt >= max_retries or not should_retry(exc):
                raise
            sleep_seconds = max(backoff_ms, 0) / 1000 * (2**attempt)
            attempt += 1
            await asyncio.sleep(sleep_seconds)
