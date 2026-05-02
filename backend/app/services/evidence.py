"""Evidence packaging helpers for grounded generation."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.core.query_analysis import (
    build_query_profile,
    final_answer_mode,
    has_strong_intent_signal,
    is_action_query,
    is_comparison_query,
    is_count_query,
    is_entity_context_query,
    needs_multi_chunk_exact_support,
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
    query_score: float
    strong_intent: bool
    terms: frozenset[str]


def package_evidence(
    retrieval_bundle: RetrievalBundle,
    *,
    query_text: str | None = None,
    limit: int | None = None,
) -> EvidencePackage:
    """Select the top fused hits and normalize them into evidence items."""

    requested_limit = limit or get_settings().evidence_package_limit
    selected_hits = _select_hits_for_query(
        retrieval_bundle,
        query_text=query_text,
        limit=requested_limit,
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
            section_title=hit.section_title,
            section_slug=hit.section_slug,
            chunk_role=hit.chunk_role,
            starts_with_heading=hit.starts_with_heading,
            is_list_block=hit.is_list_block,
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
    """Select fused hits with simpler mode-aware evidence policies."""

    if not retrieval_bundle.fused_hits:
        return []
    if not query_text:
        return retrieval_bundle.fused_hits[:limit]

    profile = build_query_profile(query_text)
    answer_mode = final_answer_mode(profile)
    ranked_hits = _rank_hits(retrieval_bundle.fused_hits, profile=profile)

    if answer_mode == "exact_lookup":
        return _select_exact_qa_hits(ranked_hits, profile=profile, limit=limit)
    if answer_mode == "list_or_recommendation":
        return _select_structured_bundle_hits(ranked_hits, profile=profile, limit=max(2, min(limit, 4)))
    if answer_mode == "summary":
        return _select_summary_hits(ranked_hits, limit=limit)
    if any(
        (
            is_action_query(profile),
            is_comparison_query(profile),
            is_entity_context_query(profile),
            is_count_query(profile),
        )
    ):
        return _select_structured_bundle_hits(ranked_hits, profile=profile, limit=max(2, min(limit, 4)))
    return _select_top_hits(ranked_hits, limit=limit)


def _rank_hits(
    fused_hits: list[FusedRetrievedChunk],
    *,
    profile,
) -> list[_ScoredHit]:
    """Rank hits with a light query-aware score instead of a second reranker."""

    top_fused_score = max((hit.fused_score for hit in fused_hits), default=1.0) or 1.0
    answer_mode = final_answer_mode(profile)

    scored_hits: list[_ScoredHit] = []
    for hit in fused_hits:
        query_score = score_text_against_query(
            hit.text,
            profile=profile,
            chunk_index=hit.chunk_index,
        )
        strong_intent = has_strong_intent_signal(hit.text, profile=profile)
        base_score = (hit.fused_score / top_fused_score) * 10.0 + query_score

        if strong_intent:
            base_score += 3.0

        if answer_mode == "summary":
            if hit.chunk_index <= 1:
                base_score += 2.0
            if any(token in hit.text.casefold() for token in ("overview", "abstract", "summary", "title")):
                base_score += 2.0
        elif answer_mode == "list_or_recommendation":
            if hit.is_list_block:
                base_score += 2.0
            if hit.chunk_role == "section_header":
                base_score += 2.0
            elif hit.chunk_role in {"section_list", "section_body"}:
                base_score += 1.0
            section_terms = tokenize_meaningful_terms(
                " ".join(
                    part
                    for part in (
                        hit.section_title,
                        hit.section_slug.replace("-", " ") if hit.section_slug else None,
                    )
                    if part
                )
            )
            if section_terms & set(profile.expanded_terms):
                base_score += 2.0

        scored_hits.append(
            _ScoredHit(
                hit=hit,
                score=base_score,
                query_score=query_score,
                strong_intent=strong_intent,
                terms=frozenset(tokenize_meaningful_terms(hit.text)),
            )
        )

    return sorted(
        scored_hits,
        key=lambda entry: (
            -entry.score,
            entry.hit.chunk_index,
            entry.hit.chunk_id,
        ),
    )


def _select_exact_qa_hits(
    ranked_hits: list[_ScoredHit],
    *,
    profile,
    limit: int,
) -> list[FusedRetrievedChunk]:
    """Choose the best exact-QA chunk and optionally one justified support chunk."""

    if not ranked_hits:
        return []

    primary = ranked_hits[0]
    selected = [primary.hit]
    max_hits = 2 if needs_multi_chunk_exact_support(profile) or limit > 1 else 1
    if max_hits == 1:
        return selected

    primary_terms = set(primary.terms)
    for candidate in ranked_hits[1:]:
        if candidate.hit.document_id != primary.hit.document_id:
            continue
        if candidate.hit.chunk_id == primary.hit.chunk_id:
            continue
        if not _exact_support_is_justified(
            primary=primary,
            candidate=candidate,
            primary_terms=primary_terms,
        ):
            continue
        selected.append(candidate.hit)
        break
    return selected


def _exact_support_is_justified(
    *,
    primary: _ScoredHit,
    candidate: _ScoredHit,
    primary_terms: set[str],
) -> bool:
    """Return whether a second exact-QA chunk adds clear support."""

    same_section = bool(
        primary.hit.section_slug
        and candidate.hit.section_slug
        and primary.hit.section_slug == candidate.hit.section_slug
    )
    adds_terms = bool(set(candidate.terms) - primary_terms)

    if candidate.strong_intent and candidate.query_score >= 8.0:
        return True
    if same_section and candidate.query_score >= 7.5:
        return True
    if adds_terms and candidate.query_score >= 9.0:
        return True
    return False


def _select_structured_bundle_hits(
    ranked_hits: list[_ScoredHit],
    *,
    profile,
    limit: int,
) -> list[FusedRetrievedChunk]:
    """Keep a tight answer-bearing cluster for list/recommendation questions."""

    if not ranked_hits:
        return []

    primary = ranked_hits[0]
    selected: list[_ScoredHit] = [primary]
    covered_terms: set[str] = set(primary.terms)

    for candidate in ranked_hits[1:]:
        if len(selected) >= limit:
            break
        if candidate.hit.document_id != primary.hit.document_id:
            continue
        if candidate.hit.chunk_id == primary.hit.chunk_id:
            continue
        if not _structured_support_is_relevant(
            primary=primary,
            candidate=candidate,
            covered_terms=covered_terms,
            profile=profile,
        ):
            continue
        selected.append(candidate)
        covered_terms.update(candidate.terms)

    return [entry.hit for entry in selected]


def _structured_support_is_relevant(
    *,
    primary: _ScoredHit,
    candidate: _ScoredHit,
    covered_terms: set[str],
    profile,
) -> bool:
    """Return whether a structured support chunk is clearly relevant."""

    del profile
    same_section = bool(
        primary.hit.section_slug
        and candidate.hit.section_slug
        and primary.hit.section_slug == candidate.hit.section_slug
    )
    adds_terms = bool(set(candidate.terms) - covered_terms)

    if candidate.strong_intent and candidate.query_score >= 7.0:
        return True
    if same_section and candidate.query_score >= 6.5 and adds_terms:
        return True
    if same_section and abs(candidate.hit.chunk_index - primary.hit.chunk_index) <= 1 and adds_terms:
        return True
    if candidate.hit.is_list_block and candidate.query_score >= 7.5:
        return True
    return False


def _select_summary_hits(
    ranked_hits: list[_ScoredHit],
    *,
    limit: int,
) -> list[FusedRetrievedChunk]:
    """Choose broader but coherent summary evidence."""

    if not ranked_hits:
        return []

    unique_document_ids = {entry.hit.document_id for entry in ranked_hits}
    if len(unique_document_ids) <= 1:
        selected_hits = _select_diverse_hits(
            ranked_hits,
            limit=limit,
            prefer_document_diversity=False,
        )
        return sorted(
            selected_hits,
            key=lambda hit: (hit.chunk_index, -hit.fused_score, hit.chunk_id),
        )

    representatives = _collapse_to_document_representatives(ranked_hits)
    selected_hits = _select_diverse_hits(
        representatives,
        limit=limit,
        prefer_document_diversity=True,
    )
    return sorted(
        selected_hits,
        key=lambda hit: (-next(entry.score for entry in representatives if entry.hit.chunk_id == hit.chunk_id), hit.chunk_index, hit.chunk_id),
    )


def _select_top_hits(
    ranked_hits: list[_ScoredHit],
    *,
    limit: int,
) -> list[FusedRetrievedChunk]:
    """Select top hits with light novelty control."""

    return _select_diverse_hits(
        ranked_hits,
        limit=limit,
        prefer_document_diversity=False,
    )


def _collapse_to_document_representatives(
    ranked_hits: list[_ScoredHit],
) -> list[_ScoredHit]:
    """Keep the strongest summary seed per document."""

    by_document: dict[object, _ScoredHit] = {}
    for entry in ranked_hits:
        current = by_document.get(entry.hit.document_id)
        if current is None or entry.score > current.score:
            by_document[entry.hit.document_id] = entry
    return sorted(
        by_document.values(),
        key=lambda entry: (
            -entry.score,
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
    """Greedily keep complementary evidence instead of flat near-duplicates."""

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
                2.5
                if prefer_document_diversity and candidate.hit.document_id not in seen_documents
                else 0.0
            )
            adjacency_penalty = 0.0
            if selected and any(
                chosen.hit.document_id == candidate.hit.document_id
                and abs(chosen.hit.chunk_index - candidate.hit.chunk_index) <= 1
                for chosen in selected
            ):
                adjacency_penalty = 1.0 if prefer_document_diversity else 0.3
            selection_value = candidate.score + novelty * 0.9 + document_bonus - adjacency_penalty
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
