"""Unit tests for Critical verification helpers."""

from __future__ import annotations

import uuid

from app.pipeline.contracts import EvidencePackage
from app.schemas.query import CitationResponse, GroundedAnswerResponse
from app.services.verification import extract_claims, verify_critical_response


def _response(answer: str) -> GroundedAnswerResponse:
    document_id = uuid.uuid4()
    return GroundedAnswerResponse(
        answer=answer,
        citations=[
            CitationResponse(
                citation_id="E001",
                chunk_id="chunk-1",
                document_id=document_id,
                chunk_index=0,
                quote="Grounded supports tenant-safe uploads.",
            )
        ],
        confidence_score=0.82,
        confidence_label="high",
        support_summary="grounded",
        verification_status="passed",
        degraded_reasons=[],
        generator_provider="local-grounded-v1",
        provider_backend="local_grounded_v1",
        provider_model=None,
        provider_fallback_used=False,
        provider_fallback_from=None,
    )


def _evidence_package(text: str) -> EvidencePackage:
    document_id = uuid.uuid4()
    return EvidencePackage(
        retrieved_chunk_ids=["chunk-1"],
        selected_evidence_ids=["chunk-1"],
        items=[
            type(
                "EvidenceItemStub",
                (),
                {
                    "citation_id": "E001",
                    "chunk_id": "chunk-1",
                    "tenant_id": uuid.uuid4(),
                    "namespace_id": uuid.uuid4(),
                    "document_id": document_id,
                    "chunk_index": 0,
                    "text": text,
                    "score": 0.95,
                    "sources": ("dense", "sparse"),
                    "section_title": "Overview",
                    "section_slug": "overview",
                    "chunk_role": "body",
                    "starts_with_heading": False,
                    "is_list_block": False,
                },
            )()
        ],
    )


def _conflicting_evidence_package() -> EvidencePackage:
    document_id = uuid.uuid4()
    return EvidencePackage(
        retrieved_chunk_ids=["chunk-1", "chunk-2"],
        selected_evidence_ids=["chunk-1", "chunk-2"],
        items=[
            type(
                "EvidenceItemStub",
                (),
                {
                    "citation_id": "E001",
                    "chunk_id": "chunk-1",
                    "tenant_id": uuid.uuid4(),
                    "namespace_id": uuid.uuid4(),
                    "document_id": document_id,
                    "chunk_index": 0,
                    "text": "Grounded supports tenant-safe uploads.",
                    "score": 0.95,
                    "sources": ("dense",),
                    "section_title": "Overview",
                    "section_slug": "overview",
                    "chunk_role": "body",
                    "starts_with_heading": False,
                    "is_list_block": False,
                },
            )(),
            type(
                "EvidenceItemStub",
                (),
                {
                    "citation_id": "E002",
                    "chunk_id": "chunk-2",
                    "tenant_id": uuid.uuid4(),
                    "namespace_id": uuid.uuid4(),
                    "document_id": document_id,
                    "chunk_index": 1,
                    "text": "Grounded does not support tenant-safe uploads.",
                    "score": 0.92,
                    "sources": ("sparse",),
                    "section_title": "Exceptions",
                    "section_slug": "exceptions",
                    "chunk_role": "body",
                    "starts_with_heading": False,
                    "is_list_block": False,
                },
            )(),
        ],
    )


def test_extract_claims_splits_sentences() -> None:
    claims = extract_claims("Grounded supports uploads. It cites evidence.")
    assert claims == ("Grounded supports uploads.", "It cites evidence.")


def test_verify_critical_response_accepts_supported_claims() -> None:
    result = verify_critical_response(
        response=_response("Grounded supports tenant-safe uploads."),
        evidence_package=_evidence_package("Grounded supports tenant-safe uploads."),
    )

    assert result.decision == "accept"
    assert result.reason is None
    assert result.claims[0].status == "supported"
    assert result.unsupported_claims_detected is False


def test_verify_critical_response_refuses_unsupported_claims() -> None:
    result = verify_critical_response(
        response=_response("Grounded supports offline exports."),
        evidence_package=_evidence_package("Grounded supports tenant-safe uploads."),
    )

    assert result.decision == "refuse"
    assert result.reason == "UNSUPPORTED_CLAIMS"
    assert result.claims[0].status == "unsupported"
    assert result.unsupported_claims_detected is True
    assert result.unsupported_claim_count == 1


def test_verify_critical_response_degrades_partially_supported_claims() -> None:
    result = verify_critical_response(
        response=_response("Grounded supports tenant-safe exports."),
        evidence_package=_evidence_package("Grounded supports tenant-safe uploads."),
    )

    assert result.decision == "degrade"
    assert result.reason == "PARTIAL_SUPPORT"
    assert result.claims[0].status == "partially_supported"
    assert result.partially_supported_claim_count == 1
    assert result.supported_claim_count == 0


def test_verify_critical_response_degrades_contradictory_evidence() -> None:
    result = verify_critical_response(
        response=_response("Grounded supports tenant-safe uploads."),
        evidence_package=_conflicting_evidence_package(),
    )

    assert result.decision == "degrade"
    assert result.reason == "CONTRADICTORY_EVIDENCE"
    assert result.contradiction_detected is True
