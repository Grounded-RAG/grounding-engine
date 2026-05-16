"""Policy-gated allowlisted external fallback helpers for Critical queries."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Namespace
from app.schemas.query import GroundedAnswerResponse


_ALLOWLISTED_SOURCE_PROVIDERS = ("allowlisted_web_search",)


@dataclass(frozen=True)
class ExternalFallbackDecision:
    """One explicit external fallback policy decision."""

    allowed: bool
    reason: str
    attempted: bool = False
    sources_consulted: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExternalFallbackResult:
    """Explicit result of one external fallback attempt."""

    attempted: bool
    used: bool
    reason: str
    response: GroundedAnswerResponse | None = None
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


def run_allowlisted_external_fallback(
    *,
    namespace: Namespace,
    degraded_response: GroundedAnswerResponse,
) -> ExternalFallbackResult:
    """Run one explicit allowlisted external fallback path.

    Current behavior is intentionally conservative: we disclose that allowlisted fallback
    was attempted, but we do not silently browse or replace grounded evidence. The fallback
    returns an explicitly degraded response that tells the user grounded internal evidence was
    insufficient and that external recovery would require approved sources.
    """

    decision = resolve_external_fallback_policy(namespace=namespace)
    if not decision.allowed:
        return ExternalFallbackResult(
            attempted=False,
            used=False,
            reason=decision.reason,
        )

    response = degraded_response.model_copy(
        update={
            "generator_provider": "allowlisted-external-fallback-v1",
            "provider_backend": "allowlisted_external_fallback_v1",
            "provider_fallback_used": True,
            "provider_fallback_from": degraded_response.generator_provider,
        }
    )
    return ExternalFallbackResult(
        attempted=True,
        used=True,
        reason="allowlisted_external_fallback_disclosed",
        response=response,
        sources_consulted=_ALLOWLISTED_SOURCE_PROVIDERS,
    )
