"""Integration tests for ingestion worker lifecycle handling."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass

import psycopg
import pytest

from app.config import get_settings
from app.core.database import dispose_database, get_session_factory
from app.models import (
    DocumentStatus,
    ExecutionTier,
    FreshnessProfile,
    IngestionJobStatus,
    SensitivityLevel,
    SubscriptionPlan,
)
from app.services.ingestion import (
    IngestionProcessorError,
    claim_ingestion_job,
    mark_ingestion_job_failed,
)
from app.workers.ingestion import run_ingestion_job


@dataclass(frozen=True)
class SeededIngestionJobData:
    """Seeded tenant, document, and ingestion job rows for worker tests."""

    tenant_id: uuid.UUID
    namespace_id: uuid.UUID
    document_id: uuid.UUID
    job_id: uuid.UUID


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def seeded_ingestion_job() -> SeededIngestionJobData:
    """Seed one queued ingestion job and its source document."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    job_id = uuid.uuid4()

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into tenants (
                    tenant_id,
                    name,
                    subscription_plan,
                    max_execution_tier,
                    default_policy,
                    retention_days
                )
                values (%s, %s, %s, %s, %s::jsonb, %s)
                """,
                (
                    tenant_id,
                    f"tenant-{tenant_id}",
                    SubscriptionPlan.PRO.value,
                    ExecutionTier.ENTERPRISE.value,
                    json.dumps({"tier": "standard"}),
                    365,
                ),
            )
            cursor.execute(
                """
                insert into namespaces (
                    namespace_id,
                    tenant_id,
                    name,
                    domain,
                    sensitivity_level,
                    freshness_profile,
                    min_execution_tier,
                    allow_web_fallback,
                    allow_internal_model_retrieval
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    namespace_id,
                    tenant_id,
                    "primary",
                    "general",
                    SensitivityLevel.INTERNAL.value,
                    FreshnessProfile.BALANCED.value,
                    ExecutionTier.STANDARD.value,
                    False,
                    False,
                ),
            )
            cursor.execute(
                """
                insert into documents (
                    doc_id,
                    tenant_id,
                    namespace_id,
                    object_key,
                    source_uri,
                    mime_type,
                    title,
                    checksum,
                    file_size_bytes,
                    status
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    document_id,
                    tenant_id,
                    namespace_id,
                    f"tenants/{tenant_id}/namespaces/{namespace_id}/documents/{document_id}/source/source.txt",
                    f"s3://grounded-documents/tenants/{tenant_id}/namespaces/{namespace_id}/documents/{document_id}/source/source.txt",
                    "text/plain",
                    "Seeded document",
                    uuid.uuid4().hex + uuid.uuid4().hex,
                    128,
                    DocumentStatus.UPLOADED.value,
                ),
            )
            cursor.execute(
                """
                insert into ingestion_jobs (
                    job_id,
                    tenant_id,
                    doc_id,
                    status
                )
                values (%s, %s, %s, %s)
                """,
                (
                    job_id,
                    tenant_id,
                    document_id,
                    IngestionJobStatus.QUEUED.value,
                ),
            )

    yield SeededIngestionJobData(
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        document_id=document_id,
        job_id=job_id,
    )

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from ingestion_jobs where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from documents where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from namespaces where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from tenants where tenant_id = %s", (tenant_id,))
    asyncio.run(dispose_database())


def _fetch_job_and_document(job_id: uuid.UUID, tenant_id: uuid.UUID) -> tuple[tuple, tuple]:
    """Fetch persisted ingestion job and document state from Postgres."""

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select status, attempt_count, error_code, error_detail, started_at, completed_at
                from ingestion_jobs
                where job_id = %s and tenant_id = %s
                """,
                (job_id, tenant_id),
            )
            job_row = cursor.fetchone()
            cursor.execute(
                """
                select status
                from documents
                where tenant_id = %s and doc_id = (
                    select doc_id from ingestion_jobs where job_id = %s
                )
                """,
                (tenant_id, job_id),
            )
            document_row = cursor.fetchone()
    assert job_row is not None
    assert document_row is not None
    return job_row, document_row


def test_claim_ingestion_job_marks_running_and_processing(
    seeded_ingestion_job: SeededIngestionJobData,
) -> None:
    """Claiming a queued job should transition it into active processing."""

    async def _run() -> None:
        async with get_session_factory()() as session:
            context = await claim_ingestion_job(
                session=session,
                job_id=seeded_ingestion_job.job_id,
            )

        assert context.job_id == seeded_ingestion_job.job_id
        assert context.document_id == seeded_ingestion_job.document_id
        assert context.namespace_id == seeded_ingestion_job.namespace_id
        assert context.attempt_count == 1

    asyncio.run(_run())

    job_row, document_row = _fetch_job_and_document(
        seeded_ingestion_job.job_id,
        seeded_ingestion_job.tenant_id,
    )
    assert job_row[0] == "running"
    assert job_row[1] == 1
    assert job_row[2] is None
    assert job_row[3] is None
    assert job_row[4] is not None
    assert job_row[5] is None
    assert document_row[0] == "processing"


def test_mark_ingestion_job_failed_persists_failure_details(
    seeded_ingestion_job: SeededIngestionJobData,
) -> None:
    """Failing a job should persist the reason and fail the source document too."""

    async def _run() -> None:
        async with get_session_factory()() as session:
            await claim_ingestion_job(
                session=session,
                job_id=seeded_ingestion_job.job_id,
            )

        async with get_session_factory()() as session:
            failure = await mark_ingestion_job_failed(
                session=session,
                job_id=seeded_ingestion_job.job_id,
                error_code="EXTRACTION_FAILED",
                error_detail="Document text extraction failed.",
            )

        assert failure.status is IngestionJobStatus.FAILED
        assert failure.document_status is DocumentStatus.FAILED
        assert failure.error_code == "EXTRACTION_FAILED"

    asyncio.run(_run())

    job_row, document_row = _fetch_job_and_document(
        seeded_ingestion_job.job_id,
        seeded_ingestion_job.tenant_id,
    )
    assert job_row[0] == "failed"
    assert job_row[2] == "EXTRACTION_FAILED"
    assert job_row[3] == "Document text extraction failed."
    assert job_row[5] is not None
    assert document_row[0] == "failed"


def test_run_ingestion_job_marks_failure_for_processor_error(
    seeded_ingestion_job: SeededIngestionJobData,
) -> None:
    """Worker scaffold should translate processor failures into job failures."""

    async def _processor(_context) -> None:
        raise IngestionProcessorError(
            "INGESTION_STAGE_NOT_READY",
            "Downstream ingestion stages are not implemented yet.",
        )

    result = asyncio.run(
        run_ingestion_job(
            seeded_ingestion_job.job_id,
            processor=_processor,
        )
    )

    assert result.status is IngestionJobStatus.FAILED
    assert result.document_status is DocumentStatus.FAILED

    job_row, document_row = _fetch_job_and_document(
        seeded_ingestion_job.job_id,
        seeded_ingestion_job.tenant_id,
    )
    assert job_row[0] == "failed"
    assert job_row[1] == 1
    assert job_row[2] == "INGESTION_STAGE_NOT_READY"
    assert job_row[3] == "Downstream ingestion stages are not implemented yet."
    assert document_row[0] == "failed"


def test_run_ingestion_job_leaves_claimed_job_running_on_success(
    seeded_ingestion_job: SeededIngestionJobData,
) -> None:
    """Successful scaffold runs should leave the job active for downstream stages."""

    async def _processor(_context) -> None:
        return None

    result = asyncio.run(
        run_ingestion_job(
            seeded_ingestion_job.job_id,
            processor=_processor,
        )
    )

    assert result.status is IngestionJobStatus.RUNNING
    assert result.document_status is DocumentStatus.PROCESSING
    assert result.attempt_count == 1

    job_row, document_row = _fetch_job_and_document(
        seeded_ingestion_job.job_id,
        seeded_ingestion_job.tenant_id,
    )
    assert job_row[0] == "running"
    assert job_row[1] == 1
    assert job_row[4] is not None
    assert job_row[5] is None
    assert document_row[0] == "processing"
