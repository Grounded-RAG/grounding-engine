"""Evaluation fixtures that keep the Standard grounded baseline honest."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from app.core.llm_client import GroundedGenerationError, generate_grounded_draft
from app.pipeline.contracts import EvidenceItem, EvidencePackage
from app.services.response_shaping import shape_grounded_response


FIXTURE_PATH = Path(__file__).with_name("fixtures") / "standard_quality_cases.json"


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


def _load_cases() -> list[dict[str, object]]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: str(case["name"]))
def test_standard_quality_cases(case: dict[str, object]) -> None:
    """Golden quality cases should keep the Standard local baseline stable."""

    evidence_payload = case["evidence"]
    assert isinstance(evidence_payload, list)
    items = [
        _evidence_item(
            citation_id=str(entry["citation_id"]),
            chunk_id=str(entry["chunk_id"]),
            text=str(entry["text"]),
            score=float(entry["score"]),
        )
        for entry in evidence_payload
        if isinstance(entry, dict)
    ]
    package = EvidencePackage(
        retrieved_chunk_ids=[item.chunk_id for item in items],
        selected_evidence_ids=[item.chunk_id for item in items],
        items=items,
    )

    expected_type = str(case["expected_type"])
    if expected_type == "generation_error":
        with pytest.raises(GroundedGenerationError, match=str(case["expected_error_contains"])):
            generate_grounded_draft(
                query_text=str(case["query"]),
                evidence_package=package,
            )
        return

    draft = generate_grounded_draft(
        query_text=str(case["query"]),
        evidence_package=package,
    )
    response = shape_grounded_response(
        draft=draft,
        evidence_package=package,
    )

    assert response.verification_status == "passed"
    assert response.support_summary == "grounded"
    for expected_fragment in case["expected_answer_contains"]:
        assert str(expected_fragment) in response.answer
    assert [citation.citation_id for citation in response.citations] == [
        str(citation_id) for citation_id in case["expected_citation_ids"]
    ]
