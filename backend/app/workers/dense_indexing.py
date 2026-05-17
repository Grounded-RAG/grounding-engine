"""Dense-indexing worker entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session_factory
from app.models import DocumentStatus, IngestionJobStatus
from app.services.dense_indexing import DenseIndexingResult, dense_index_document
from app.services.ingestion import load_ingestion_job_context


@dataclass(frozen=True)
class DenseIndexingRunResult:
    """Worker result returned after dense indexing chunk manifests."""

    job_id: UUID
    document_id: UUID
    status: IngestionJobStatus
    document_status: DocumentStatus
    collection_name: str
    points_indexed: int
    vector_dimensions: int


async def run_dense_indexing_job(
    job_id: UUID,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> DenseIndexingRunResult:
    """Run dense indexing for a currently active ingestion job."""

    factory = session_factory or get_session_factory()

    async with factory() as session:
        context = await load_ingestion_job_context(
            session=session,
            job_id=job_id,
            allowed_statuses={IngestionJobStatus.RUNNING},
        )

    dense_result: DenseIndexingResult = await dense_index_document(context)
    return DenseIndexingRunResult(
        job_id=context.job_id,
        document_id=context.document_id,
        status=IngestionJobStatus.RUNNING,
        document_status=DocumentStatus.PROCESSING,
        collection_name=dense_result.collection_name,
        points_indexed=dense_result.points_indexed,
        vector_dimensions=dense_result.vector_dimensions,
    )
