"""Unit tests for Standard ingestion pipeline orchestration."""

from __future__ import annotations

import uuid

import pytest

from app.models import DocumentStatus, IngestionJobStatus
from app.services.ingestion import (
    IngestionFailureResult,
    IngestionProcessorError,
    IngestionRunResult,
)
from app.workers.pipeline import run_standard_ingestion_pipeline


class _FactoryContext:
    """Tiny async context manager used to fake a session factory."""

    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        del exc_type, exc, tb
        return False


class _SessionFactory:
    """Fake session factory compatible with the pipeline helpers."""

    def __call__(self):
        return _FactoryContext()


@pytest.mark.asyncio()
async def test_run_standard_ingestion_pipeline_completes_all_stages(monkeypatch) -> None:
    """The Standard pipeline should run extraction through sparse indexing in order."""

    job_id = uuid.uuid4()
    document_id = uuid.uuid4()
    stage_calls: list[str] = []

    async def fake_run_extraction_job(input_job_id, *, session_factory):
        assert input_job_id == job_id
        assert isinstance(session_factory, _SessionFactory)
        stage_calls.append("extraction")

        from app.workers.extraction import ExtractionRunResult

        return ExtractionRunResult(
            run=IngestionRunResult(
                job_id=job_id,
                document_id=document_id,
                status=IngestionJobStatus.RUNNING,
                document_status=DocumentStatus.PROCESSING,
                attempt_count=1,
            ),
            extracted_document=type(
                "ExtractedDocumentStub",
                (),
                {"artifact_key": "artifacts/extracted/text.txt"},
            )(),
        )

    async def fake_run_chunking_job(input_job_id, *, session_factory):
        assert input_job_id == job_id
        assert isinstance(session_factory, _SessionFactory)
        stage_calls.append("chunking")

        from app.workers.chunking import ChunkingRunResult

        return ChunkingRunResult(
            job_id=job_id,
            document_id=document_id,
            status=IngestionJobStatus.RUNNING,
            document_status=DocumentStatus.PROCESSING,
            manifest_key="artifacts/chunks/manifest.json",
            chunk_count=2,
        )

    async def fake_run_dense_indexing_job(input_job_id, *, session_factory):
        assert input_job_id == job_id
        assert isinstance(session_factory, _SessionFactory)
        stage_calls.append("dense")

        from app.workers.dense_indexing import DenseIndexingRunResult

        return DenseIndexingRunResult(
            job_id=job_id,
            document_id=document_id,
            status=IngestionJobStatus.RUNNING,
            document_status=DocumentStatus.PROCESSING,
            collection_name="grounded_chunks",
            points_indexed=2,
            vector_dimensions=128,
        )

    async def fake_run_sparse_indexing_job(input_job_id, *, session_factory):
        assert input_job_id == job_id
        assert isinstance(session_factory, _SessionFactory)
        stage_calls.append("sparse")

        from app.workers.sparse_indexing import SparseIndexingRunResult

        return SparseIndexingRunResult(
            run=IngestionRunResult(
                job_id=job_id,
                document_id=document_id,
                status=IngestionJobStatus.INDEXED,
                document_status=DocumentStatus.INDEXED,
                attempt_count=1,
            ),
            rows_indexed=2,
            manifest_key="artifacts/chunks/manifest.json",
        )

    monkeypatch.setattr(
        "app.workers.pipeline.run_extraction_job",
        fake_run_extraction_job,
    )
    monkeypatch.setattr(
        "app.workers.pipeline.run_chunking_job",
        fake_run_chunking_job,
    )
    monkeypatch.setattr(
        "app.workers.pipeline.run_dense_indexing_job",
        fake_run_dense_indexing_job,
    )
    monkeypatch.setattr(
        "app.workers.pipeline.run_sparse_indexing_job",
        fake_run_sparse_indexing_job,
    )

    result = await run_standard_ingestion_pipeline(
        job_id,
        session_factory=_SessionFactory(),
    )

    assert stage_calls == ["extraction", "chunking", "dense", "sparse"]
    assert result.status is IngestionJobStatus.INDEXED
    assert result.document_status is DocumentStatus.INDEXED
    assert result.extraction_artifact_key == "artifacts/extracted/text.txt"
    assert result.chunk_manifest_key == "artifacts/chunks/manifest.json"
    assert result.dense_points_indexed == 2
    assert result.sparse_rows_indexed == 2


@pytest.mark.asyncio()
async def test_run_standard_ingestion_pipeline_marks_failure_for_later_stage_errors(
    monkeypatch,
) -> None:
    """Later-stage processor errors should be translated into clean pipeline failures."""

    pipeline_job_id = uuid.uuid4()
    document_id = uuid.uuid4()

    async def fake_run_extraction_job(input_job_id, *, session_factory):
        assert input_job_id == pipeline_job_id
        assert isinstance(session_factory, _SessionFactory)

        from app.workers.extraction import ExtractionRunResult

        return ExtractionRunResult(
            run=IngestionRunResult(
                job_id=pipeline_job_id,
                document_id=document_id,
                status=IngestionJobStatus.RUNNING,
                document_status=DocumentStatus.PROCESSING,
                attempt_count=1,
            ),
            extracted_document=type(
                "ExtractedDocumentStub",
                (),
                {"artifact_key": "artifacts/extracted/text.txt"},
            )(),
        )

    async def fake_run_chunking_job(input_job_id, *, session_factory):
        assert input_job_id == pipeline_job_id
        assert isinstance(session_factory, _SessionFactory)
        raise IngestionProcessorError(
            "CHUNK_MANIFEST_UPLOAD_FAILED",
            "Failed to store the chunk manifest artifact.",
        )

    async def fake_mark_ingestion_job_failed(
        *,
        session,
        job_id: uuid.UUID,
        error_code: str,
        error_detail: str,
    ):
        del session
        assert job_id == pipeline_job_id
        assert error_code == "CHUNK_MANIFEST_UPLOAD_FAILED"
        assert error_detail == "Failed to store the chunk manifest artifact."
        return IngestionFailureResult(
            job_id=job_id,
            document_id=document_id,
            status=IngestionJobStatus.FAILED,
            document_status=DocumentStatus.FAILED,
            error_code=error_code,
            error_detail=error_detail,
        )

    monkeypatch.setattr(
        "app.workers.pipeline.run_extraction_job",
        fake_run_extraction_job,
    )
    monkeypatch.setattr(
        "app.workers.pipeline.run_chunking_job",
        fake_run_chunking_job,
    )
    monkeypatch.setattr(
        "app.workers.pipeline.mark_ingestion_job_failed",
        fake_mark_ingestion_job_failed,
    )

    result = await run_standard_ingestion_pipeline(
        pipeline_job_id,
        session_factory=_SessionFactory(),
    )

    assert result.status is IngestionJobStatus.FAILED
    assert result.document_status is DocumentStatus.FAILED
    assert result.dense_points_indexed == 0
    assert result.sparse_rows_indexed == 0
