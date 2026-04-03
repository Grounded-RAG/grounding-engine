"""Helpers for trust metadata exposed by Standard grounded responses."""

from __future__ import annotations

from typing import Literal


ConfidenceLabel = Literal["low", "medium", "high"]
SupportSummary = Literal["grounded", "partial", "insufficient"]


def confidence_label_for_score(score: float) -> ConfidenceLabel:
    """Map a normalized confidence score into a stable qualitative label."""

    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def support_summary_for_response(
    *,
    confidence_score: float,
    degraded_reasons: list[str],
    citation_count: int,
) -> SupportSummary:
    """Summarize whether the final answer is grounded, partial, or insufficient."""

    normalized_reasons = {reason.strip().upper() for reason in degraded_reasons if reason.strip()}
    if citation_count == 0 or normalized_reasons & {
        "NO_GROUNDED_EVIDENCE",
        "INSUFFICIENT_SUPPORT",
        "LOW_CONFIDENCE_SUPPORT",
        "QUERY_REQUIRES_CLARIFICATION",
        "INSUFFICIENT_QUERY_ALIGNMENT",
    }:
        return "insufficient"
    if confidence_score < 0.65:
        return "partial"
    return "grounded"


def provider_metadata(generator_provider: str) -> dict[str, str | bool | None]:
    """Parse one persisted provider string into structured provider metadata."""

    normalized = generator_provider.strip()
    fallback_used = ":fallback_from_" in normalized
    fallback_from = None
    base_provider = normalized
    if fallback_used:
        base_provider, fallback_from = normalized.split(":fallback_from_", 1)

    provider_backend = "unknown"
    provider_model: str | None = None
    if base_provider == "local-grounded-v1":
        provider_backend = "local_grounded_v1"
    elif base_provider == "degraded-handler-v1":
        provider_backend = "degraded_handler_v1"
    elif base_provider == "clarification-handler-v1":
        provider_backend = "clarification_handler_v1"
    elif base_provider.startswith("gemini:"):
        provider_backend = "gemini_v1"
        provider_model = base_provider.split(":", 1)[1].strip() or None
    elif base_provider.startswith("openai-compatible:"):
        provider_backend = "openai_compatible_v1"
        provider_model = base_provider.split(":", 1)[1].strip() or None
    elif base_provider:
        provider_backend = base_provider.replace("-", "_")

    return {
        "provider_backend": provider_backend,
        "provider_model": provider_model,
        "provider_fallback_used": fallback_used,
        "provider_fallback_from": fallback_from.strip() if fallback_from else None,
    }
