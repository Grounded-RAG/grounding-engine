"""Evaluation-style coverage for Critical verification behavior."""

from __future__ import annotations

import uuid

from app.pipeline.contracts import EvidencePackage
from app.schemas.query import CitationResponse, GroundedAnswerResponse
from app.services.verification import verify_critical_response


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


def _package(*texts: str) -> EvidencePackage:
    document_id = uuid.uuid4()
    items = []
    for index, text in enumerate(texts):
        items.append(
            type(
                "EvidenceItemStub",
                (),
                {
                    "citation_id": f"E{index + 1:03d}",
                    "chunk_id": f"chunk-{index + 1}",
                    "tenant_id": uuid.uuid4(),
                    "namespace_id": uuid.uuid4(),
                    "document_id": document_id,
                    "chunk_index": index,
                    "text": text,
                    "score": 0.95 - (index * 0.02),
                    "sources": ("dense", "sparse"),
                    "section_title": "Overview",
                    "section_slug": "overview",
                    "chunk_role": "body",
                    "starts_with_heading": False,
                    "is_list_block": False,
                },
            )()
        )

    return EvidencePackage(
        retrieved_chunk_ids=[item.chunk_id for item in items],
        selected_evidence_ids=[item.chunk_id for item in items],
        items=items,
    )


def test_critical_benchmarks_refuse_unsupported_claims() -> None:
    result = verify_critical_response(
        response=_response("Grounded supports offline exports."),
        evidence_package=_package("Grounded supports tenant-safe uploads."),
    )

    assert result.decision == "refuse"
    assert result.reason == "UNSUPPORTED_CLAIMS"
    assert result.unsupported_claim_count == 1
    assert result.retry_query_text == "offline exports"


def test_critical_benchmarks_degrade_contradictory_evidence() -> None:
    result = verify_critical_response(
        response=_response("Grounded supports tenant-safe uploads."),
        evidence_package=_package(
            "Grounded supports tenant-safe uploads.",
            "Grounded does not support tenant-safe uploads.",
        ),
    )

    assert result.decision == "degrade"
    assert result.reason == "CONTRADICTORY_EVIDENCE"
    assert result.contradiction_detected is True


def test_critical_benchmarks_prepare_bounded_retry_for_partial_support() -> None:
    result = verify_critical_response(
        response=_response("Grounded supports tenant-safe exports."),
        evidence_package=_package("Grounded supports tenant-safe uploads."),
    )

    assert result.decision == "degrade"
    assert result.reason == "PARTIAL_SUPPORT"
    assert result.partially_supported_claim_count == 1
    assert result.retry_query_text == "exports"
