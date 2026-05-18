"""Policy-gated internal model retrieval helpers for Critical queries."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Namespace
from app.pipeline.contracts import EvidenceItem, EvidencePackage, FusedRetrievedChunk


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


def run_internal_model_retrieval(
    *,
    namespace: Namespace,
    evidence_package: EvidencePackage,
    fused_hits: list[FusedRetrievedChunk] | None = None,
    max_items: int = 8,
) -> InternalModelRetrievalResult:
    """Run one bounded internal evidence expansion for Critical mode.

    This keeps the path explicit and bounded. It never fabricates new evidence and never
    overrides existing evidence silently. It only widens the evidence package using already
    retrieved grounded content when policy allows it.
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

    selected_chunk_ids = {item.chunk_id for item in evidence_package.items}
    remaining_capacity = max_items - len(evidence_package.items)
    candidate_hits = [
        hit
        for hit in fused_hits
        if hit.chunk_id in evidence_package.retrieved_chunk_ids and hit.chunk_id not in selected_chunk_ids
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

    # Internal expansion may only widen the already retrieved grounded set.
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
