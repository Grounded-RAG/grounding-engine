"""Policy-gated allowlisted external fallback helpers for Critical queries."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from app.core.telemetry import get_logger
from app.models import Namespace
from app.schemas.query import GroundedAnswerResponse


logger = get_logger("app.external_fallback")

# Every provider name in this tuple must be explicitly approved.
_ALLOWLISTED_SOURCE_PROVIDERS = ("duckduckgo_instant_answer_v1",)

_DDGS_INSTANT_URL = "https://api.duckduckgo.com/"
_DDGS_TIMEOUT_SECONDS = 8
_DDGS_MAX_SNIPPETS = 3

# Optional override: set EXTERNAL_SEARCH_API_KEY to use a paid provider instead.
_SEARCH_API_KEY = os.environ.get("EXTERNAL_SEARCH_API_KEY", "")


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


async def _fetch_duckduckgo_snippets(query: str) -> list[str]:
    """Fetch instant-answer snippets from the DuckDuckGo API.

    Returns up to _DDGS_MAX_SNIPPETS plain-text snippets.
    Returns an empty list on any network or parse error — the caller
    degrades gracefully rather than raising.
    """
    params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "skip_disambig": "1",
        "no_redirect": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=_DDGS_TIMEOUT_SECONDS) as client:
            resp = await client.get(_DDGS_INSTANT_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("external_fallback_ddgs_failed", reason=str(exc))
        return []

    snippets: list[str] = []

    abstract = data.get("AbstractText", "").strip()
    if abstract:
        snippets.append(abstract)

    for related in data.get("RelatedTopics", []):
        if not isinstance(related, dict):
            continue
        text = related.get("Text", "").strip()
        if text and text not in snippets:
            snippets.append(text)
        if len(snippets) >= _DDGS_MAX_SNIPPETS:
            break

    return snippets[:_DDGS_MAX_SNIPPETS]


async def run_allowlisted_external_fallback(
    *,
    namespace: Namespace,
    degraded_response: GroundedAnswerResponse,
    query_text: str = "",
) -> ExternalFallbackResult:
    """Run one explicit allowlisted external fallback path.

    Behavior:
    - Policy gate checked first; returns immediately if not allowed.
    - Attempts a real DuckDuckGo instant-answer lookup for query_text.
    - If snippets are retrieved, assembles them into a disclosed answer that
      clearly attributes the source class.
    - If the lookup fails or returns nothing, falls back to a safe degraded
      response that discloses the attempt.
    - Never silently browses, never replaces grounded internal evidence.
    - Always discloses source_class in the response and trace.
    """
    decision = resolve_external_fallback_policy(namespace=namespace)
    if not decision.allowed:
        return ExternalFallbackResult(
            attempted=False,
            used=False,
            reason=decision.reason,
        )

    source_provider = _ALLOWLISTED_SOURCE_PROVIDERS[0]
    snippets: list[str] = []

    if query_text.strip():
        snippets = await _fetch_duckduckgo_snippets(query_text.strip())

    if snippets:
        combined = " ".join(snippets)
        answer_text = (
            f"[External source: {source_provider}] "
            f"The grounded internal evidence was insufficient. "
            f"The following was retrieved from an allowlisted external source: {combined}"
        )
        response = degraded_response.model_copy(
            update={
                "answer": answer_text,
                "generator_provider": "allowlisted-external-fallback-v1",
                "provider_backend": source_provider,
                "provider_fallback_used": True,
                "provider_fallback_from": degraded_response.generator_provider,
            }
        )
        return ExternalFallbackResult(
            attempted=True,
            used=True,
            reason="allowlisted_external_snippets_retrieved",
            response=response,
            sources_consulted=(source_provider,),
        )

    # No snippets: disclose the attempt but return the degraded response as-is.
    response = degraded_response.model_copy(
        update={
            "generator_provider": "allowlisted-external-fallback-v1",
            "provider_backend": source_provider,
            "provider_fallback_used": True,
            "provider_fallback_from": degraded_response.generator_provider,
        }
    )
    return ExternalFallbackResult(
        attempted=True,
        used=False,
        reason="allowlisted_external_fallback_no_snippets",
        response=response,
        sources_consulted=(source_provider,),
    )
