"""Unit tests for sparse indexing helpers."""

from __future__ import annotations

import json
import uuid

import pytest

from app.pipeline.contracts import ChunkManifest
from app.services.ingestion import IngestionJobContext, IngestionProcessorError
from app.services.sparse_indexing import sparse_index_document


class FakeAsyncSession:
    """Minimal async session stub for sparse indexing tests."""

    def __init__(self) -> None:
        self.calls: list[object] = []
        self.rollback_called = False
        self.flush_called = False

    async def execute(self, statement, params=None):
        self.calls.append((statement, params))
        return None

    async def flush(self) -> None:
        self.flush_called = True

    async def rollback(self) -> None:
        self.rollback_called = True


@pytest.mark.asyncio()
async def test_sparse_index_document_rewrites_chunk_rows(monkeypatch) -> None:
    """Sparse indexing should replace existing rows with the current chunk manifest."""

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
    manifest = ChunkManifest.from_payload(
        {
            "document_id": str(context.document_id),
            "source_artifact_key": (
                "tenants/t1/namespaces/n1/documents/d1/artifacts/extracted/text.txt"
            ),
            "chunking_strategy": "deterministic_token_window_v1",
            "chunks": [
                {
                    "chunk_id": "chunk-1",
                    "chunk_index": 0,
                    "text": "alpha beta",
                    "token_count": 2,
                    "character_count": 10,
                    "start_token": 0,
                    "end_token": 1,
                },
                {
                    "chunk_id": "chunk-2",
                    "chunk_index": 1,
                    "text": "gamma delta",
                    "token_count": 2,
                    "character_count": 11,
                    "start_token": 2,
                    "end_token": 3,
                },
            ],
        }
    )

    async def fake_download_bytes(key: str) -> bytes:
        assert key.endswith("/artifacts/chunks/manifest.json")
        return json.dumps(manifest.to_payload()).encode("utf-8")

    monkeypatch.setattr("app.services.sparse_indexing.download_bytes", fake_download_bytes)
    session = FakeAsyncSession()

    result = await sparse_index_document(session=session, context=context)

    assert result.rows_indexed == 2
    assert result.manifest_key.endswith("/artifacts/chunks/manifest.json")
    assert len(session.calls) == 2
    delete_call, insert_call = session.calls
    assert delete_call[1] is None
    assert insert_call[1] is not None
    inserted_rows = insert_call[1]
    assert isinstance(inserted_rows, list)
    assert inserted_rows[0]["tenant_id"] == context.tenant_id
    assert inserted_rows[0]["chunk_text"] == "alpha beta"
    assert session.flush_called is True


@pytest.mark.asyncio()
async def test_sparse_index_document_rejects_invalid_manifest(monkeypatch) -> None:
    """Invalid chunk manifests should fail with a clean ingestion error."""

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

    async def fake_download_bytes(key: str) -> bytes:
        del key
        return b"{not valid json"

    monkeypatch.setattr("app.services.sparse_indexing.download_bytes", fake_download_bytes)

    with pytest.raises(IngestionProcessorError, match="could not be parsed"):
        await sparse_index_document(session=FakeAsyncSession(), context=context)
