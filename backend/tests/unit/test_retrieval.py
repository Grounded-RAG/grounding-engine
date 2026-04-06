"""Unit tests for sparse, dense, and fused retrieval helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.pipeline.contracts import FusedRetrievedChunk, RetrievedChunk
from app.services.retrieval import (
    dense_retrieve_chunks,
    fuse_retrieval_hits,
    retrieve_hybrid_candidates,
    sparse_retrieve_chunks,
)


class FakeAsyncResult:
    """Minimal mapping result wrapper for async SQL execution tests."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def mappings(self) -> "FakeAsyncResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self._rows


class FakeScalarQueryResult:
    """Minimal scalar iterable wrapper for ORM-style retrieval tests."""

    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> "FakeScalarQueryResult":
        return self

    def __iter__(self):
        return iter(self._rows)


class FakeAsyncSession:
    """Minimal async session stub for sparse retrieval tests."""

    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.executed = []

    async def execute(self, statement, params=None):
        self.executed.append((statement, params))
        return FakeAsyncResult(self.rows)


class ScalarAsyncSession(FakeAsyncSession):
    """Async session stub that returns ORM-like scalar rows."""

    async def execute(self, statement, params=None):
        self.executed.append((statement, params))
        return FakeScalarQueryResult(self.rows)


@pytest.mark.asyncio()
async def test_sparse_retrieve_chunks_maps_database_rows() -> None:
    """Sparse retrieval should convert DB rows into ordered retrieval hits."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    session = FakeAsyncSession(
        [
            {
                "chunk_id": "chunk-1",
                "tenant_id": tenant_id,
                "namespace_id": namespace_id,
                "doc_id": document_id,
                "chunk_index": 0,
                "chunk_text": "alpha beta",
                "score": 0.42,
            },
            {
                "chunk_id": "chunk-2",
                "tenant_id": tenant_id,
                "namespace_id": namespace_id,
                "doc_id": document_id,
                "chunk_index": 1,
                "chunk_text": "beta gamma",
                "score": 0.35,
            },
        ]
    )

    hits = await sparse_retrieve_chunks(
        session=session,
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        query_text="beta",
        limit=2,
    )

    assert [hit.chunk_id for hit in hits] == ["chunk-1", "chunk-2"]
    assert [hit.rank for hit in hits] == [1, 2]
    assert hits[0].source == "sparse"
    assert session.executed[0][1]["query_text"] == "beta"


@pytest.mark.asyncio()
async def test_dense_retrieve_chunks_maps_qdrant_points(monkeypatch) -> None:
    """Dense retrieval should convert Qdrant points into retrieval hits."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    async def fake_embed_texts(texts: list[str]):
        assert texts == ["alpha query"]
        from app.core.embeddings import DenseEmbedding

        return [DenseEmbedding(text="alpha query", vector=[0.1, 0.2, 0.3])]

    def fake_search_dense_points(*, query_vector, tenant_id, namespace_id, limit):
        assert query_vector == [0.1, 0.2, 0.3]
        assert limit == 3
        return [
            SimpleNamespace(
                score=0.9,
                payload={
                    "chunk_id": "chunk-1",
                    "tenant_id": str(tenant_id),
                    "namespace_id": str(namespace_id),
                    "document_id": str(document_id),
                    "chunk_index": 0,
                    "text": "alpha beta",
                },
            )
        ]

    monkeypatch.setattr("app.services.retrieval.embed_texts", fake_embed_texts)
    monkeypatch.setattr(
        "app.services.retrieval.search_dense_points",
        fake_search_dense_points,
    )

    hits = await dense_retrieve_chunks(
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        query_text="alpha query",
        limit=3,
    )

    assert len(hits) == 1
    assert hits[0].chunk_id == "chunk-1"
    assert hits[0].rank == 1
    assert hits[0].source == "dense"


def test_fuse_retrieval_hits_rewards_mutual_agreement() -> None:
    """RRF should rank chunks found by both paths above single-path candidates."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    sparse_hits = [
        RetrievedChunk(
            chunk_id="shared",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=document_id,
            chunk_index=0,
            text="shared text",
            score=0.8,
            rank=1,
            source="sparse",
        ),
        RetrievedChunk(
            chunk_id="sparse-only",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=document_id,
            chunk_index=1,
            text="sparse only",
            score=0.6,
            rank=2,
            source="sparse",
        ),
    ]
    dense_hits = [
        RetrievedChunk(
            chunk_id="dense-only",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=document_id,
            chunk_index=2,
            text="dense only",
            score=0.7,
            rank=1,
            source="dense",
        ),
        RetrievedChunk(
            chunk_id="shared",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=document_id,
            chunk_index=0,
            text="shared text",
            score=0.65,
            rank=2,
            source="dense",
        ),
    ]

    fused_hits = fuse_retrieval_hits(sparse_hits, dense_hits, rrf_k=60)

    assert isinstance(fused_hits[0], FusedRetrievedChunk)
    assert fused_hits[0].chunk_id == "shared"
    assert fused_hits[0].sources == ("dense", "sparse")
    assert {hit.chunk_id for hit in fused_hits} == {
        "shared",
        "sparse-only",
        "dense-only",
    }


@pytest.mark.asyncio()
async def test_retrieve_hybrid_candidates_runs_both_paths(monkeypatch) -> None:
    """Hybrid retrieval should return sparse, dense, and fused candidate sets."""

    sparse_hits = [
        RetrievedChunk(
            chunk_id="chunk-1",
            tenant_id=uuid.uuid4(),
            namespace_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            chunk_index=0,
            text="alpha beta",
            score=0.7,
            rank=1,
            source="sparse",
        )
    ]
    dense_hits = [
        RetrievedChunk(
            chunk_id="chunk-2",
            tenant_id=uuid.uuid4(),
            namespace_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            chunk_index=1,
            text="beta gamma",
            score=0.8,
            rank=1,
            source="dense",
        )
    ]

    async def fake_sparse_retrieve_chunks(**kwargs):
        assert kwargs["query_text"] == "beta query"
        return sparse_hits

    async def fake_dense_retrieve_chunks(**kwargs):
        assert kwargs["query_text"] == "beta query"
        return dense_hits

    monkeypatch.setattr(
        "app.services.retrieval.sparse_retrieve_chunks",
        fake_sparse_retrieve_chunks,
    )
    monkeypatch.setattr(
        "app.services.retrieval.dense_retrieve_chunks",
        fake_dense_retrieve_chunks,
    )

    bundle = await retrieve_hybrid_candidates(
        session=FakeAsyncSession([]),
        tenant_id=uuid.uuid4(),
        namespace_id=uuid.uuid4(),
        query_text="beta query",
        limit=4,
    )

    assert bundle.sparse_hits == sparse_hits
    assert bundle.dense_hits == dense_hits
    assert [hit.chunk_id for hit in bundle.fused_hits] == ["chunk-1", "chunk-2"]


@pytest.mark.asyncio()
async def test_retrieve_hybrid_candidates_reranks_for_answerable_name_query(monkeypatch) -> None:
    """Hybrid retrieval should surface more directly answerable chunks for field-style questions."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    sparse_hits = [
        RetrievedChunk(
            chunk_id="chunk-awards",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=document_id,
            chunk_index=3,
            text="Selected as 1 of 10 students for a prestigious ICT award.",
            score=0.8,
            rank=1,
            source="sparse",
        ),
        RetrievedChunk(
            chunk_id="chunk-name",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=document_id,
            chunk_index=0,
            text="Samrawit Gebremaryam Bahta\nsamrawit@example.com",
            score=0.2,
            rank=6,
            source="sparse",
        ),
    ]
    dense_hits = [
        RetrievedChunk(
            chunk_id="chunk-experience",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=document_id,
            chunk_index=2,
            text="AI Engineer at iCog Labs building grounded retrieval systems.",
            score=0.91,
            rank=1,
            source="dense",
        ),
        RetrievedChunk(
            chunk_id="chunk-name",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=document_id,
            chunk_index=0,
            text="Samrawit Gebremaryam Bahta\nsamrawit@example.com",
            score=0.51,
            rank=7,
            source="dense",
        ),
    ]

    async def fake_sparse_retrieve_chunks(**kwargs):
        assert kwargs["limit"] == 16
        return sparse_hits

    async def fake_dense_retrieve_chunks(**kwargs):
        assert kwargs["limit"] == 16
        return dense_hits

    monkeypatch.setattr(
        "app.services.retrieval.sparse_retrieve_chunks",
        fake_sparse_retrieve_chunks,
    )
    monkeypatch.setattr(
        "app.services.retrieval.dense_retrieve_chunks",
        fake_dense_retrieve_chunks,
    )

    bundle = await retrieve_hybrid_candidates(
        session=FakeAsyncSession([]),
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        query_text="What is the resume owner's name?",
        limit=4,
    )

    assert bundle.fused_hits[0].chunk_id == "chunk-name"


@pytest.mark.asyncio()
async def test_retrieve_hybrid_candidates_recovers_header_context_from_relevant_document(
    monkeypatch,
) -> None:
    """Header chunks from a relevant document should be recoverable even when initial hits miss them."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    sparse_hits = [
        RetrievedChunk(
            chunk_id="chunk-awards",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=document_id,
            chunk_index=4,
            text="AWARDS\nSelected for Huawei Seeds for the Future.",
            score=0.82,
            rank=1,
            source="sparse",
        )
    ]
    dense_hits = [
        RetrievedChunk(
            chunk_id="chunk-experience",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=document_id,
            chunk_index=2,
            text="PROFESSIONAL EXPERIENCE\nAI Engineer at iCog Labs.",
            score=0.91,
            rank=1,
            source="dense",
        )
    ]

    async def fake_sparse_retrieve_chunks(**kwargs):
        return sparse_hits

    async def fake_dense_retrieve_chunks(**kwargs):
        return dense_hits

    class FakeScalarResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def __iter__(self):
            return iter(self._rows)

    class SupportingSession(FakeAsyncSession):
        async def execute(self, statement, params=None):
            del statement, params
            return FakeScalarResult(
                [
                    SimpleNamespace(
                        chunk_id="chunk-header",
                        tenant_id=tenant_id,
                        namespace_id=namespace_id,
                        doc_id=document_id,
                        chunk_index=0,
                        chunk_text="Samrawit Gebremaryam Bahta\nsamrawit@example.com",
                    )
                ]
            )

    monkeypatch.setattr(
        "app.services.retrieval.sparse_retrieve_chunks",
        fake_sparse_retrieve_chunks,
    )
    monkeypatch.setattr(
        "app.services.retrieval.dense_retrieve_chunks",
        fake_dense_retrieve_chunks,
    )

    bundle = await retrieve_hybrid_candidates(
        session=SupportingSession([]),
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        query_text="What is the person's name?",
        limit=4,
    )

    assert bundle.fused_hits[0].chunk_id == "chunk-header"


@pytest.mark.asyncio()
async def test_retrieve_hybrid_candidates_supports_dataset_summary_queries(monkeypatch) -> None:
    """Dataset-summary questions should be able to use leading namespace chunks even without lexical hits."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()

    async def fake_sparse_retrieve_chunks(**kwargs):
        del kwargs
        return []

    async def fake_dense_retrieve_chunks(**kwargs):
        del kwargs
        return []

    monkeypatch.setattr(
        "app.services.retrieval.sparse_retrieve_chunks",
        fake_sparse_retrieve_chunks,
    )
    monkeypatch.setattr(
        "app.services.retrieval.dense_retrieve_chunks",
        fake_dense_retrieve_chunks,
    )

    session = ScalarAsyncSession(
        [
            SimpleNamespace(
                chunk_id="chunk-header",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                doc_id=document_id,
                chunk_index=0,
                chunk_text="Samrawit Gebremaryam Bahta\nEDUCATION\nBSc in Software Engineering",
            ),
            SimpleNamespace(
                chunk_id="chunk-skills",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                doc_id=document_id,
                chunk_index=1,
                chunk_text="TECHNICAL SKILLS\nPython, Go, TypeScript, FastAPI",
            ),
        ]
    )

    bundle = await retrieve_hybrid_candidates(
        session=session,
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        query_text="What is the dataset about?",
        limit=4,
    )

    assert [hit.chunk_id for hit in bundle.fused_hits[:2]] == ["chunk-header", "chunk-skills"]
