"""Unit tests for answer orchestration over grounded evidence."""

from __future__ import annotations

import uuid

import pytest

from app.pipeline.contracts import EvidenceItem, EvidencePackage, GroundedAnswerDraft
from app.services.answering import answer_from_evidence


def _evidence_item(*, citation_id: str, chunk_id: str, text: str, score: float) -> EvidenceItem:
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

@pytest.mark.asyncio()
async def test_answer_from_evidence_returns_grounded_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer orchestration should return a passed grounded response when evidence exists."""

    async def fake_generate_answer_from_evidence(*, query_text: str, evidence_package: EvidencePackage):
        del query_text, evidence_package
        return GroundedAnswerDraft(
            answer="Grounded returns cited answers.",
            cited_chunk_ids=["chunk-1"],
            confidence=0.92,
        )

    monkeypatch.setattr(
        "app.services.answering.generate_answer_from_evidence",
        fake_generate_answer_from_evidence,
    )

    package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            _evidence_item(
                citation_id="E001",
                chunk_id="chunk-1",
                text="Grounded returns cited answers.",
                score=0.9,
            )
        ],
    )

    response = await answer_from_evidence(
        query_text="What does grounded return?",
        evidence_package=package,
    )

    assert response.verification_status == "passed"
    assert response.citations[0].citation_id == "E001"
    assert response.degraded_reasons == []
    assert response.confidence_label == "high"
    assert response.support_summary == "grounded"


@pytest.mark.asyncio()
async def test_answer_from_evidence_returns_degraded_when_evidence_missing() -> None:
    """Answer orchestration should return a degraded response when no evidence exists."""

    response = await answer_from_evidence(
        query_text="What does grounded return?",
        evidence_package=EvidencePackage(
            retrieved_chunk_ids=[],
            selected_evidence_ids=[],
            items=[],
        ),
    )

    assert response.verification_status == "degraded"
    assert response.citations == []
    assert response.degraded_reasons == ["NO_GROUNDED_EVIDENCE"]
    assert response.support_summary == "insufficient"
