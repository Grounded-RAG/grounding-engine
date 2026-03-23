"""Sparse-indexing worker entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session_factory
from app.models import DocumentStatus, IngestionJobStatus
from app.services.ingestion import (
    IngestionRunResult,
    load_ingestion_job_context,
    mark_ingestion_job_indexed,
)
from app.services.sparse_indexing import SparseIndexingResult, sparse_index_document


@dataclass(frozen=True)
class SparseIndexingRunResult:
    """Worker result returned after sparse indexing chunk manifests."""

    run: IngestionRunResult
    rows_indexed: int
    manifest_key: str


async def run_sparse_indexing_job(
    job_id: UUID,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> SparseIndexingRunResult:
    """Run sparse indexing and finalize the ingestion job as indexed."""

    factory = session_factory or get_session_factory()

    async with factory() as session:
        context = await load_ingestion_job_context(
            session=session,
            job_id=job_id,
            allowed_statuses={IngestionJobStatus.RUNNING},
        )
        sparse_result: SparseIndexingResult = await sparse_index_document(
            session=session,
            context=context,
        )
        run_result = await mark_ingestion_job_indexed(
            session=session,
            job_id=job_id,
        )

    assert run_result.status is IngestionJobStatus.INDEXED
    assert run_result.document_status is DocumentStatus.INDEXED
    return SparseIndexingRunResult(
        run=run_result,
        rows_indexed=sparse_result.rows_indexed,
        manifest_key=sparse_result.manifest_key,
    )
