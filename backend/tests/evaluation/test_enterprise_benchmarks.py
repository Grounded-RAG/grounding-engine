"""Benchmark-style evaluation coverage for Enterprise retrieval upgrades."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
import uuid

import pytest

from app.core.query_analysis import (
    QueryPlan,
    QueryProfile,
    build_query_plan,
    refine_query_plan_for_execution_tier,
)
from app.models import ExecutionTier, FreshnessProfile
from app.pipeline.contracts import FusedRetrievedChunk, RetrievedChunk
from app.services.evidence import package_evidence
from app.services.retrieval import RetrievalBundle, retrieve_hybrid_candidates


class FakeAsyncSession:
    """Minimal async session placeholder for retrieval tests."""

    async def execute(self, statement, params=None):
        del statement, params
        return SimpleNamespace(all=lambda: [])


def _comparison_bundle() -> RetrievalBundle:
    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    option_a_doc = uuid.uuid4()
    option_b_doc = uuid.uuid4()
    return RetrievalBundle(
        sparse_hits=[],
        dense_hits=[],
        fused_hits=[
            FusedRetrievedChunk(
                chunk_id="option-a-cost",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=option_a_doc,
                chunk_index=0,
                text="Option A costs $400 per month and needs two engineers.",
                fused_score=0.96,
                sources=("dense", "sparse"),
                section_title="Option A",
                section_slug="option-a",
                chunk_role="section_body",
            ),
            FusedRetrievedChunk(
                chunk_id="option-a-uptime",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=option_a_doc,
                chunk_index=1,
                text="Option A provides 99.9% uptime coverage.",
                fused_score=0.9,
                sources=("dense",),
                section_title="Option A",
                section_slug="option-a",
                chunk_role="section_list",
                is_list_block=True,
            ),
            FusedRetrievedChunk(
                chunk_id="option-b-cost",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=option_b_doc,
                chunk_index=0,
                text="Option B costs $520 per month and needs one engineer.",
                fused_score=0.88,
                sources=("sparse",),
                section_title="Option B",
                section_slug="option-b",
                chunk_role="section_body",
            ),
        ],
    )


def _multi_part_bundle() -> RetrievalBundle:
    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    document_id = uuid.uuid4()
    return RetrievalBundle(
        sparse_hits=[],
        dense_hits=[],
        fused_hits=[
            FusedRetrievedChunk(
                chunk_id="pilot-start",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=document_id,
                chunk_index=0,
                text="The pilot started in March 2025.",
                fused_score=0.95,
                sources=("dense", "sparse"),
                section_title="Pilot Overview",
                section_slug="pilot-overview",
                chunk_role="section_body",
            ),
            FusedRetrievedChunk(
                chunk_id="charger-installation",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=document_id,
                chunk_index=1,
                text="The charging stations were installed in April 2025.",
                fused_score=0.92,
                sources=("dense",),
                section_title="Charging Infrastructure",
                section_slug="charging-infrastructure",
                chunk_role="section_body",
            ),
            FusedRetrievedChunk(
                chunk_id="pilot-end",
                tenant_id=tenant_id,
                namespace_id=namespace_id,
                document_id=document_id,
                chunk_index=2,
                text="The pilot ended in July 2025.",
                fused_score=0.89,
                sources=("sparse",),
                section_title="Pilot Overview",
                section_slug="pilot-overview",
                chunk_role="section_body",
            ),
        ],
    )


def test_enterprise_benchmarks_show_planning_and_evidence_uplift() -> None:
    """Enterprise should improve controlled planning and evidence coverage on hard queries."""

    comparison_query = "Compare option A and option B deployment costs and staffing."
    standard_comparison_plan = build_query_plan(comparison_query)
    enterprise_comparison_plan = refine_query_plan_for_execution_tier(
        standard_comparison_plan,
        execution_tier=ExecutionTier.ENTERPRISE,
    )

    comparison_bundle = _comparison_bundle()
    standard_comparison_package = package_evidence(
        comparison_bundle,
        query_text=comparison_query,
        limit=2,
        execution_tier=ExecutionTier.STANDARD,
    )
    enterprise_comparison_package = package_evidence(
        comparison_bundle,
        query_text=comparison_query,
        limit=2,
        execution_tier=ExecutionTier.ENTERPRISE,
    )

    multi_part_query = "When did the pilot start, when were the charging stations installed, and when did the pilot end?"
    multi_part_bundle = _multi_part_bundle()
    standard_multi_part_package = package_evidence(
        multi_part_bundle,
        query_text=multi_part_query,
        limit=1,
        execution_tier=ExecutionTier.STANDARD,
    )
    enterprise_multi_part_package = package_evidence(
        multi_part_bundle,
        query_text=multi_part_query,
        limit=1,
        execution_tier=ExecutionTier.ENTERPRISE,
    )

    standard_score = 0
    enterprise_score = 0

    standard_score += len(standard_comparison_plan.retrieval_queries)
    enterprise_score += len(enterprise_comparison_plan.retrieval_queries)

    standard_score += len({item.document_id for item in standard_comparison_package.items})
    enterprise_score += len({item.document_id for item in enterprise_comparison_package.items})

    standard_score += len(standard_multi_part_package.items)
    enterprise_score += len(enterprise_multi_part_package.items)

    assert enterprise_score > standard_score
    assert any("difference" in query.casefold() for query in enterprise_comparison_plan.retrieval_queries)
    assert len({item.document_id for item in enterprise_comparison_package.items}) == 2
    assert len(enterprise_multi_part_package.items) == 3


@pytest.mark.asyncio()
async def test_enterprise_benchmarks_show_recency_uplift(monkeypatch) -> None:
    """Enterprise should outrank stale documents for explicitly recency-sensitive queries."""

    tenant_id = uuid.uuid4()
    namespace_id = uuid.uuid4()
    old_document_id = uuid.uuid4()
    new_document_id = uuid.uuid4()

    sparse_hits = [
        RetrievedChunk(
            chunk_id="old-policy",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=old_document_id,
            chunk_index=0,
            text="The latest policy version on file is 2023.09.",
            score=0.9,
            rank=1,
            source="sparse",
        ),
        RetrievedChunk(
            chunk_id="new-policy",
            tenant_id=tenant_id,
            namespace_id=namespace_id,
            document_id=new_document_id,
            chunk_index=0,
            text="Policy release 2025.01 was published in January 2025.",
            score=0.7,
            rank=2,
            source="sparse",
        ),
    ]

    async def fake_sparse_retrieve_chunks(**kwargs):
        del kwargs
        return sparse_hits

    async def fake_dense_retrieve_chunks(**kwargs):
        del kwargs
        return []

    async def fake_fetch_supporting_context_hits(**kwargs):
        del kwargs
        return []

    async def fake_fetch_document_freshness_metadata(**kwargs):
        del kwargs
        return {
            old_document_id: datetime(2023, 9, 1, tzinfo=UTC),
            new_document_id: datetime(2025, 1, 10, tzinfo=UTC),
        }

    async def fake_apply_enterprise_reranker(hits, **kwargs):
        del kwargs
        return hits

    monkeypatch.setattr("app.services.retrieval.sparse_retrieve_chunks", fake_sparse_retrieve_chunks)
    monkeypatch.setattr("app.services.retrieval.dense_retrieve_chunks", fake_dense_retrieve_chunks)
    monkeypatch.setattr(
        "app.services.retrieval._fetch_supporting_context_hits",
        fake_fetch_supporting_context_hits,
    )
    monkeypatch.setattr(
        "app.services.retrieval._fetch_document_freshness_metadata",
        fake_fetch_document_freshness_metadata,
    )
    monkeypatch.setattr(
        "app.services.retrieval._apply_enterprise_reranker",
        fake_apply_enterprise_reranker,
    )
    monkeypatch.setattr(
        "app.services.retrieval.get_settings",
        lambda: SimpleNamespace(
            retrieval_candidate_limit=8,
            retrieval_overfetch_factor=4,
            rrf_smoothing_constant=60,
            evidence_package_limit=3,
            enterprise_reranker_candidate_limit=8,
            enterprise_temporal_scoring_enabled=True,
        ),
    )

    plan = QueryPlan(
        raw_query_text="What is the latest policy version?",
        resolved_query_text="What is the latest policy version?",
        profile=QueryProfile(
            raw_text="What is the latest policy version?",
            normalized_text="what is the latest policy version",
            terms=frozenset({"latest", "policy", "version"}),
            expanded_terms=frozenset({"latest", "policy", "version"}),
            attribute_terms=frozenset({"policy version"}),
            context_terms=frozenset(),
            semantic_tags=frozenset({"date"}),
            query_kind="lookup",
            document_reference_rank=None,
        ),
        retrieval_query_text="what is the latest policy version",
        retrieval_queries=("what is the latest policy version",),
        explanation="kind=lookup",
        used_conversation_context=False,
    )

    standard_bundle = await retrieve_hybrid_candidates(
        session=FakeAsyncSession(),
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        query_text="What is the latest policy version?",
        query_plan=plan,
        execution_tier=ExecutionTier.STANDARD,
        freshness_profile=FreshnessProfile.AGGRESSIVE,
        limit=2,
    )
    enterprise_bundle = await retrieve_hybrid_candidates(
        session=FakeAsyncSession(),
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        query_text="What is the latest policy version?",
        query_plan=plan,
        execution_tier=ExecutionTier.ENTERPRISE,
        freshness_profile=FreshnessProfile.AGGRESSIVE,
        limit=2,
    )

    assert [hit.chunk_id for hit in standard_bundle.fused_hits] == ["old-policy", "new-policy"]
    assert [hit.chunk_id for hit in enterprise_bundle.fused_hits] == ["new-policy", "old-policy"]
