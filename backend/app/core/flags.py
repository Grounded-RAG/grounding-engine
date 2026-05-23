"""Runtime feature flags for Critical-tier and advanced retrieval features."""

from __future__ import annotations

import os


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def is_semantic_verification_enabled() -> bool:
    """Use word-boundary + morphological matching instead of plain substring overlap."""
    return _env_bool("ENABLE_SEMANTIC_VERIFICATION", default=True)


def is_multi_attempt_crag_enabled() -> bool:
    """Allow more than one corrective-retrieval attempt per Critical query."""
    return _env_bool("ENABLE_MULTI_ATTEMPT_CRAG", default=True)


def is_long_context_retrieval_enabled() -> bool:
    """Run LLM-backed synthesis over the full retrieved candidate set, not just top-k."""
    return _env_bool("ENABLE_LONG_CONTEXT_RETRIEVAL", default=False)


def is_freshness_conflict_resolution_enabled() -> bool:
    """Actively re-select between conflicting chunks based on source freshness."""
    return _env_bool("ENABLE_FRESHNESS_CONFLICT_RESOLUTION", default=True)


def max_crag_attempts() -> int:
    """Maximum corrective-retrieval attempts allowed per Critical query (1–5)."""
    try:
        return max(1, min(5, int(os.environ.get("MAX_CRAG_ATTEMPTS", "3"))))
    except ValueError:
        return 3


def min_evidence_quality_improvement() -> float:
    """Minimum average support-score improvement required before accepting corrective evidence."""
    try:
        return float(os.environ.get("MIN_EVIDENCE_QUALITY_IMPROVEMENT", "0.1"))
    except ValueError:
        return 0.1
