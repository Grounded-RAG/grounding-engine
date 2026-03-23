"""Structured response shaping for grounded answers."""

from __future__ import annotations

from app.pipeline.contracts import EvidenceItem, EvidencePackage, GroundedAnswerDraft
from app.schemas.query import CitationResponse, GroundedAnswerResponse


class ResponseShapingError(RuntimeError):
    """Raised when a grounded draft cannot be shaped into a valid response."""


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
            quote=item.text,
        )
        for item in cited_items
    ]
    confidence_score = round(sum(item.score for item in cited_items) / len(cited_items), 4)

    return GroundedAnswerResponse(
        answer=draft.answer_text,
        citations=citations,
        confidence_score=min(max(confidence_score, 0.0), 1.0),
        verification_status="passed",
        degraded_reasons=[],
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
        verification_status="degraded",
        degraded_reasons=[normalized_reason],
    )
