"""Phase 1 Standard ingestion pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session_factory
from app.core.telemetry import get_logger
from app.models import DocumentStatus, IngestionJobStatus
from app.services.ingestion import (
    IngestionFailureResult,
    IngestionProcessorError,
    IngestionServiceError,
    mark_ingestion_job_failed,
)
from app.workers.chunking import ChunkingRunResult, run_chunking_job
from app.workers.dense_indexing import DenseIndexingRunResult, run_dense_indexing_job
from app.workers.extraction import ExtractionRunResult, run_extraction_job
from app.workers.sparse_indexing import SparseIndexingRunResult, run_sparse_indexing_job


logger = get_logger("app.ingestion")


@dataclass(frozen=True)
class StandardIngestionPipelineResult:
    """Final result for the Standard ingestion pipeline."""

    job_id: UUID
    document_id: UUID
    status: IngestionJobStatus
    document_status: DocumentStatus
    extraction_artifact_key: str | None
    chunk_manifest_key: str | None
    dense_points_indexed: int
    sparse_rows_indexed: int


async def _mark_pipeline_failed(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    job_id: UUID,
    error_code: str,
    error_detail: str,
) -> StandardIngestionPipelineResult:
    """Persist a clean pipeline failure for downstream stages."""

    async with session_factory() as session:
        failure: IngestionFailureResult = await mark_ingestion_job_failed(
            session=session,
            job_id=job_id,
            error_code=error_code,
            error_detail=error_detail,
        )

    return StandardIngestionPipelineResult(
        job_id=failure.job_id,
        document_id=failure.document_id,
        status=failure.status,
        document_status=failure.document_status,
        extraction_artifact_key=None,
        chunk_manifest_key=None,
        dense_points_indexed=0,
        sparse_rows_indexed=0,
    )


async def run_standard_ingestion_pipeline(
    job_id: UUID,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> StandardIngestionPipelineResult:
    """Run the full Standard ingestion pipeline for one queued job."""

    factory = session_factory or get_session_factory()

    try:
        extraction: ExtractionRunResult = await run_extraction_job(
            job_id,
            session_factory=factory,
        )
    except IngestionServiceError as exc:
        return await _mark_pipeline_failed(
            session_factory=factory,
            job_id=job_id,
            error_code="INGESTION_PIPELINE_STATE_ERROR",
            error_detail=str(exc),
        )
    except Exception as exc:
        return await _mark_pipeline_failed(
            session_factory=factory,
            job_id=job_id,
            error_code="INGESTION_PIPELINE_UNEXPECTED_ERROR",
            error_detail=str(exc),
        )

    if extraction.run.status is IngestionJobStatus.FAILED:
        return StandardIngestionPipelineResult(
            job_id=extraction.run.job_id,
            document_id=extraction.run.document_id,
            status=extraction.run.status,
            document_status=extraction.run.document_status,
            extraction_artifact_key=(
                extraction.extracted_document.artifact_key
                if extraction.extracted_document is not None
                else None
            ),
            chunk_manifest_key=None,
            dense_points_indexed=0,
            sparse_rows_indexed=0,
        )

    try:
        chunking: ChunkingRunResult = await run_chunking_job(
            job_id,
            session_factory=factory,
        )
        dense: DenseIndexingRunResult = await run_dense_indexing_job(
            job_id,
            session_factory=factory,
        )
        sparse: SparseIndexingRunResult = await run_sparse_indexing_job(
            job_id,
            session_factory=factory,
        )
    except IngestionProcessorError as exc:
        return await _mark_pipeline_failed(
            session_factory=factory,
            job_id=job_id,
            error_code=exc.error_code,
            error_detail=exc.detail,
        )
    except IngestionServiceError as exc:
        return await _mark_pipeline_failed(
            session_factory=factory,
            job_id=job_id,
            error_code="INGESTION_PIPELINE_STATE_ERROR",
            error_detail=str(exc),
        )
    except Exception as exc:
        return await _mark_pipeline_failed(
            session_factory=factory,
            job_id=job_id,
            error_code="INGESTION_PIPELINE_UNEXPECTED_ERROR",
            error_detail=str(exc),
        )

    return StandardIngestionPipelineResult(
        job_id=sparse.run.job_id,
        document_id=sparse.run.document_id,
        status=sparse.run.status,
        document_status=sparse.run.document_status,
        extraction_artifact_key=(
            extraction.extracted_document.artifact_key
            if extraction.extracted_document is not None
            else None
        ),
        chunk_manifest_key=chunking.manifest_key,
        dense_points_indexed=dense.points_indexed,
        sparse_rows_indexed=sparse.rows_indexed,
    )


async def run_standard_ingestion_pipeline_background(
    job_id: UUID,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Run the Standard ingestion pipeline in a background-safe wrapper."""

    try:
        result = await run_standard_ingestion_pipeline(
            job_id,
            session_factory=session_factory,
        )
    except Exception:
        logger.exception(
            "ingestion_pipeline_crashed",
            job_id=str(job_id),
        )
        return

    if result.status is IngestionJobStatus.FAILED:
        logger.warning(
            "ingestion_pipeline_failed",
            job_id=str(result.job_id),
            document_id=str(result.document_id),
            status=result.status.value,
        )
        return

    logger.info(
        "ingestion_pipeline_completed",
        job_id=str(result.job_id),
        document_id=str(result.document_id),
        status=result.status.value,
        dense_points_indexed=result.dense_points_indexed,
        sparse_rows_indexed=result.sparse_rows_indexed,
    )
