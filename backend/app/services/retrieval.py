"""Sparse, dense, and fused retrieval helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.query_analysis import (
    QueryPlan,
    build_query_plan,
    has_strong_intent_signal,
    is_collection_query,
    is_dataset_summary_query,
    is_field_extraction_query,
    score_text_against_query,
    tokenize_meaningful_terms,
)
from app.core.embeddings import EmbeddingError, embed_texts
from app.models import DocumentChunkRecord
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


def _query_term_coverage_score(*, text: str, query_plan: QueryPlan) -> float:
    """Reward chunks that cover more of the query's meaningful vocabulary."""

    profile = query_plan.profile
    text_terms = tokenize_meaningful_terms(text)
    if not text_terms:
        return 0.0

    direct_overlap = len(set(profile.terms) & text_terms)
    expanded_overlap = len(set(profile.expanded_terms) & text_terms)
    score = direct_overlap * 3.5 + max(expanded_overlap - direct_overlap, 0) * 1.25

    normalized_text = " ".join(text.lower().split())
    for attribute in profile.attribute_terms:
        if attribute in normalized_text:
            score += 3.0
    return score


def _intent_bonus_for_hit(*, hit: FusedRetrievedChunk, query_plan: QueryPlan) -> float:
    """Apply stronger intent-focused bonuses and penalties after hybrid fusion."""

    profile = query_plan.profile
    strong_intent = has_strong_intent_signal(hit.text, profile=profile)
    line_count = len([line for line in hit.text.splitlines() if line.strip()])
    structured = ":" in hit.text or line_count >= 2

    if is_field_extraction_query(profile) and not is_collection_query(profile):
        return 10.0 if strong_intent else -5.0
    if is_collection_query(profile):
        if strong_intent and structured:
            return 8.0
        if strong_intent:
            return 3.0
        return -6.0
    if is_dataset_summary_query(profile):
        if strong_intent:
            return 4.0
        if hit.chunk_index <= 1:
            return 2.5
    return 0.0


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
            ts_rank_cd(search_vector, websearch_to_tsquery('english', :query_text)) as score
        from document_chunks
        where tenant_id = :tenant_id
          and namespace_id = :namespace_id
          and search_vector @@ websearch_to_tsquery('english', :query_text)
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


def _rerank_fused_hits_for_query(
    fused_hits: list[FusedRetrievedChunk],
    *,
    query_plan: QueryPlan,
    limit: int,
) -> list[FusedRetrievedChunk]:
    """Rerank fused hits by query answerability before the final top-k cut."""

    if not fused_hits:
        return []

    profile = query_plan.profile
    top_fused_score = max(hit.fused_score for hit in fused_hits) or 1.0

    reranked = sorted(
        fused_hits,
        key=lambda hit: (
            -(
                (hit.fused_score / top_fused_score) * 8.5
                + score_text_against_query(
                    hit.text,
                    profile=profile,
                    chunk_index=hit.chunk_index,
                )
                + _query_term_coverage_score(text=hit.text, query_plan=query_plan)
                + _intent_bonus_for_hit(hit=hit, query_plan=query_plan)
                + len(hit.sources) * 0.9
            ),
            hit.chunk_index,
            hit.chunk_id,
        ),
    )
    return reranked[:limit]


async def _fetch_supporting_context_hits(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    namespace_id: UUID,
    query_plan: QueryPlan,
    fused_hits: list[FusedRetrievedChunk],
) -> list[FusedRetrievedChunk]:
    """Recover nearby/header chunks from already-relevant documents."""

    if not fused_hits:
        return []

    profile = query_plan.profile
    target_indexes_by_doc: dict[UUID, set[int]] = {}
    doc_priority_scores: dict[UUID, float] = {}

    for hit in fused_hits[:5]:
        doc_priority_scores[hit.document_id] = max(
            doc_priority_scores.get(hit.document_id, 0.0),
            hit.fused_score,
        )
        target_indexes = target_indexes_by_doc.setdefault(hit.document_id, set())
        target_indexes.update(
            index
            for index in (hit.chunk_index - 1, hit.chunk_index, hit.chunk_index + 1)
            if index >= 0
        )

    if is_field_extraction_query(profile):
        for document_id in list(target_indexes_by_doc)[:3]:
            target_indexes_by_doc[document_id].update({0, 1})

    clauses = [
        (
            (DocumentChunkRecord.doc_id == document_id)
            & (DocumentChunkRecord.chunk_index.in_(sorted(indexes)))
        )
        for document_id, indexes in target_indexes_by_doc.items()
        if indexes
    ]
    if not clauses:
        return []

    statement = (
        select(DocumentChunkRecord)
        .where(
            DocumentChunkRecord.tenant_id == tenant_id,
            DocumentChunkRecord.namespace_id == namespace_id,
            or_(*clauses),
        )
        .order_by(DocumentChunkRecord.doc_id.asc(), DocumentChunkRecord.chunk_index.asc())
    )

    try:
        result = await session.execute(statement)
    except SQLAlchemyError as exc:
        raise RetrievalError("Supporting context retrieval failed.") from exc

    existing_chunk_ids = {hit.chunk_id for hit in fused_hits}
    supplemental_hits: list[FusedRetrievedChunk] = []
    rows = result.scalars() if hasattr(result, "scalars") else []
    for row in rows:
        if row.chunk_id in existing_chunk_ids:
            continue

        doc_score = doc_priority_scores.get(row.doc_id, 0.0)
        proximity_score = 0.72
        if row.chunk_index <= 1 and is_field_extraction_query(profile):
            proximity_score = 0.9

        supplemental_hits.append(
            FusedRetrievedChunk(
                chunk_id=row.chunk_id,
                tenant_id=row.tenant_id,
                namespace_id=row.namespace_id,
                document_id=row.doc_id,
                chunk_index=row.chunk_index,
                text=row.chunk_text,
                fused_score=max(doc_score * proximity_score, 0.0001),
                sources=("context",),
            )
        )

    return supplemental_hits


async def _fetch_namespace_lead_chunks(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    namespace_id: UUID,
    limit: int,
) -> list[FusedRetrievedChunk]:
    """Fetch leading chunks across the namespace for broad dataset-summary questions."""

    statement = (
        select(DocumentChunkRecord)
        .where(
            DocumentChunkRecord.tenant_id == tenant_id,
            DocumentChunkRecord.namespace_id == namespace_id,
            DocumentChunkRecord.chunk_index <= 1,
        )
        .order_by(DocumentChunkRecord.doc_id.asc(), DocumentChunkRecord.chunk_index.asc())
        .limit(limit)
    )

    try:
        result = await session.execute(statement)
    except SQLAlchemyError as exc:
        raise RetrievalError("Dataset summary retrieval failed.") from exc

    rows = result.scalars() if hasattr(result, "scalars") else []
    return [
        FusedRetrievedChunk(
            chunk_id=row.chunk_id,
            tenant_id=row.tenant_id,
            namespace_id=row.namespace_id,
            document_id=row.doc_id,
            chunk_index=row.chunk_index,
            text=row.chunk_text,
            fused_score=1.0 if row.chunk_index == 0 else 0.85,
            sources=("summary_context",),
        )
        for row in rows
    ]


async def retrieve_hybrid_candidates(
    *,
    session: AsyncSession,
    tenant_id: UUID,
    namespace_id: UUID,
    query_text: str,
    query_plan: QueryPlan | None = None,
    limit: int | None = None,
) -> RetrievalBundle:
    """Run sparse and dense retrieval, then merge candidates with RRF."""

    settings = get_settings()
    final_limit = limit or settings.retrieval_candidate_limit
    overfetch_limit = max(
        final_limit,
        final_limit * settings.retrieval_overfetch_factor,
    )
    plan = query_plan or build_query_plan(query_text)
    profile = plan.profile

    sparse_hits: list[RetrievedChunk] = []
    dense_hits: list[RetrievedChunk] = []
    for retrieval_query in plan.retrieval_queries:
        sparse_hits.extend(
            await sparse_retrieve_chunks(
                session=session,
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                query_text=retrieval_query,
                limit=overfetch_limit,
            )
        )
        dense_hits.extend(
            await dense_retrieve_chunks(
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                query_text=retrieval_query,
                limit=overfetch_limit,
            )
        )
    fused_hits = fuse_retrieval_hits(
        sparse_hits,
        dense_hits,
        rrf_k=settings.rrf_smoothing_constant,
    )
    supporting_hits = await _fetch_supporting_context_hits(
        session=session,
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        query_plan=plan,
        fused_hits=fused_hits,
    )
    if supporting_hits:
        fused_hits = list(fused_hits) + supporting_hits
    if is_dataset_summary_query(profile):
        summary_hits = await _fetch_namespace_lead_chunks(
            session=session,
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            limit=max(final_limit, settings.evidence_package_limit * 2),
        )
        existing_chunk_ids = {hit.chunk_id for hit in fused_hits}
        fused_hits = list(fused_hits) + [
            hit for hit in summary_hits if hit.chunk_id not in existing_chunk_ids
        ]
    fused_hits = _rerank_fused_hits_for_query(
        fused_hits,
        query_plan=plan,
        limit=final_limit,
    )
    return RetrievalBundle(
        sparse_hits=sparse_hits,
        dense_hits=dense_hits,
        fused_hits=fused_hits,
    )
