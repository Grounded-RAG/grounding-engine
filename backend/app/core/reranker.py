"""Enterprise reranker interfaces and disabled-safe backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.config import Settings, get_settings
from app.models import ExecutionTier
from app.pipeline.contracts import FusedRetrievedChunk


@dataclass(frozen=True)
class RerankerScoredHit:
    """One reranked hit with a stable score and optional debug payload."""

    chunk_id: str
    score: float
    rank: int
    debug: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class RerankerResult:
    """Result returned by one reranker invocation."""

    backend_name: str
    applied: bool
    hits: list[RerankerScoredHit]
    debug: dict[str, object] = field(default_factory=dict)


class RetrievalReranker(Protocol):
    """Contract for enterprise rerankers over fused retrieval candidates."""

    backend_name: str

    async def rerank(
        self,
        *,
        query_text: str,
        hits: list[FusedRetrievedChunk],
        limit: int,
    ) -> RerankerResult:
        """Return one ranked view of the provided candidates."""


@dataclass(frozen=True)
class DisabledReranker:
    """Pass-through reranker used when Enterprise reranking is disabled."""

    backend_name: str = "disabled"
    reason: str = "enterprise_reranker_disabled"

    async def rerank(
        self,
        *,
        query_text: str,
        hits: list[FusedRetrievedChunk],
        limit: int,
    ) -> RerankerResult:
        del query_text
        ordered_hits = [
            RerankerScoredHit(
                chunk_id=hit.chunk_id,
                score=hit.fused_score,
                rank=index,
                debug={"reason": self.reason},
            )
            for index, hit in enumerate(hits[:limit], start=1)
        ]
        return RerankerResult(
            backend_name=self.backend_name,
            applied=False,
            hits=ordered_hits,
            debug={"reason": self.reason},
        )


@dataclass(frozen=True)
class StubEnterpriseReranker:
    """Stable no-op backend used to exercise the Enterprise reranker path."""

    backend_name: str = "stub"

    async def rerank(
        self,
        *,
        query_text: str,
        hits: list[FusedRetrievedChunk],
        limit: int,
    ) -> RerankerResult:
        del query_text
        scored_hits = [
            RerankerScoredHit(
                chunk_id=hit.chunk_id,
                score=hit.fused_score,
                rank=index,
                debug={"strategy": "pass_through"},
            )
            for index, hit in enumerate(hits[:limit], start=1)
        ]
        return RerankerResult(
            backend_name=self.backend_name,
            applied=True,
            hits=scored_hits,
            debug={"strategy": "pass_through"},
        )


def resolve_retrieval_reranker(
    *,
    execution_tier: ExecutionTier,
    settings: Settings | None = None,
) -> RetrievalReranker:
    """Resolve one reranker backend for the active execution tier."""

    resolved_settings = settings or get_settings()

    if execution_tier is not ExecutionTier.ENTERPRISE:
        return DisabledReranker(reason="non_enterprise_tier")
    if not resolved_settings.enterprise_enabled:
        return DisabledReranker(reason="enterprise_tier_disabled")
    if not resolved_settings.enterprise_reranker_enabled:
        return DisabledReranker(reason="enterprise_reranker_flag_disabled")
    if resolved_settings.enterprise_reranker_backend == "stub":
        return StubEnterpriseReranker()
    return DisabledReranker(reason="enterprise_reranker_backend_disabled")
