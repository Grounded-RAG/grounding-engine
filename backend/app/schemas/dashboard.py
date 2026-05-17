"""Dashboard API schemas for the product shell."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import IngestionJobStatus


class DashboardSummaryResponse(BaseModel):
    """High-level tenant-scoped counts for the product dashboard."""

    dataset_count: int = Field(ge=0)
    document_count: int = Field(ge=0)
    indexed_document_count: int = Field(ge=0)
    running_job_count: int = Field(ge=0)
    failed_job_count: int = Field(ge=0)
    agent_count: int = Field(ge=0)
    conversation_count: int = Field(ge=0)


class DashboardRecentJobResponse(BaseModel):
    """One recent ingestion job projected for dashboard activity views."""

    job_id: UUID
    document_id: UUID
    dataset_id: UUID
    document_title: str | None = None
    status: IngestionJobStatus
    attempt_count: int = Field(ge=0)
    error_code: str | None = None
    error_detail: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
