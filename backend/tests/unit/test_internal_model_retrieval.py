"""Unit tests for Critical internal model retrieval scaffolding."""

from __future__ import annotations

import uuid

from app.pipeline.contracts import EvidencePackage, FusedRetrievedChunk
from app.services.internal_model_retrieval import resolve_internal_model_retrieval_policy
from app.services.internal_model_retrieval import run_internal_model_retrieval


def test_internal_model_retrieval_policy_stays_disabled_without_dataset_opt_in() -> None:
    namespace = type("NamespaceStub", (), {"allow_internal_model_retrieval": False})()

    decision = resolve_internal_model_retrieval_policy(namespace=namespace)

    assert decision.allowed is False
    assert decision.reason == "policy_disabled"
    assert decision.attempted is False


def test_internal_model_retrieval_policy_allows_dataset_opt_in() -> None:
    namespace = type("NamespaceStub", (), {"allow_internal_model_retrieval": True})()

    decision = resolve_internal_model_retrieval_policy(namespace=namespace)

    assert decision.allowed is True
    assert decision.reason == "policy_enabled"
    assert decision.attempted is False


def _evidence_package() -> EvidencePackage:
    document_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    return EvidencePackage(
        retrieved_chunk_ids=["chunk-1", "chunk-2"],
        selected_evidence_ids=["chunk-1"],
        items=[
            type(
                "EvidenceItemStub",
                (),
                {
                    "citation_id": "E001",
                    "chunk_id": "chunk-1",
                    "tenant_id": tenant_id,
                    "namespace_id": namespace_id,
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
            )()
        ],
    )


def test_internal_model_retrieval_expands_with_additional_grounded_candidates() -> None:
    namespace = type("NamespaceStub", (), {"allow_internal_model_retrieval": True})()
    evidence_package = _evidence_package()
    extra_hit = FusedRetrievedChunk(
        chunk_id="chunk-2",
        tenant_id=evidence_package.items[0].tenant_id,
        namespace_id=evidence_package.items[0].namespace_id,
        document_id=evidence_package.items[0].document_id,
        chunk_index=1,
        text="Grounded also supports offline exports.",
        fused_score=0.91,
        sources=("sparse",),
    )

    result = run_internal_model_retrieval(
        namespace=namespace,
        evidence_package=evidence_package,
        fused_hits=[extra_hit],
    )

    assert result.attempted is True
    assert result.used is True
    assert result.reason == "bounded_internal_retrieval_expanded"
    assert result.evidence_package is not None
    assert result.evidence_package.selected_evidence_ids == ["chunk-1", "chunk-2"]
    assert len(result.evidence_package.items) == 2


def test_internal_model_retrieval_noops_without_new_candidates() -> None:
    namespace = type("NamespaceStub", (), {"allow_internal_model_retrieval": True})()
    evidence_package = _evidence_package()

    result = run_internal_model_retrieval(
        namespace=namespace,
        evidence_package=evidence_package,
        fused_hits=[],
    )

    assert result.attempted is True
    assert result.used is False
    assert result.reason == "no_additional_retrieval_candidates"
