"""Services for managing ingestion job lifecycle transitions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import DocumentStatus, IngestionJob, IngestionJobStatus


class IngestionServiceError(RuntimeError):
    """Raised when ingestion lifecycle operations cannot be completed."""


class IngestionProcessorError(RuntimeError):
    """Raised by ingestion processors when a job should fail cleanly."""

    def __init__(self, error_code: str, detail: str) -> None:
        super().__init__(detail)
        self.error_code = error_code
        self.detail = detail


@dataclass(frozen=True)
class IngestionJobContext:
    """Worker-facing context for a claimed ingestion job."""

    job_id: uuid.UUID
    tenant_id: uuid.UUID
    document_id: uuid.UUID
    namespace_id: uuid.UUID
    object_key: str
    mime_type: str
    title: str | None
    source_uri: str | None
    attempt_count: int


@dataclass(frozen=True)
class IngestionFailureResult:
    """Failure details returned after marking an ingestion job failed."""

    job_id: uuid.UUID
    document_id: uuid.UUID
    status: IngestionJobStatus
    document_status: DocumentStatus
    error_code: str
    error_detail: str


@dataclass(frozen=True)
class IngestionRunResult:
    """Worker result returned after starting or failing a job."""

    job_id: uuid.UUID
    document_id: uuid.UUID
    status: IngestionJobStatus
    document_status: DocumentStatus
    attempt_count: int


async def _get_ingestion_job_with_document(
    *,
    session: AsyncSession,
    job_id: uuid.UUID,
    for_update: bool = False,
) -> IngestionJob | None:
    """Fetch an ingestion job with its document relationship loaded."""

    statement = (
        select(IngestionJob)
        .options(selectinload(IngestionJob.document))
        .where(IngestionJob.job_id == job_id)
    )
    if for_update:
        statement = statement.with_for_update()

    result = await session.execute(statement)
    return result.scalar_one_or_none()


def _build_context(job: IngestionJob) -> IngestionJobContext:
    """Translate a claimed ingestion job into worker context."""

    if job.document is None:
        raise IngestionServiceError("Ingestion job document binding is invalid.")

    return IngestionJobContext(
        job_id=job.job_id,
        tenant_id=job.tenant_id,
        document_id=job.doc_id,
        namespace_id=job.document.namespace_id,
        object_key=job.document.object_key,
        mime_type=job.document.mime_type,
        title=job.document.title,
        source_uri=job.document.source_uri,
        attempt_count=job.attempt_count,
    )


async def claim_ingestion_job(
    *,
    session: AsyncSession,
    job_id: uuid.UUID,
) -> IngestionJobContext:
    """Claim a queued ingestion job and transition it into running state."""

    job = await _get_ingestion_job_with_document(
        session=session,
        job_id=job_id,
        for_update=True,
    )
    if job is None:
        raise IngestionServiceError("Ingestion job not found.")
    if job.document is None:
        raise IngestionServiceError("Ingestion job document binding is invalid.")
    if job.status is not IngestionJobStatus.QUEUED:
        raise IngestionServiceError("Ingestion job is not available to claim.")

    job.status = IngestionJobStatus.RUNNING
    job.attempt_count += 1
    job.started_at = datetime.now(UTC)
    job.completed_at = None
    job.error_code = None
    job.error_detail = None
    job.document.status = DocumentStatus.PROCESSING

    await session.commit()
    await session.refresh(job)
    return _build_context(job)


async def mark_ingestion_job_failed(
    *,
    session: AsyncSession,
    job_id: uuid.UUID,
    error_code: str,
    error_detail: str,
) -> IngestionFailureResult:
    """Mark an ingestion job and its document as failed."""

    job = await _get_ingestion_job_with_document(
        session=session,
        job_id=job_id,
        for_update=True,
    )
    if job is None:
        raise IngestionServiceError("Ingestion job not found.")
    if job.document is None:
        raise IngestionServiceError("Ingestion job document binding is invalid.")

    job.status = IngestionJobStatus.FAILED
    job.error_code = error_code
    job.error_detail = error_detail
    job.completed_at = datetime.now(UTC)
    job.document.status = DocumentStatus.FAILED

    await session.commit()
    await session.refresh(job)
    return IngestionFailureResult(
        job_id=job.job_id,
        document_id=job.doc_id,
        status=job.status,
        document_status=job.document.status,
        error_code=job.error_code or error_code,
        error_detail=job.error_detail or error_detail,
    )
