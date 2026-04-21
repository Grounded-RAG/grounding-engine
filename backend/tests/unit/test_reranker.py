"""Unit tests for Enterprise reranker interface resolution."""

from __future__ import annotations

import json
import uuid

import pytest

from app.config import Settings
from app.core.reranker import (
    DisabledReranker,
    GeminiEnterpriseReranker,
    StubEnterpriseReranker,
    resolve_retrieval_reranker,
)
from app.models import ExecutionTier
from app.pipeline.contracts import FusedRetrievedChunk


def _fused_hit(chunk_id: str, score: float) -> FusedRetrievedChunk:
    """Build one minimal fused hit for reranker tests."""

    return FusedRetrievedChunk(
        chunk_id=chunk_id,
        tenant_id=uuid.uuid4(),
        namespace_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        chunk_index=0,
        text=f"Chunk {chunk_id}",
        fused_score=score,
        sources=("dense", "sparse"),
    )


def test_resolve_retrieval_reranker_returns_disabled_for_standard_tier() -> None:
    """Standard retrieval should never opt into the Enterprise reranker path."""

    reranker = resolve_retrieval_reranker(
        execution_tier=ExecutionTier.STANDARD,
        settings=Settings(),
    )

    assert isinstance(reranker, DisabledReranker)


def test_resolve_retrieval_reranker_returns_stub_when_enabled() -> None:
    """Enterprise retrieval should resolve the configured stub backend cleanly."""

    reranker = resolve_retrieval_reranker(
        execution_tier=ExecutionTier.ENTERPRISE,
        settings=Settings(
            enterprise_enabled=True,
            enterprise_reranker_enabled=True,
            enterprise_reranker_backend="stub",
        ),
    )

    assert isinstance(reranker, StubEnterpriseReranker)


def test_resolve_retrieval_reranker_returns_gemini_backend_when_configured() -> None:
    """Enterprise retrieval should resolve a real Gemini backend when configured."""

    reranker = resolve_retrieval_reranker(
        execution_tier=ExecutionTier.ENTERPRISE,
        settings=Settings(
            enterprise_enabled=True,
            enterprise_reranker_enabled=True,
            enterprise_reranker_backend="gemini_v1",
            gemini_api_key="test-key",
        ),
    )

    assert isinstance(reranker, GeminiEnterpriseReranker)


@pytest.mark.asyncio()
async def test_disabled_reranker_is_pass_through() -> None:
    """Disabled reranking should preserve order and original fused scores."""

    reranker = DisabledReranker(reason="test_disabled")
    hits = [_fused_hit("chunk-1", 0.9), _fused_hit("chunk-2", 0.7)]

    result = await reranker.rerank(
        query_text="What happened?",
        hits=hits,
        limit=2,
    )

    assert result.applied is False
    assert [hit.chunk_id for hit in result.hits] == ["chunk-1", "chunk-2"]
    assert [hit.score for hit in result.hits] == [0.9, 0.7]


@pytest.mark.asyncio()
async def test_gemini_enterprise_reranker_parses_ranked_hits(monkeypatch) -> None:
    """Gemini reranking should parse strict JSON into scored chunk ids."""

    async def fake_run_with_retries(operation, **kwargs):
        del operation, kwargs
        return json.dumps(
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": json.dumps(
                                        {
                                            "hits": [
                                                {"chunk_id": "chunk-2", "score": 0.98, "reason": "direct answer"},
                                                {"chunk_id": "chunk-1", "score": 0.75, "reason": "supporting detail"},
                                            ]
                                        }
                                    )
                                }
                            ]
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("app.core.reranker.run_with_retries", fake_run_with_retries)

    reranker = GeminiEnterpriseReranker(
        api_key="test-key",
        base_url="https://example.test",
        model="gemini-2.5-flash",
        max_retries=1,
        backoff_ms=1,
        timeout_seconds=1,
    )
    result = await reranker.rerank(
        query_text="Which company supplied the vans?",
        hits=[_fused_hit("chunk-1", 0.8), _fused_hit("chunk-2", 0.7)],
        limit=2,
    )

    assert result.applied is True
    assert [hit.chunk_id for hit in result.hits] == ["chunk-2", "chunk-1"]
