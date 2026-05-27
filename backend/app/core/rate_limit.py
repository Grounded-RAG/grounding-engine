"""In-process sliding-window rate limiter for API endpoints.

Uses a per-key deque of request timestamps to enforce a maximum number of
requests in a rolling window. No external dependency (Redis-free).

Limits are applied per API-key so each key gets its own independent bucket.

Default limits (all overridable via env vars):
  RATE_LIMIT_QUERY_RPM   = 60   (query endpoint)
  RATE_LIMIT_INGEST_RPM  = 30   (document ingest endpoint)
  RATE_LIMIT_DEFAULT_RPM = 120  (all other authenticated endpoints)
"""

from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _rpm(env_var: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(env_var, default)))
    except (ValueError, TypeError):
        return default


QUERY_RPM: int = _rpm("RATE_LIMIT_QUERY_RPM", 60)
INGEST_RPM: int = _rpm("RATE_LIMIT_INGEST_RPM", 30)
DEFAULT_RPM: int = _rpm("RATE_LIMIT_DEFAULT_RPM", 120)

_WINDOW_SECONDS: float = 60.0


# ---------------------------------------------------------------------------
# Core sliding-window bucket
# ---------------------------------------------------------------------------

@dataclass
class _Bucket:
    max_requests: int
    timestamps: deque[float] = field(default_factory=deque)
    lock: Lock = field(default_factory=Lock)

    def _evict(self, now: float) -> None:
        cutoff = now - _WINDOW_SECONDS
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

    def is_allowed(self) -> bool:
        now = time.monotonic()
        with self.lock:
            self._evict(now)
            if len(self.timestamps) >= self.max_requests:
                return False
            self.timestamps.append(now)
            return True

    def remaining(self) -> int:
        now = time.monotonic()
        with self.lock:
            self._evict(now)
            return max(0, self.max_requests - len(self.timestamps))


# ---------------------------------------------------------------------------
# Global registry — one bucket per (api_key_id, limit_key) pair
# ---------------------------------------------------------------------------

_registry: dict[tuple[str, str], _Bucket] = {}
_registry_lock = Lock()


def _get_bucket(api_key_id: str, limit_key: str, max_requests: int) -> _Bucket:
    key = (api_key_id, limit_key)
    with _registry_lock:
        if key not in _registry:
            _registry[key] = _Bucket(max_requests=max_requests)
        return _registry[key]


# ---------------------------------------------------------------------------
# Public check function
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    limit_key: str


def check_rate_limit(
    *,
    api_key_id: str,
    limit_key: str,
    max_requests: int,
) -> RateLimitResult:
    """Check the sliding-window rate limit for one API key.

    Returns a result — never raises. Policy decisions stay in the caller.
    """
    bucket = _get_bucket(api_key_id, limit_key, max_requests)
    allowed = bucket.is_allowed()
    remaining = bucket.remaining()
    return RateLimitResult(
        allowed=allowed,
        limit=max_requests,
        remaining=remaining,
        limit_key=limit_key,
    )


# ---------------------------------------------------------------------------
# FastAPI dependency factories
# ---------------------------------------------------------------------------

def _make_dependency(limit_key: str, max_requests: int):
    from fastapi import Depends, HTTPException, status
    from app.api.deps import TenantContext, get_tenant_context

    async def _dep(
        tenant_context: TenantContext = Depends(get_tenant_context),
    ) -> None:
        result = check_rate_limit(
            api_key_id=str(tenant_context.api_key_id),
            limit_key=limit_key,
            max_requests=max_requests,
        )
        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Rate limit exceeded: {max_requests} requests per minute "
                    f"on '{limit_key}' endpoint."
                ),
                headers={"Retry-After": "60"},
            )

    return _dep


# Public dependency objects — import directly in route files.
query_rate_limit = _make_dependency("query", QUERY_RPM)
ingest_rate_limit = _make_dependency("ingest", INGEST_RPM)
default_rate_limit = _make_dependency("default", DEFAULT_RPM)
