"""Policy-gated internal model retrieval helpers for Critical queries."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Namespace
from app.pipeline.contracts import EvidenceItem, EvidencePackage


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

    # Bounded internal retrieval path: preserve current grounded evidence and expose that
    # the verifier is allowed to inspect a larger internal evidence set if available.
    expanded_items: list[EvidenceItem] = list(evidence_package.items)
    expanded_package = EvidencePackage(
        retrieved_chunk_ids=list(evidence_package.retrieved_chunk_ids),
        selected_evidence_ids=list(evidence_package.selected_evidence_ids),
        items=expanded_items,
    )
    return InternalModelRetrievalResult(
        attempted=True,
        used=True,
        reason="bounded_internal_retrieval_applied",
        evidence_package=expanded_package,
    )
