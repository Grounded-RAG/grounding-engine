"""Integration tests for deterministic chunking worker processing."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from types import SimpleNamespace

import psycopg
import pytest

from app.config import get_settings
from app.core.database import dispose_database
from app.core.storage import StorageError
from app.models import (
    DocumentStatus,
    ExecutionTier,
    FreshnessProfile,
    IngestionJobStatus,
    SensitivityLevel,
    SubscriptionPlan,
)
from app.services.chunking import derive_chunk_manifest_key
from app.services.extraction import derive_extracted_text_key
from app.workers.chunking import run_chunking_job


@dataclass(frozen=True)
class SeededChunkingJobData:
    """Seeded running ingestion job data for chunking tests."""

    tenant_id: uuid.UUID
    namespace_id: uuid.UUID
    document_id: uuid.UUID
    job_id: uuid.UUID
    object_key: str


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def object_store(monkeypatch) -> dict[str, bytes]:
    """Provide an in-memory object store for chunking worker tests."""

    objects: dict[str, bytes] = {}

    async def fake_download_bytes(key: str) -> bytes:
        try:
            return objects[key]
        except KeyError as exc:
            raise StorageError("Object not found in fake storage.") from exc

    async def fake_upload_bytes(
        key: str,
        payload: bytes,
        *,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> SimpleNamespace:
        del content_type, metadata
        objects[key] = payload
        return SimpleNamespace(key=key, size=len(payload))

    monkeypatch.setattr("app.services.chunking.download_bytes", fake_download_bytes)
    monkeypatch.setattr("app.services.chunking.upload_bytes", fake_upload_bytes)
    return objects


@pytest.fixture()
def chunking_env(monkeypatch) -> None:
    """Use a small deterministic chunk window for integration tests."""

    monkeypatch.setenv("CHUNK_MAX_TOKENS", "4")
    monkeypatch.setenv("CHUNK_OVERLAP_TOKENS", "1")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def seeded_chunking_job(
    chunking_env: None,
    object_store: dict[str, bytes],
) -> SeededChunkingJobData:
    """Seed one running ingestion job with an extracted text artifact."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    job_id = uuid.uuid4()
    object_key = (
        f"tenants/{tenant_id}/namespaces/{namespace_id}/documents/{document_id}/source/manual.txt"
    )
    extracted_key = derive_extracted_text_key(object_key)

    object_store[extracted_key] = b"one two three four five six seven eight nine"

    with psycopg.connect(_sync_database_url(), connect_timeout=3) as connection:
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
                    object_key,
                    f"s3://grounded-documents/{object_key}",
                    "text/plain",
                    "manual",
                    uuid.uuid4().hex + uuid.uuid4().hex,
                    128,
                    DocumentStatus.PROCESSING.value,
                ),
            )
            cursor.execute(
                """
                insert into ingestion_jobs (
                    job_id,
                    tenant_id,
                    doc_id,
                    status,
                    attempt_count,
                    started_at
                )
                values (%s, %s, %s, %s, %s, now())
                """,
                (
                    job_id,
                    tenant_id,
                    document_id,
                    IngestionJobStatus.RUNNING.value,
                    1,
                ),
            )

    yield SeededChunkingJobData(
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        document_id=document_id,
        job_id=job_id,
        object_key=object_key,
    )

    object_store.pop(extracted_key, None)
    object_store.pop(derive_chunk_manifest_key(object_key), None)

    with psycopg.connect(_sync_database_url(), connect_timeout=3) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from ingestion_jobs where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from documents where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from namespaces where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from tenants where tenant_id = %s", (tenant_id,))
    asyncio.run(dispose_database())


def test_run_chunking_job_persists_deterministic_chunk_manifest(
    seeded_chunking_job: SeededChunkingJobData,
    object_store: dict[str, bytes],
) -> None:
    """Chunking should persist a manifest artifact while leaving the job active."""

    result = asyncio.run(run_chunking_job(seeded_chunking_job.job_id))

    assert result.status is IngestionJobStatus.RUNNING
    assert result.document_status is DocumentStatus.PROCESSING
    assert result.chunk_count == 3
    assert result.manifest_key == derive_chunk_manifest_key(seeded_chunking_job.object_key)

    manifest_payload = object_store[result.manifest_key].decode("utf-8")
    manifest = json.loads(manifest_payload)

    assert manifest["document_id"] == str(seeded_chunking_job.document_id)
    assert manifest["chunking_strategy"] == "structure_aware_v1"
    assert [chunk["text"] for chunk in manifest["chunks"]] == [
        "one two three four",
        "three four five six seven",
        "six seven eight nine",
    ]
    assert [chunk["token_count"] for chunk in manifest["chunks"]] == [4, 5, 4]

    with psycopg.connect(_sync_database_url(), connect_timeout=3) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select status, attempt_count from ingestion_jobs where job_id = %s",
                (seeded_chunking_job.job_id,),
            )
            job_row = cursor.fetchone()
            cursor.execute(
                "select status from documents where doc_id = %s",
                (seeded_chunking_job.document_id,),
            )
            document_row = cursor.fetchone()

    assert job_row == ("running", 1)
    assert document_row == ("processing",)
