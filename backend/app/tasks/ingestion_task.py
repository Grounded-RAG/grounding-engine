"""ARQ tasks for background ingestion work."""

from __future__ import annotations

import uuid

from app.workers.pipeline import run_standard_ingestion_pipeline


async def ingest_document(ctx: dict, job_id: str) -> None:
    """Run the standard ingestion pipeline for one queued job."""

    del ctx
    await run_standard_ingestion_pipeline(uuid.UUID(job_id))
