"""Evidence packaging helpers for grounded generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

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
from app.models import ExecutionTier
from app.pipeline.contracts import EvidenceItem, EvidencePackage, FusedRetrievedChunk
from app.services.retrieval import RetrievalBundle

logger = logging.getLogger(__name__)


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
    execution_tier: ExecutionTier = ExecutionTier.STANDARD,
    package_id: str | None = None,
) -> EvidencePackage:
    """Select the top fused hits and normalize them into evidence items.

    ``package_id`` scopes the generated ``citation_id`` values to one call.
    The default (``None``) generates a fresh ``uuid4().hex[:8]`` per call,
    so two back-to-back calls never produce overlapping ``E001..E00N``
    sequences — important for CRAG retries that re-package the same
    retrieval. Callers that want deterministic ids (e.g. tests) can pass
    an explicit ``package_id``.
    """

    resolved_package_id = package_id or uuid4().hex[:8]
    requested_limit = limit or get_settings().evidence_package_limit
    selected_hits = _select_hits_for_query(
        retrieval_bundle,
        query_text=query_text,
        limit=requested_limit,
        execution_tier=execution_tier,
    )

    selected_items = [
        EvidenceItem(
            citation_id=f"E{resolved_package_id[:4]}{index:03d}",
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
    execution_tier: ExecutionTier,
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
        return _select_exact_qa_hits(
            ranked_hits,
            profile=profile,
            limit=limit,
            execution_tier=execution_tier,
        )
    if answer_mode == "list_or_recommendation":
        return _select_structured_bundle_hits(
            ranked_hits,
            profile=profile,
            limit=max(2, min(limit, 4)),
            execution_tier=execution_tier,
        )
    if answer_mode == "summary":
        return _select_summary_hits(ranked_hits, limit=limit)
    if profile.query_kind == "definition":
        return _select_top_hits(ranked_hits, limit=max(limit, 5))
    if any(
        (
            is_action_query(profile),
            is_comparison_query(profile),
            is_entity_context_query(profile),
            is_count_query(profile),
        )
    ):
        return _select_structured_bundle_hits(
            ranked_hits,
            profile=profile,
            limit=max(2, min(limit, 4)),
            execution_tier=execution_tier,
        )
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
    execution_tier: ExecutionTier,
) -> list[FusedRetrievedChunk]:
    """Choose the best exact-QA chunk and optionally one justified support chunk."""

    if not ranked_hits:
        return []

    primary = ranked_hits[0]
    selected = [primary.hit]
    max_hits = _exact_support_limit(
        profile=profile,
        limit=limit,
        execution_tier=execution_tier,
    )
    if max_hits == 1:
        return selected

    primary_terms = set(primary.terms)
    for candidate in ranked_hits[1:]:
        if candidate.hit.chunk_id == primary.hit.chunk_id:
            continue
        if not _exact_support_is_justified(
            primary=primary,
            candidate=candidate,
            primary_terms=primary_terms,
            execution_tier=execution_tier,
        ):
            continue
        selected.append(candidate.hit)
        primary_terms.update(candidate.terms)
        if len(selected) >= max_hits:
            break
    return sorted(
        selected,
        key=lambda hit: (hit.chunk_index, -hit.fused_score, hit.chunk_id),
    )


def _exact_support_limit(
    *,
    profile,
    limit: int,
    execution_tier: ExecutionTier,
) -> int:
    """Return the maximum number of exact support chunks to keep."""

    if execution_tier is not ExecutionTier.ENTERPRISE:
        return 2 if needs_multi_chunk_exact_support(profile) or limit > 1 else 1

    if len(profile.attribute_terms) >= 2:
        return min(max(limit, 3), 3)
    if needs_multi_chunk_exact_support(profile) or limit > 1:
        return min(max(limit, 2), 3)
    return 1


def _exact_support_is_justified(
    *,
    primary: _ScoredHit,
    candidate: _ScoredHit,
    primary_terms: set[str],
    execution_tier: ExecutionTier,
) -> bool:
    """Return whether a second exact-QA chunk adds clear support."""

    same_document = candidate.hit.document_id == primary.hit.document_id
    same_section = bool(
        primary.hit.section_slug
        and candidate.hit.section_slug
        and primary.hit.section_slug == candidate.hit.section_slug
    )
    adds_terms = bool(set(candidate.terms) - primary_terms)

    if execution_tier is ExecutionTier.ENTERPRISE:
        if same_document and candidate.strong_intent and candidate.query_score >= 6.5:
            return True
        if same_section and candidate.query_score >= 6.5:
            return True
        if same_document and adds_terms and candidate.query_score >= 7.0:
            return True
        if candidate.query_score >= 9.5 and adds_terms:
            return True
        return False

    if not same_document:
        return False
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
    execution_tier: ExecutionTier,
) -> list[FusedRetrievedChunk]:
    """Keep a tight answer-bearing cluster for list/recommendation questions."""

    if not ranked_hits:
        return []

    if execution_tier is ExecutionTier.ENTERPRISE:
        return _select_enterprise_structured_bundle_hits(
            ranked_hits,
            profile=profile,
            limit=max(3, min(limit, 5)),
        )

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


def _select_enterprise_structured_bundle_hits(
    ranked_hits: list[_ScoredHit],
    *,
    profile,
    limit: int,
) -> list[FusedRetrievedChunk]:
    """Keep a compact but richer support cluster for Enterprise hard queries."""

    primary = ranked_hits[0]
    selected: list[_ScoredHit] = [primary]
    covered_terms: set[str] = set(primary.terms)

    if is_comparison_query(profile):
        contrast_candidate = _first_matching_hit(
            ranked_hits[1:],
            predicate=lambda candidate: _comparison_support_is_relevant(
                primary=primary,
                candidate=candidate,
                covered_terms=covered_terms,
            ),
        )
        if contrast_candidate is not None:
            selected.append(contrast_candidate)
            covered_terms.update(contrast_candidate.terms)

    for candidate in ranked_hits[1:]:
        if len(selected) >= limit:
            break
        if any(existing.hit.chunk_id == candidate.hit.chunk_id for existing in selected):
            continue
        if not _enterprise_structured_support_is_relevant(
            primary=primary,
            candidate=candidate,
            covered_terms=covered_terms,
            profile=profile,
        ):
            continue
        selected.append(candidate)
        covered_terms.update(candidate.terms)

    return [entry.hit for entry in selected]


def _first_matching_hit(
    ranked_hits: list[_ScoredHit],
    *,
    predicate,
) -> _ScoredHit | None:
    """Return the first ranked hit that satisfies one predicate."""

    for candidate in ranked_hits:
        if predicate(candidate):
            return candidate
    return None


def _comparison_support_is_relevant(
    *,
    primary: _ScoredHit,
    candidate: _ScoredHit,
    covered_terms: set[str],
) -> bool:
    """Return whether one candidate adds a useful contrasting comparison anchor."""

    different_document = candidate.hit.document_id != primary.hit.document_id
    different_section = bool(
        candidate.hit.document_id == primary.hit.document_id
        and candidate.hit.section_slug
        and primary.hit.section_slug
        and candidate.hit.section_slug != primary.hit.section_slug
    )
    adds_terms = bool(set(candidate.terms) - covered_terms)

    if candidate.query_score < 6.0:
        return False
    if different_document and adds_terms:
        return True
    if different_section and adds_terms:
        return True
    return False


def _enterprise_structured_support_is_relevant(
    *,
    primary: _ScoredHit,
    candidate: _ScoredHit,
    covered_terms: set[str],
    profile,
) -> bool:
    """Return whether one Enterprise structured support chunk is clearly useful."""

    same_section = bool(
        primary.hit.section_slug
        and candidate.hit.section_slug
        and primary.hit.section_slug == candidate.hit.section_slug
    )
    same_document = candidate.hit.document_id == primary.hit.document_id
    adds_terms = bool(set(candidate.terms) - covered_terms)

    if candidate.strong_intent and candidate.query_score >= 6.0:
        return True
    if same_section and candidate.query_score >= 6.0:
        return True
    if same_document and candidate.hit.is_list_block and candidate.query_score >= 6.0:
        return True
    if adds_terms and candidate.query_score >= 6.5:
        return True
    if is_comparison_query(profile) and _comparison_support_is_relevant(
        primary=primary,
        candidate=candidate,
        covered_terms=covered_terms,
    ):
        return True
    return False


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
