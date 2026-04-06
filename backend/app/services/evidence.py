"""Evidence packaging helpers for grounded generation."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.core.query_analysis import (
    build_query_profile,
    is_collection_query,
    is_dataset_summary_query,
    is_field_extraction_query,
    score_text_against_query,
    tokenize_meaningful_terms,
)
from app.pipeline.contracts import EvidenceItem, EvidencePackage, FusedRetrievedChunk
from app.services.retrieval import RetrievalBundle


@dataclass(frozen=True)
class _ScoredHit:
    """Intermediate scored hit used during evidence selection."""

    hit: FusedRetrievedChunk
    score: float
    terms: frozenset[str]


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

    scored_hits = [
        _ScoredHit(
            hit=hit,
            score=(
                (hit.fused_score / top_fused_score) * 12.0
                + score_text_against_query(
                    hit.text,
                    profile=profile,
                    chunk_index=hit.chunk_index,
                )
                + len(hit.sources) * 1.5
            ),
            terms=frozenset(tokenize_meaningful_terms(hit.text)),
        )
        for hit in retrieval_bundle.fused_hits
    ]
    ranked_hits = sorted(
        scored_hits,
        key=lambda entry: (
            -entry.score,
            entry.hit.chunk_index,
            entry.hit.chunk_id,
        ),
    )
    if is_field_extraction_query(profile) and not is_collection_query(profile):
        return [entry.hit for entry in ranked_hits[:limit]]
    return _select_diverse_hits(
        ranked_hits,
        limit=limit,
        prefer_document_diversity=is_dataset_summary_query(profile) or is_collection_query(profile),
    )


def _select_diverse_hits(
    ranked_hits: list[_ScoredHit],
    *,
    limit: int,
    prefer_document_diversity: bool,
) -> list[FusedRetrievedChunk]:
    """Greedily keep complementary evidence instead of flat top-k duplicates."""

    if not ranked_hits:
        return []

    remaining = list(ranked_hits)
    selected: list[_ScoredHit] = []
    covered_terms: set[str] = set()
    seen_documents: set[object] = set()

    while remaining and len(selected) < limit:
        best_index = 0
        best_value = float("-inf")
        for index, candidate in enumerate(remaining):
            novelty = len(candidate.terms - covered_terms)
            document_bonus = (
                3.0
                if prefer_document_diversity and candidate.hit.document_id not in seen_documents
                else 0.0
            )
            adjacency_penalty = 0.0
            if selected and any(
                chosen.hit.document_id == candidate.hit.document_id
                and abs(chosen.hit.chunk_index - candidate.hit.chunk_index) <= 1
                for chosen in selected
            ):
                adjacency_penalty = 1.5 if prefer_document_diversity else 0.5

            selection_value = candidate.score + novelty * 1.2 + document_bonus - adjacency_penalty
            if selection_value > best_value:
                best_value = selection_value
                best_index = index

        chosen = remaining.pop(best_index)
        selected.append(chosen)
        covered_terms.update(chosen.terms)
        seen_documents.add(chosen.hit.document_id)

    return [entry.hit for entry in selected]


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
