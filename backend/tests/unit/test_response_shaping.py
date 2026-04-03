"""Unit tests for structured response shaping."""

from __future__ import annotations

import uuid

import pytest

from app.pipeline.contracts import EvidenceItem, EvidencePackage, GroundedAnswerDraft
from app.services.response_shaping import (
    ResponseShapingError,
    shape_degraded_response,
    shape_grounded_response,
)


def _evidence_item(
    *,
    citation_id: str,
    chunk_id: str,
    text: str,
    score: float,
) -> EvidenceItem:
    return EvidenceItem(
        citation_id=citation_id,
        chunk_id=chunk_id,
        tenant_id=uuid.uuid4(),
        namespace_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        text=text,
        score=score,
        sources=("dense", "sparse"),
    )


def test_shape_grounded_response_builds_structured_citations() -> None:
    """Response shaping should return a structured answer with ordered citations."""

    first = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="Grounded supports tenant-safe uploads.",
        score=0.9,
    )
    second = _evidence_item(
        citation_id="E002",
        chunk_id="chunk-2",
        text="It also tracks ingestion job status.",
        score=0.8,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1", "chunk-2"],
        selected_evidence_ids=["chunk-1", "chunk-2"],
        items=[first, second],
    )
    draft = GroundedAnswerDraft(
        answer_text=(
            "Grounded supports tenant-safe uploads. [E001] "
            "It also tracks ingestion job status. [E002]"
        ),
        cited_evidence_ids=["chunk-1", "chunk-2"],
        citation_snippets={
            "chunk-1": "Grounded supports tenant-safe uploads.",
            "chunk-2": "It also tracks ingestion job status.",
        },
        generator_provider="local-grounded-v1",
        support_coverage=1.0,
        source_diversity=2,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert response.answer == draft.answer_text
    assert response.verification_status == "passed"
    assert response.confidence_score == 1.0
    assert response.degraded_reasons == []
    assert [citation.citation_id for citation in response.citations] == ["E001", "E002"]
    assert response.citations[0].quote == "Grounded supports tenant-safe uploads."


def test_shape_grounded_response_deduplicates_repeated_citations() -> None:
    """Repeated cited chunk ids should only appear once in the final response."""

    item = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="Grounded returns cited answers.",
        score=0.9,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[item],
    )
    draft = GroundedAnswerDraft(
        answer_text="Grounded returns cited answers. [E001] [E001]",
        cited_evidence_ids=["chunk-1", "chunk-1"],
        citation_snippets={"chunk-1": "Grounded returns cited answers."},
        generator_provider="local-grounded-v1",
        support_coverage=1.0,
        source_diversity=2,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert len(response.citations) == 1
    assert response.citations[0].chunk_id == "chunk-1"


def test_shape_grounded_response_rejects_unknown_evidence_reference() -> None:
    """Drafts that cite unknown chunk ids should fail cleanly."""

    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="Grounded uses evidence packaging.",
                score=0.7,
            )
        ],
    )
    draft = GroundedAnswerDraft(
        answer_text="Grounded uses evidence packaging. [E999]",
        cited_evidence_ids=["chunk-missing"],
        citation_snippets={"chunk-missing": "Grounded uses evidence packaging."},
        generator_provider="local-grounded-v1",
    )

    with pytest.raises(ResponseShapingError, match="unknown evidence chunk"):
        shape_grounded_response(draft=draft, evidence_package=package)


def test_shape_degraded_response_returns_structured_fallback() -> None:
    """Degraded responses should use the same answer schema with explicit reasons."""

    response = shape_degraded_response(
        reason="NO_GROUNDED_EVIDENCE",
        answer_text="I could not find grounded evidence for this query.",
    )

    assert response.answer == "I could not find grounded evidence for this query."
    assert response.citations == []
    assert response.confidence_score == 0.0
    assert response.verification_status == "degraded"
    assert response.degraded_reasons == ["NO_GROUNDED_EVIDENCE"]


def test_shape_grounded_response_degrades_low_confidence_support() -> None:
    """Weak support should still return the answer but mark it degraded."""

    item = _evidence_item(
        citation_id="E001",
        chunk_id="chunk-1",
        text="One weakly ranked supporting snippet.",
        score=0.001,
    )
    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1", "chunk-2", "chunk-3"],
        selected_evidence_ids=["chunk-1"],
        items=[item],
    )
    draft = GroundedAnswerDraft(
        answer_text="One weakly ranked supporting snippet. [E001]",
        cited_evidence_ids=["chunk-1"],
        citation_snippets={"chunk-1": "One weakly ranked supporting snippet."},
        generator_provider="local-grounded-v1",
        support_coverage=0.2,
        source_diversity=1,
    )

    response = shape_grounded_response(draft=draft, evidence_package=package)

    assert response.verification_status == "degraded"
    assert response.degraded_reasons == ["LOW_CONFIDENCE_SUPPORT"]
    assert response.confidence_score < 0.25
