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


def test_extract_claims_preserves_common_abbreviations() -> None:
    """The sentence splitter must not fragment titles like 'Dr.' or 'e.g.'."""

    claims = extract_claims(
        "Dr. Smith led the rollout. The team adopted the policy."
    )
    assert claims == (
        "Dr. Smith led the rollout.",
        "The team adopted the policy.",
    )


def test_extract_claims_handles_initials_and_incitations() -> None:
    """The splitter should not split inside U.S., U.K., i.e., etc."""

    claims = extract_claims(
        "Grounded is built in the U.S. It is deployed widely. "
        "The product, i.e. the engine, ships weekly."
    )
    assert claims == (
        "Grounded is built in the U.S.",
        "It is deployed widely.",
        "The product, i.e. the engine, ships weekly.",
    )


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
    assert result.retry_query_text == "offline exports"


def test_verify_critical_response_prioritizes_missing_claim_terms_for_retry() -> None:
    result = verify_critical_response(
        response=_response("Grounded supports offline exports without sync."),
        evidence_package=_evidence_package("Grounded supports tenant-safe uploads."),
    )

    assert result.decision == "refuse"
    assert result.retry_query_text == "offline exports without sync"


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
    assert result.retry_query_text == "exports"


def test_verify_critical_response_degrades_contradictory_evidence() -> None:
    result = verify_critical_response(
        response=_response("Grounded supports tenant-safe uploads."),
        evidence_package=_conflicting_evidence_package(),
    )

    assert result.decision == "degrade"
    assert result.reason == "CONTRADICTORY_EVIDENCE"
    assert result.contradiction_detected is True


def test_verify_critical_response_detects_morph_only_negation_contradiction() -> None:
    """When the only claim term that matches the evidence does so via
    morphological root (e.g. ``exports`` -> ``export``) and a negation
    is adjacent to that position, the contradiction must still be detected.

    Regression for the negation-proximity bug: ``evidence_norm.find(term)``
    returns -1 for morph-only matches, the code substituted ``9999`` for
    the position, and the proximity test (``< 40`` chars) silently failed.
    """

    result = verify_critical_response(
        response=_response("Exports happen every morning."),
        evidence_package=_evidence_package("We do not export at all."),
    )

    assert result.decision == "degrade"
    assert result.reason == "CONTRADICTORY_EVIDENCE"
    assert result.contradiction_detected is True


def test_verify_critical_response_unions_matched_terms_across_chunks() -> None:
    """A claim whose terms are spread across multiple chunks (no single
    chunk fully supports it) should still be accepted when every term
    appears somewhere in the evidence.

    Regression for the CRAG missing-terms bug: the per-chunk assessment
    picked the best single chunk and used only its missing terms, so a
    claim that was supported in aggregate (but no chunk alone) was
    refused and retried for terms that were already covered.
    """

    document_id = uuid.uuid4()
    evidence_package = EvidencePackage(
        retrieved_chunk_ids=["chunk-1", "chunk-2", "chunk-3"],
        selected_evidence_ids=["chunk-1", "chunk-2", "chunk-3"],
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
                    "text": "Acme builds the platform.",
                    "score": 0.9,
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
                    "text": "The platform exports data every week.",
                    "score": 0.88,
                    "sources": ("sparse",),
                    "section_title": "Pipelines",
                    "section_slug": "pipelines",
                    "chunk_role": "body",
                    "starts_with_heading": False,
                    "is_list_block": False,
                },
            )(),
            type(
                "EvidenceItemStub",
                (),
                {
                    "citation_id": "E003",
                    "chunk_id": "chunk-3",
                    "tenant_id": uuid.uuid4(),
                    "namespace_id": uuid.uuid4(),
                    "document_id": document_id,
                    "chunk_index": 2,
                    "text": "Widgets are stored in a secure vault.",
                    "score": 0.85,
                    "sources": ("dense", "sparse"),
                    "section_title": "Storage",
                    "section_slug": "storage",
                    "chunk_role": "body",
                    "starts_with_heading": False,
                    "is_list_block": False,
                },
            )(),
        ],
    )

    result = verify_critical_response(
        response=_response("Acme exports widgets."),
        evidence_package=evidence_package,
    )

    assert result.decision == "accept"
    assert result.supported_claim_count == 1
    assert result.unsupported_claim_count == 0
    assert result.retry_query_text in (None, "")
