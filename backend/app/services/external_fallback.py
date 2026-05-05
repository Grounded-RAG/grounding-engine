"""Policy-gated external fallback scaffolding for Critical queries."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Namespace


@dataclass(frozen=True)
class ExternalFallbackDecision:
    """One explicit external fallback policy decision."""

    allowed: bool
    reason: str
    attempted: bool = False
    sources_consulted: tuple[str, ...] = ()


def resolve_external_fallback_policy(*, namespace: Namespace) -> ExternalFallbackDecision:
    """Return whether Critical may use policy-controlled external fallback."""

    if not getattr(namespace, "allow_web_fallback", False):
        return ExternalFallbackDecision(
            allowed=False,
            reason="policy_disabled",
        )

    return ExternalFallbackDecision(
        allowed=True,
        reason="allowlisted_policy_enabled",
    )
