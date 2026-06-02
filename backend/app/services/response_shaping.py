"""Structured response shaping for grounded answers."""

from __future__ import annotations

import re

from app.config import get_settings
from app.pipeline.contracts import EvidenceItem, EvidencePackage, GroundedAnswerDraft
from app.schemas.query import CitationResponse, GroundedAnswerResponse
from app.services.trust import (
    confidence_label_for_score,
    provider_metadata,
    support_summary_for_response,
)


class ResponseShapingError(RuntimeError):
    """Raised when a grounded draft cannot be shaped into a valid response."""


_WHITESPACE_PATTERN = re.compile(r"\s+")


def _normalize_quote(quote: str, *, max_length: int = 180) -> str:
    """Trim and normalize citation snippets so the inspector stays readable."""

    normalized = _WHITESPACE_PATTERN.sub(" ", quote).strip().strip('"')
    if len(normalized) <= max_length:
        return normalized

    truncated = normalized[: max_length - 1].rsplit(" ", 1)[0].strip()
    if not truncated:
        truncated = normalized[: max_length - 1].strip()
    return f"{truncated}..."


def _calculate_confidence(
    *,
    cited_items: list[EvidenceItem],
    draft: GroundedAnswerDraft,
) -> float:
    """Estimate grounded confidence from retrieval strength and support coverage."""

    average_score = sum(item.score for item in cited_items) / len(cited_items)
    retrieval_signal = min(
        average_score * max(get_settings().rrf_smoothing_constant * 0.4, 1),
        1.0,
    )
    support_signal = min(max(draft.support_coverage, 0.0), 1.0)
    diversity_signal = min(max(draft.source_diversity, 0) / 2, 1.0)
    citation_signal = min(len(cited_items) / 3, 1.0)
    calibrated = min(
        0.45 * retrieval_signal
        + 0.25 * support_signal
        + 0.15 * citation_signal
        + 0.15 * diversity_signal,
        1.0,
    )
    if (
        len(cited_items) >= 2
        and support_signal >= 0.95
        and diversity_signal >= 0.95
    ):
        calibrated = min(calibrated + 0.05, 1.0)
    if len(cited_items) == 1 and support_signal < 0.7:
        calibrated = max(calibrated - 0.08, 0.0)
    if len(cited_items) >= 2 and support_signal < 0.68:
        calibrated = max(calibrated - 0.04, 0.0)
    return round(
        calibrated,
        4,
    )


def shape_grounded_response(
    *,
    draft: GroundedAnswerDraft,
    evidence_package: EvidencePackage,
) -> GroundedAnswerResponse:
    """Shape a grounded draft and evidence package into a structured response."""

    evidence_by_chunk_id = {
        item.chunk_id: item
        for item in evidence_package.items
    }

    cited_items: list[EvidenceItem] = []
    seen_chunk_ids: set[str] = set()
    for chunk_id in draft.cited_evidence_ids:
        if chunk_id in seen_chunk_ids:
            continue
        try:
            item = evidence_by_chunk_id[chunk_id]
        except KeyError as exc:
            raise ResponseShapingError(
                f"Grounded draft referenced unknown evidence chunk: {chunk_id}."
            ) from exc
        cited_items.append(item)
        seen_chunk_ids.add(chunk_id)

    if not cited_items:
        raise ResponseShapingError("Structured responses require at least one citation.")

    citations = [
        CitationResponse(
            citation_id=item.citation_id,
            chunk_id=item.chunk_id,
            document_id=item.document_id,
            chunk_index=item.chunk_index,
            quote=_normalize_quote(draft.citation_snippets.get(item.chunk_id) or item.text),
        )
        for item in cited_items
    ]
    confidence_score = _calculate_confidence(
        cited_items=cited_items,
        draft=draft,
    )
    support_signal = min(max(draft.support_coverage, 0.0), 1.0)
    degraded_reasons: list[str] = []
    if confidence_score < 0.25:
        degraded_reasons.append("LOW_CONFIDENCE_SUPPORT")
    elif confidence_score < 0.5:
        degraded_reasons.append("PARTIAL_EVIDENCE")
    elif (
        len(cited_items) >= 2
        and (confidence_score < 0.7 or support_signal < 0.75)
        and support_signal < 0.82
    ):
        degraded_reasons.append("AMBIGUOUS_SUPPORT")
    # Invariant: degraded_reasons is non-empty => verification_status == "degraded".
    verification_status = "degraded" if degraded_reasons else "passed"
    confidence_label = confidence_label_for_score(confidence_score)
    support_summary = support_summary_for_response(
        confidence_score=confidence_score,
        degraded_reasons=degraded_reasons,
        citation_count=len(citations),
    )
    provider_info = provider_metadata(draft.generator_provider)

    return GroundedAnswerResponse(
        answer=draft.answer_text,
        citations=citations,
        confidence_score=min(max(confidence_score, 0.0), 1.0),
        confidence_label=confidence_label,
        support_summary=support_summary,
        verification_status=verification_status,
        degraded_reasons=degraded_reasons,
        generator_provider=draft.generator_provider,
        provider_backend=str(provider_info["provider_backend"]),
        provider_model=provider_info["provider_model"],
        provider_fallback_used=bool(provider_info["provider_fallback_used"]),
        provider_fallback_from=provider_info["provider_fallback_from"],
    )


def shape_degraded_response(
    *,
    reason: str,
    answer_text: str | None = None,
) -> GroundedAnswerResponse:
    """Return an honest degraded response when evidence is insufficient or unsafe."""

    normalized_reason = reason.strip()
    if not normalized_reason:
        raise ResponseShapingError("Degraded responses require a non-empty reason.")

    return GroundedAnswerResponse(
        answer=answer_text
        or "I do not have enough grounded evidence to answer confidently.",
        citations=[],
        confidence_score=0.0,
        confidence_label="low",
        support_summary="insufficient",
        verification_status="degraded",
        degraded_reasons=[normalized_reason],
        generator_provider="degraded-handler-v1",
        provider_backend="degraded_handler_v1",
        provider_model=None,
        provider_fallback_used=False,
        provider_fallback_from=None,
    )
