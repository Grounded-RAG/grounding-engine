"""Unit tests for sparse indexing worker entrypoints."""

from __future__ import annotations

import uuid

import pytest

from app.models import DocumentStatus, IngestionJobStatus
from app.services.ingestion import IngestionJobContext, IngestionRunResult
from app.workers.sparse_indexing import run_sparse_indexing_job


@pytest.mark.asyncio()
async def test_run_sparse_indexing_job_indexes_and_finalizes(monkeypatch) -> None:
    """Sparse indexing worker should finalize a running ingestion job as indexed."""

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

    async def fake_sparse_index_document(*, session, context):
        del session, context

        from app.services.sparse_indexing import SparseIndexingResult

        return SparseIndexingResult(
            rows_indexed=3,
            manifest_key="manifest.json",
        )

    async def fake_mark_ingestion_job_indexed(*, session, job_id):
        del session
        assert job_id == context.job_id
        return IngestionRunResult(
            job_id=context.job_id,
            document_id=context.document_id,
            status=IngestionJobStatus.INDEXED,
            document_status=DocumentStatus.INDEXED,
            attempt_count=1,
        )

    monkeypatch.setattr(
        "app.workers.sparse_indexing.load_ingestion_job_context",
        fake_load_ingestion_job_context,
    )
    monkeypatch.setattr(
        "app.workers.sparse_indexing.sparse_index_document",
        fake_sparse_index_document,
    )
    monkeypatch.setattr(
        "app.workers.sparse_indexing.mark_ingestion_job_indexed",
        fake_mark_ingestion_job_indexed,
    )

    result = await run_sparse_indexing_job(
        context.job_id,
        session_factory=_SessionFactory(),
    )

    assert result.run.status is IngestionJobStatus.INDEXED
    assert result.run.document_status is DocumentStatus.INDEXED
    assert result.rows_indexed == 3
    assert result.manifest_key == "manifest.json"
