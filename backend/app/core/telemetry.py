"""Structured logging and request telemetry helpers."""

from __future__ import annotations

import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response


REQUEST_ID_HEADER = "X-Request-ID"


def configure_logging(log_level: str) -> None:
    """Configure structured JSON logging for the application."""

    structlog.reset_defaults()
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
        force=True,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a namespaced structured logger."""

    return structlog.get_logger(name)


def generate_request_id() -> str:
    """Return a compact request identifier suitable for headers and logs."""

    return uuid.uuid4().hex


def bind_request_context(*, request_id: str, method: str, path: str) -> None:
    """Bind request-scoped context used by logs and later trace stitching."""

    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        trace_id=request_id,
        method=method,
        path=path,
    )


def bind_tenant_context(*, tenant_id: str, api_key_id: str | None = None) -> None:
    """Bind tenant-aware context after authentication succeeds."""

    context = {"tenant_id": tenant_id}
    if api_key_id is not None:
        context["api_key_id"] = api_key_id
    structlog.contextvars.bind_contextvars(**context)


def bind_execution_context(
    *,
    requested_tier: str | None,
    router_recommendation: str,
    effective_tier: str,
    routing_reason: str,
    selected_mode: str | None = None,
) -> None:
    """Bind execution-routing context once a tier decision has been made."""

    structlog.contextvars.bind_contextvars(
        requested_tier=requested_tier,
        router_recommendation=router_recommendation,
        effective_tier=effective_tier,
        routing_reason=routing_reason,
        selected_mode=selected_mode,
    )


def clear_request_context() -> None:
    """Clear any request-scoped log context."""

    structlog.contextvars.clear_contextvars()


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach request IDs, bind log context, and emit request lifecycle logs."""

    clear_request_context()
    request_id = request.headers.get(REQUEST_ID_HEADER, "").strip() or generate_request_id()
    bind_request_context(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    request.state.request_id = request_id
    request.state.trace_id = request_id
    logger = get_logger("app.http")
    start = time.perf_counter()
    logger.info("request_started")

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception("request_failed", duration_ms=duration_ms)
        raise
    finally:
        if "response" not in locals():
            clear_request_context()

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers[REQUEST_ID_HEADER] = request_id
    logger.info("request_completed", status_code=response.status_code, duration_ms=duration_ms)
    clear_request_context()
    return response
