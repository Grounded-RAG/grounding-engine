"""Reconciliation worker for stuck ingestion jobs.

Scans for ingestion jobs stuck in QUEUED or RUNNING beyond a configurable
timeout and transitions them to FAILED so they don't remain as zombie
entries indefinitely. Designed to be invoked periodically via cron, a
Kubernetes CronJob, or a simple scheduler.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session_factory
from app.models import DocumentStatus, IngestionJob, IngestionJobStatus, Document

logger = logging.getLogger(__name__)

# Jobs older than this threshold in QUEUED or RUNNING state are considered stuck.
DEFAULT_STUCK_THRESHOLD_MINUTES: int = 60


async def reconcile_stuck_ingestion_jobs(
    *,
    stuck_threshold_minutes: int = DEFAULT_STUCK_THRESHOLD_MINUTES,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> int:
    """Find and fail ingestion jobs stuck in transient states.

    Returns the number of jobs transitioned to FAILED.
    """

    factory = session_factory or get_session_factory()
    cutoff = datetime.now(UTC) - timedelta(minutes=stuck_threshold_minutes)
    reconciled_count = 0

    async with factory() as session:
        # Find stuck jobs: QUEUED or RUNNING and created/started before cutoff
        statement = select(IngestionJob).where(
            IngestionJob.status.in_([
                IngestionJobStatus.QUEUED,
                IngestionJobStatus.RUNNING,
            ]),
            IngestionJob.created_at < cutoff,
        )
        result = await session.execute(statement)
        stuck_jobs = list(result.scalars().all())

        if not stuck_jobs:
            logger.info("Reconciliation: no stuck ingestion jobs found.")
            return 0

        now = datetime.now(UTC)
        for job in stuck_jobs:
            original_status = job.status
            job.status = IngestionJobStatus.FAILED
            job.error_code = "RECONCILIATION_TIMEOUT"
            job.error_detail = (
                f"Job was stuck in {original_status.value} state since "
                f"{job.created_at.isoformat() if job.created_at else 'unknown'}. "
                f"Automatically failed by reconciliation worker after "
                f"{stuck_threshold_minutes} minute threshold."
            )
            job.completed_at = now

            # Also mark the parent document as failed if it's still PROCESSING
            doc_statement = (
                select(Document)
                .where(
                    Document.tenant_id == job.tenant_id,
                    Document.doc_id == job.doc_id,
                    Document.status.in_([
                        DocumentStatus.UPLOADED,
                        DocumentStatus.PROCESSING,
                    ]),
                )
            )
            doc_result = await session.execute(doc_statement)
            document = doc_result.scalar_one_or_none()
            if document is not None:
                document.status = DocumentStatus.FAILED

            reconciled_count += 1
            logger.warning(
                "Reconciliation: failed stuck job %s (was %s, tenant=%s, doc=%s)",
                job.job_id,
                original_status.value,
                job.tenant_id,
                job.doc_id,
            )

        await session.commit()
        logger.info(
            "Reconciliation: transitioned %d stuck jobs to FAILED.",
            reconciled_count,
        )

    return reconciled_count
