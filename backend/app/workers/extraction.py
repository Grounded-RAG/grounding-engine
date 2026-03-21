"""Extraction-stage worker entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session_factory
from app.services.extraction import (
    ExtractedDocument,
    extract_document_artifact,
    persist_enriched_document_metadata,
)
from app.services.ingestion import IngestionRunResult
from app.workers.ingestion import run_ingestion_job


@dataclass(frozen=True)
class ExtractionRunResult:
    """Combined worker result for the extraction stage."""

    run: IngestionRunResult
    extracted_document: ExtractedDocument | None


async def run_extraction_job(
    job_id: UUID,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> ExtractionRunResult:
    """Run the extraction stage for a claimed ingestion job."""

    factory = session_factory or get_session_factory()
    extracted: ExtractedDocument | None = None

    async def _processor(context) -> None:
        nonlocal extracted
        extracted = await extract_document_artifact(context)
        async with factory() as session:
            await persist_enriched_document_metadata(
                session=session,
                tenant_id=context.tenant_id,
                document_id=context.document_id,
                extracted_document=extracted,
            )

    run_result = await run_ingestion_job(
        job_id,
        processor=_processor,
        session_factory=factory,
    )

    return ExtractionRunResult(
        run=run_result,
        extracted_document=extracted,
    )
