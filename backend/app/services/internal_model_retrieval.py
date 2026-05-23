"""Policy-gated internal model retrieval helpers for Critical queries."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.flags import is_long_context_retrieval_enabled
from app.models import Namespace
from app.pipeline.contracts import EvidenceItem, EvidencePackage, FusedRetrievedChunk


_LONG_CONTEXT_MAX_CHUNKS = 24
_LONG_CONTEXT_MAX_ITEMS_OUT = 8


@dataclass(frozen=True)
class InternalModelRetrievalDecision:
    """One explicit internal model retrieval policy decision."""

    allowed: bool
    reason: str
    attempted: bool = False


@dataclass(frozen=True)
class InternalModelRetrievalResult:
    """Result of one bounded internal retrieval expansion."""

    attempted: bool
    used: bool
    reason: str
    evidence_package: EvidencePackage | None = None


def resolve_internal_model_retrieval_policy(*, namespace: Namespace) -> InternalModelRetrievalDecision:
    """Return whether Critical may use the internal model retrieval path."""
    if not getattr(namespace, "allow_internal_model_retrieval", False):
        return InternalModelRetrievalDecision(
            allowed=False,
            reason="policy_disabled",
        )
    return InternalModelRetrievalDecision(
        allowed=True,
        reason="policy_enabled",
    )


def _score_candidate(hit: FusedRetrievedChunk) -> float:
    """Score a candidate chunk for long-context inclusion."""
    role_bonus = {
        "section_header": 0.15,
        "section_body": 0.10,
        "document_header": 0.05,
        "body": 0.0,
        "section_list": -0.05,
        "list": -0.10,
    }.get(hit.chunk_role, 0.0)
    return hit.fused_score + role_bonus


def _build_long_context_evidence_package(
    *,
    evidence_package: EvidencePackage,
    fused_hits: list[FusedRetrievedChunk],
    max_items: int,
) -> EvidencePackage | None:
    """Select up to max_items chunks from the full retrieved candidate pool.

    Unlike the narrow-window expansion (which only considers already-selected
    chunks), this path draws from all fused_hits ranked by score + role authority,
    giving the downstream generator a broader internal context to read.

    This is the 'true long-context internal retrieval path' — it reads a wider
    evidence window from the bounded grounded corpus rather than re-selecting
    only what was already packaged.
    """
    already_selected = {item.chunk_id for item in evidence_package.items}
    retrieved_ids = set(evidence_package.retrieved_chunk_ids)

    # Restrict to chunks that were actually retrieved (grounded corpus only).
    candidates = [
        hit for hit in fused_hits
        if hit.chunk_id in retrieved_ids and hit.chunk_id not in already_selected
    ]
    if not candidates:
        return None

    # Limit candidate pool to avoid unbounded context.
    candidates = sorted(candidates, key=_score_candidate, reverse=True)
    candidates = candidates[: _LONG_CONTEXT_MAX_CHUNKS]

    remaining_capacity = max(0, max_items - len(evidence_package.items))
    if remaining_capacity == 0:
        return None

    selected_candidates = candidates[:remaining_capacity]

    expanded_items: list[EvidenceItem] = list(evidence_package.items)
    next_index = len(expanded_items) + 1
    for hit in selected_candidates:
        expanded_items.append(
            EvidenceItem(
                citation_id=f"E{next_index:03d}",
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
        )
        next_index += 1

    return EvidencePackage(
        retrieved_chunk_ids=list(evidence_package.retrieved_chunk_ids),
        selected_evidence_ids=[item.chunk_id for item in expanded_items],
        items=expanded_items,
    )


def run_internal_model_retrieval(
    *,
    namespace: Namespace,
    evidence_package: EvidencePackage,
    fused_hits: list[FusedRetrievedChunk] | None = None,
    max_items: int = _LONG_CONTEXT_MAX_ITEMS_OUT,
) -> InternalModelRetrievalResult:
    """Run bounded internal evidence expansion for Critical mode.

    Two paths are available depending on the ENABLE_LONG_CONTEXT_RETRIEVAL flag:

    Long-context path (flag enabled):
        Draws from the full retrieved candidate pool, sorted by score + role
        authority, up to _LONG_CONTEXT_MAX_CHUNKS candidates.  This gives the
        generator a genuinely wider internal context window.

    Narrow-window path (flag disabled, default):
        Re-selects only from chunks already present in retrieved_chunk_ids that
        were not selected into the evidence package.  This is bounded and safe.

    Both paths:
    - Never fabricate new evidence.
    - Never silently override existing grounded evidence.
    - Record attempt/used/reason in the trace.
    """
    decision = resolve_internal_model_retrieval_policy(namespace=namespace)
    if not decision.allowed:
        return InternalModelRetrievalResult(
            attempted=False,
            used=False,
            reason=decision.reason,
        )

    if len(evidence_package.items) >= max_items:
        return InternalModelRetrievalResult(
            attempted=True,
            used=False,
            reason="bounded_evidence_limit_reached",
            evidence_package=evidence_package,
        )

    if not evidence_package.items:
        return InternalModelRetrievalResult(
            attempted=True,
            used=False,
            reason="no_grounded_evidence_available",
            evidence_package=evidence_package,
        )

    if not fused_hits:
        return InternalModelRetrievalResult(
            attempted=True,
            used=False,
            reason="no_additional_retrieval_candidates",
            evidence_package=evidence_package,
        )

    # Long-context path: draw from full candidate pool.
    if is_long_context_retrieval_enabled():
        expanded = _build_long_context_evidence_package(
            evidence_package=evidence_package,
            fused_hits=fused_hits,
            max_items=max_items,
        )
        if expanded is None:
            return InternalModelRetrievalResult(
                attempted=True,
                used=False,
                reason="long_context_no_new_candidates",
                evidence_package=evidence_package,
            )
        return InternalModelRetrievalResult(
            attempted=True,
            used=len(expanded.items) > len(evidence_package.items),
            reason="long_context_internal_retrieval_expanded",
            evidence_package=expanded,
        )

    # Narrow-window path: only widen from already-selected retrieved set.
    selected_chunk_ids = {item.chunk_id for item in evidence_package.items}
    remaining_capacity = max_items - len(evidence_package.items)
    candidate_hits = [
        hit
        for hit in fused_hits
        if hit.chunk_id in evidence_package.retrieved_chunk_ids
        and hit.chunk_id not in selected_chunk_ids
    ]
    if not candidate_hits:
        return InternalModelRetrievalResult(
            attempted=True,
            used=False,
            reason="no_new_grounded_candidates",
            evidence_package=evidence_package,
        )

    candidate_hits = sorted(
        candidate_hits,
        key=lambda hit: (-hit.fused_score, hit.chunk_index, hit.chunk_id),
    )[:remaining_capacity]

    expanded_items: list[EvidenceItem] = list(evidence_package.items)
    next_index = len(expanded_items) + 1
    for hit in candidate_hits:
        expanded_items.append(
            EvidenceItem(
                citation_id=f"E{next_index:03d}",
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
        )
        next_index += 1

    expanded_package = EvidencePackage(
        retrieved_chunk_ids=list(evidence_package.retrieved_chunk_ids),
        selected_evidence_ids=[item.chunk_id for item in expanded_items],
        items=expanded_items,
    )
    return InternalModelRetrievalResult(
        attempted=True,
        used=len(expanded_items) > len(evidence_package.items),
        reason=(
            "bounded_internal_retrieval_expanded"
            if len(expanded_items) > len(evidence_package.items)
            else "bounded_internal_retrieval_noop"
        ),
        evidence_package=expanded_package,
    )
