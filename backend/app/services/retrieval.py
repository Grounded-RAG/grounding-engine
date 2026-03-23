"""Sparse, dense, and fused retrieval helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.embeddings import EmbeddingError, embed_texts
from app.core.qdrant_client import VectorStoreError, search_dense_points
from app.pipeline.contracts import FusedRetrievedChunk, RetrievedChunk


class RetrievalError(RuntimeError):
    """Raised when a retrieval path cannot complete safely."""


@dataclass(frozen=True)
class RetrievalBundle:
    """All retrieval candidates produced for one query."""

    sparse_hits: list[RetrievedChunk]
    dense_hits: list[RetrievedChunk]
    fused_hits: list[FusedRetrievedChunk]


def _coerce_uuid(value: UUID | str) -> UUID:
    """Coerce UUID-like payload values into UUID instances."""

    return value if isinstance(value, UUID) else UUID(str(value))


async def sparse_retrieve_chunks(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    namespace_id: UUID,
    query_text: str,
    limit: int | None = None,
) -> list[RetrievedChunk]:
    """Retrieve lexical candidates from PostgreSQL full-text search."""

    candidate_limit = limit or get_settings().retrieval_candidate_limit
    statement = text(
        """
        select
            chunk_id,
            tenant_id,
            namespace_id,
            doc_id,
            chunk_index,
            chunk_text,
            ts_rank_cd(search_vector, plainto_tsquery('english', :query_text)) as score
        from document_chunks
        where tenant_id = :tenant_id
          and namespace_id = :namespace_id
          and search_vector @@ plainto_tsquery('english', :query_text)
        order by score desc, chunk_index asc
        limit :limit
        """
    )

    try:
        result = await session.execute(
            statement,
            {
                "tenant_id": tenant_id,
                "namespace_id": namespace_id,
                "query_text": query_text,
                "limit": candidate_limit,
            },
        )
    except SQLAlchemyError as exc:
        raise RetrievalError("Sparse retrieval query failed.") from exc

    rows = result.mappings().all()
    hits: list[RetrievedChunk] = []
    for index, row in enumerate(rows, start=1):
        hits.append(
            RetrievedChunk(
                chunk_id=str(row["chunk_id"]),
                tenant_id=_coerce_uuid(row["tenant_id"]),
                namespace_id=_coerce_uuid(row["namespace_id"]),
                document_id=_coerce_uuid(row["doc_id"]),
                chunk_index=int(row["chunk_index"]),
                text=str(row["chunk_text"]),
                score=float(row["score"]),
                rank=index,
                source="sparse",
            )
        )
    return hits


async def dense_retrieve_chunks(
    *,
    tenant_id: UUID,
    namespace_id: UUID,
    query_text: str,
    limit: int | None = None,
) -> list[RetrievedChunk]:
    """Retrieve semantic candidates from Qdrant."""

    candidate_limit = limit or get_settings().retrieval_candidate_limit
    try:
        query_embedding = (await embed_texts([query_text]))[0]
        points = search_dense_points(
            query_vector=query_embedding.vector,
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            limit=candidate_limit,
        )
    except (EmbeddingError, IndexError) as exc:
        raise RetrievalError("Dense retrieval failed to embed the query.") from exc
    except VectorStoreError as exc:
        raise RetrievalError("Dense retrieval query failed.") from exc

    hits: list[RetrievedChunk] = []
    for index, point in enumerate(points, start=1):
        payload = point.payload or {}
        hits.append(
            RetrievedChunk(
                chunk_id=str(payload["chunk_id"]),
                tenant_id=_coerce_uuid(payload["tenant_id"]),
                namespace_id=_coerce_uuid(payload["namespace_id"]),
                document_id=_coerce_uuid(payload["document_id"]),
                chunk_index=int(payload["chunk_index"]),
                text=str(payload["text"]),
                score=float(point.score),
                rank=index,
                source="dense",
            )
        )
    return hits


def fuse_retrieval_hits(
    *hits_groups: Iterable[RetrievedChunk],
    limit: int | None = None,
    rrf_k: int | None = None,
) -> list[FusedRetrievedChunk]:
    """Fuse sparse and dense results using reciprocal rank fusion."""

    smoothing_constant = rrf_k or get_settings().rrf_smoothing_constant
    fused_by_chunk: dict[str, dict[str, object]] = {}

    for hits_group in hits_groups:
        for hit in hits_group:
            bucket = fused_by_chunk.setdefault(
                hit.chunk_id,
                {
                    "hit": hit,
                    "score": 0.0,
                    "sources": [],
                },
            )
            bucket["score"] = float(bucket["score"]) + 1.0 / (
                smoothing_constant + hit.rank
            )
            sources = bucket["sources"]
            if isinstance(sources, list) and hit.source not in sources:
                sources.append(hit.source)

    fused_hits = [
        FusedRetrievedChunk(
            chunk_id=chunk_id,
            tenant_id=entry["hit"].tenant_id,
            namespace_id=entry["hit"].namespace_id,
            document_id=entry["hit"].document_id,
            chunk_index=entry["hit"].chunk_index,
            text=entry["hit"].text,
            fused_score=float(entry["score"]),
            sources=tuple(sorted(entry["sources"])),
        )
        for chunk_id, entry in fused_by_chunk.items()
    ]
    fused_hits.sort(
        key=lambda hit: (
            -hit.fused_score,
            hit.chunk_index,
            hit.chunk_id,
        )
    )
    if limit is None:
        return fused_hits
    return fused_hits[:limit]


async def retrieve_hybrid_candidates(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    namespace_id: UUID,
    query_text: str,
    limit: int | None = None,
) -> RetrievalBundle:
    """Run sparse and dense retrieval, then merge candidates with RRF."""

    sparse_hits = await sparse_retrieve_chunks(
        session=session,
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        query_text=query_text,
        limit=limit,
    )
    dense_hits = await dense_retrieve_chunks(
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        query_text=query_text,
        limit=limit,
    )
    fused_hits = fuse_retrieval_hits(
        sparse_hits,
        dense_hits,
        limit=limit or get_settings().retrieval_candidate_limit,
    )
    return RetrievalBundle(
        sparse_hits=sparse_hits,
        dense_hits=dense_hits,
        fused_hits=fused_hits,
    )
