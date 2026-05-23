"""Audit log API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Audit log entry returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    log_id: UUID
    workspace_id: UUID | None
    actor_key_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    summary: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Paginated list of audit log entries."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
