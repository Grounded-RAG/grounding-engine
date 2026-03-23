"""Background ingestion worker entrypoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session_factory
from app.models import DocumentStatus, IngestionJobStatus
from app.services.ingestion import (
    IngestionJobContext,
    IngestionProcessorError,
    IngestionRunResult,
    claim_ingestion_job,
    mark_ingestion_job_failed,
)


Processor = Callable[[IngestionJobContext], Awaitable[None]]


async def run_ingestion_job(
    job_id: UUID,
    *,
    processor: Processor,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> IngestionRunResult:
    """Claim an ingestion job, invoke a processor, and fail cleanly on errors."""

    factory = session_factory or get_session_factory()

    async with factory() as session:
        context = await claim_ingestion_job(session=session, job_id=job_id)

    try:
        await processor(context)
    except IngestionProcessorError as exc:
        async with factory() as session:
            failure = await mark_ingestion_job_failed(
                session=session,
                job_id=job_id,
                error_code=exc.error_code,
                error_detail=exc.detail,
            )
        return IngestionRunResult(
            job_id=failure.job_id,
            document_id=failure.document_id,
            status=failure.status,
            document_status=failure.document_status,
            attempt_count=context.attempt_count,
        )
    except Exception as exc:
        async with factory() as session:
            await mark_ingestion_job_failed(
                session=session,
                job_id=job_id,
                error_code="INGESTION_UNEXPECTED_ERROR",
                error_detail=str(exc),
            )
        raise

    return IngestionRunResult(
        job_id=context.job_id,
        document_id=context.document_id,
        status=IngestionJobStatus.RUNNING,
        document_status=DocumentStatus.PROCESSING,
        attempt_count=context.attempt_count,
    )
