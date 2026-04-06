"""Evidence packaging helpers for grounded generation."""

from __future__ import annotations

from app.config import get_settings
from app.core.query_analysis import build_query_profile, score_text_against_query
from app.pipeline.contracts import EvidenceItem, EvidencePackage, FusedRetrievedChunk
from app.services.retrieval import RetrievalBundle


def package_evidence(
    retrieval_bundle: RetrievalBundle,
    *,
    query_text: str | None = None,
    limit: int | None = None,
) -> EvidencePackage:
    """Select the top fused hits and normalize them into evidence items."""

    selection_limit = limit or get_settings().evidence_package_limit
    selected_hits = _select_hits_for_query(
        retrieval_bundle,
        query_text=query_text,
        limit=selection_limit,
    )

    selected_items = [
        EvidenceItem(
            citation_id=f"E{index:03d}",
            chunk_id=hit.chunk_id,
            tenant_id=hit.tenant_id,
            namespace_id=hit.namespace_id,
            document_id=hit.document_id,
            chunk_index=hit.chunk_index,
            text=hit.text,
            score=hit.fused_score,
            sources=hit.sources,
        )
        for index, hit in enumerate(selected_hits, start=1)
    ]

    return EvidencePackage(
        retrieved_chunk_ids=_collect_retrieved_chunk_ids(retrieval_bundle),
        selected_evidence_ids=[item.chunk_id for item in selected_items],
        items=selected_items,
    )


def _select_hits_for_query(
    retrieval_bundle: RetrievalBundle,
    *,
    query_text: str | None,
    limit: int,
) -> list[FusedRetrievedChunk]:
    """Select fused hits, reranking them by answerability when a query is available."""

    if not retrieval_bundle.fused_hits:
        return []
    if not query_text:
        return retrieval_bundle.fused_hits[:limit]

    profile = build_query_profile(query_text)
    top_fused_score = max(hit.fused_score for hit in retrieval_bundle.fused_hits) or 1.0

    ranked_hits = sorted(
        retrieval_bundle.fused_hits,
        key=lambda hit: (
            -(
                (hit.fused_score / top_fused_score) * 12.0
                + score_text_against_query(
                    hit.text,
                    profile=profile,
                    chunk_index=hit.chunk_index,
                )
                + len(hit.sources) * 1.5
            ),
            hit.chunk_index,
            hit.chunk_id,
        ),
    )
    return ranked_hits[:limit]


def _collect_retrieved_chunk_ids(retrieval_bundle: RetrievalBundle) -> list[str]:
    """Return retrieval candidate ids without duplicates, preserving first appearance."""

    seen: set[str] = set()
    ordered_ids: list[str] = []
    for hit in (
        list(retrieval_bundle.fused_hits)
        + list(retrieval_bundle.sparse_hits)
        + list(retrieval_bundle.dense_hits)
    ):
        chunk_id = _hit_chunk_id(hit)
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        ordered_ids.append(chunk_id)
    return ordered_ids


def _hit_chunk_id(hit: FusedRetrievedChunk | object) -> str:
    """Extract a chunk id from a fused or retrieved hit object."""

    chunk_id = getattr(hit, "chunk_id", None)
    if not isinstance(chunk_id, str):
        raise TypeError("Retrieval hit is missing a valid chunk_id.")
    return chunk_id
