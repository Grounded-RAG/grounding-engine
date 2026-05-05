"""Policy-gated internal model retrieval scaffolding for Critical queries."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Namespace


@dataclass(frozen=True)
class InternalModelRetrievalDecision:
    """One explicit internal model retrieval policy decision."""

    allowed: bool
    reason: str
    attempted: bool = False


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
