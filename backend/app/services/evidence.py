"""Evidence packaging helpers for grounded generation."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.core.query_analysis import (
    build_query_profile,
    has_strong_intent_signal,
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

    requested_limit = limit or get_settings().evidence_package_limit
    if query_text:
        profile = build_query_profile(query_text)
        if is_field_extraction_query(profile) and not is_collection_query(profile):
            selection_limit = 1
        elif is_collection_query(profile):
            selection_limit = min(requested_limit, 2)
        else:
            selection_limit = requested_limit
    else:
        selection_limit = requested_limit
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
                + (
                    (4.0 - min(hit.chunk_index, 3)) * 1.5
                    if is_dataset_summary_query(profile)
                    else 0.0
                )
                + (
                    4.5
                    if is_dataset_summary_query(profile)
                    and any(
                        token in hit.text.casefold()
                        for token in ("overview", "introduction", "summary")
                    )
                    else 0.0
                )
                + (
                    7.0
                    if has_strong_intent_signal(hit.text, profile=profile)
                    else (-5.0 if is_collection_query(profile) else 0.0)
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
    if is_field_extraction_query(profile):
        strong_intent_hits = [
            entry
            for entry in ranked_hits
            if has_strong_intent_signal(entry.hit.text, profile=profile)
        ]
        if strong_intent_hits:
            ranked_hits = strong_intent_hits
    if is_field_extraction_query(profile) and not is_collection_query(profile):
        return [ranked_hits[0].hit]
    if is_dataset_summary_query(profile):
        ranked_hits = _collapse_to_document_representatives(ranked_hits)
        selected_hits = _select_diverse_hits(
            ranked_hits,
            limit=limit,
            prefer_document_diversity=True,
        )
        return sorted(
            selected_hits,
            key=lambda hit: (
                -(
                    hit.fused_score
                    + (
                        4.0
                        if any(
                            token in hit.text.casefold()
                            for token in ("overview", "introduction", "summary")
                        )
                        else 0.0
                    )
                    + max(0, 2 - hit.chunk_index) * 0.75
                ),
                hit.chunk_index,
                hit.chunk_id,
            ),
        )
    return _select_diverse_hits(
        ranked_hits,
        limit=limit,
        prefer_document_diversity=False,
    )


def _collapse_to_document_representatives(
    ranked_hits: list[_ScoredHit],
) -> list[_ScoredHit]:
    """Keep the single best summary seed per document before diversity selection."""

    def representative_score(entry: _ScoredHit) -> float:
        lead_bonus = (4.0 - min(entry.hit.chunk_index, 3)) * 2.0
        overview_bonus = (
            4.0
            if any(
                token in entry.hit.text.casefold()
                for token in ("overview", "introduction", "summary")
            )
            else 0.0
        )
        return entry.score + lead_bonus + overview_bonus

    by_document: dict[object, _ScoredHit] = {}
    for entry in ranked_hits:
        current = by_document.get(entry.hit.document_id)
        if current is None or representative_score(entry) > representative_score(current):
            by_document[entry.hit.document_id] = entry
    return sorted(
        by_document.values(),
        key=lambda entry: (
            -representative_score(entry),
            entry.hit.chunk_index,
            entry.hit.chunk_id,
        ),
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
