"""Schemas for health and readiness endpoints."""

from typing import Literal

from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """Liveness response payload."""

    status: Literal["alive"]


class ReadinessResponse(BaseModel):
    """Readiness response payload."""

    status: Literal["ready"]
    service: str
    environment: str
    version: str
    checks: dict[str, str]
