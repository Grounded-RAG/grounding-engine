"""Unit tests for dense indexing worker entrypoints."""

from __future__ import annotations

import uuid

import pytest

from app.models import DocumentStatus, IngestionJobStatus
from app.services.ingestion import IngestionJobContext
from app.workers.dense_indexing import run_dense_indexing_job


@pytest.mark.asyncio()
async def test_run_dense_indexing_job_loads_context_and_indexes(monkeypatch) -> None:
    """Dense indexing worker should load an active job and return processing state."""

    context = IngestionJobContext(
        job_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        namespace_id=uuid.uuid4(),
        object_key="tenants/t1/namespaces/n1/documents/d1/source/manual.txt",
        mime_type="text/plain",
        title="Manual",
        source_uri=None,
        attempt_count=1,
    )

    class _FactoryContext:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

    class _SessionFactory:
        def __call__(self):
            return _FactoryContext()

    async def fake_load_ingestion_job_context(*, session, job_id, allowed_statuses):
        del session
        assert job_id == context.job_id
        assert allowed_statuses == {IngestionJobStatus.RUNNING}
        return context

    async def fake_dense_index_document(loaded_context):
        assert loaded_context == context

        from app.services.dense_indexing import DenseIndexingResult

        return DenseIndexingResult(
            collection_name="grounded_chunks",
            points_indexed=3,
            vector_dimensions=128,
            manifest_key="manifest.json",
        )

    monkeypatch.setattr(
        "app.workers.dense_indexing.load_ingestion_job_context",
        fake_load_ingestion_job_context,
    )
    monkeypatch.setattr(
        "app.workers.dense_indexing.dense_index_document",
        fake_dense_index_document,
    )

    result = await run_dense_indexing_job(
        context.job_id,
        session_factory=_SessionFactory(),
    )

    assert result.job_id == context.job_id
    assert result.document_id == context.document_id
    assert result.status is IngestionJobStatus.RUNNING
    assert result.document_status is DocumentStatus.PROCESSING
    assert result.collection_name == "grounded_chunks"
    assert result.points_indexed == 3
    assert result.vector_dimensions == 128
