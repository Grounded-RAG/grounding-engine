"""Chunking-stage worker entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session_factory
from app.models import DocumentStatus, IngestionJobStatus
from app.services.chunking import ChunkedDocumentArtifact, chunk_extracted_document
from app.services.ingestion import load_ingestion_job_context


@dataclass(frozen=True)
class ChunkingRunResult:
    """Worker result returned after chunking an extracted document."""

    job_id: UUID
    document_id: UUID
    status: IngestionJobStatus
    document_status: DocumentStatus
    manifest_key: str
    chunk_count: int


async def run_chunking_job(
    job_id: UUID,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> ChunkingRunResult:
    """Run deterministic chunking for a currently active ingestion job."""

    factory = session_factory or get_session_factory()

    async with factory() as session:
        context = await load_ingestion_job_context(
            session=session,
            job_id=job_id,
            allowed_statuses={IngestionJobStatus.RUNNING},
        )

    chunked_artifact: ChunkedDocumentArtifact = await chunk_extracted_document(context)
    return ChunkingRunResult(
        job_id=context.job_id,
        document_id=context.document_id,
        status=IngestionJobStatus.RUNNING,
        document_status=DocumentStatus.PROCESSING,
        manifest_key=chunked_artifact.manifest_key,
        chunk_count=chunked_artifact.chunk_count,
    )
