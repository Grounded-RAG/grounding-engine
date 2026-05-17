"""Document and ingestion job API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentStatus, IngestionJobStatus


class DocumentUploadResponse(BaseModel):
    """Response returned after a document upload is accepted."""

    document_id: UUID
    namespace_id: UUID
    job_id: UUID
    filename: str
    title: str
    mime_type: str
    file_size_bytes: int
    document_status: DocumentStatus
    job_status: IngestionJobStatus
    already_exists: bool = False


class IngestionJobStatusResponse(BaseModel):
    """Tenant-scoped ingestion job status response."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: UUID
    document_id: UUID
    status: IngestionJobStatus
    attempt_count: int
    error_code: str | None
    error_detail: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class DocumentReindexResponse(BaseModel):
    """Response returned after a document is queued for reindexing."""

    document_id: UUID
    namespace_id: UUID
    job_id: UUID
    document_status: DocumentStatus
    job_status: IngestionJobStatus
