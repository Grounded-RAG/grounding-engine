"""Shared benchmark contracts for RAG performance and output evaluation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BenchmarkCase:
    """One benchmark input with ground truth and optional replay data."""

    id: str
    query: str
    query_type: str
    difficulty: str
    expected_answer: str | None = None
    ground_truth_chunk_ids: list[str] = field(default_factory=list)
    ground_truth_statements: list[str] = field(default_factory=list)
    domain: str = "unknown"
    suite: str = "default"
    expected_behavior: str | None = None
    stale_chunk_ids: list[str] = field(default_factory=list)
    candidate_chunks: list[dict[str, Any]] = field(default_factory=list)
    variant_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, default_suite: str) -> "BenchmarkCase":
        return cls(
            id=str(payload["id"]),
            query=str(payload["query"]),
            query_type=str(payload.get("query_type", "unknown")),
            difficulty=str(payload.get("difficulty", "unknown")),
            expected_answer=(
                str(payload["expected_answer"])
                if payload.get("expected_answer") is not None
                else None
            ),
            ground_truth_chunk_ids=[str(value) for value in payload.get("ground_truth_chunk_ids", [])],
            ground_truth_statements=[str(value) for value in payload.get("ground_truth_statements", [])],
            domain=str(payload.get("domain", "unknown")),
            suite=str(payload.get("suite", default_suite)),
            expected_behavior=(
                str(payload["expected_behavior"])
                if payload.get("expected_behavior") is not None
                else None
            ),
            stale_chunk_ids=[str(value) for value in payload.get("stale_chunk_ids", [])],
            candidate_chunks=list(payload.get("candidate_chunks", [])),
            variant_outputs=dict(payload.get("variant_outputs", {})),
        )


@dataclass
class BenchmarkMetrics:
    """Quality metrics calculated for one benchmark result."""

    precision_at_k: float = 0.0
    recall_at_k: float = 0.0
    mrr: float = 0.0
    ndcg_at_k: float = 0.0
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0
    citation_accuracy: float = 0.0
    temporal_accuracy: float = 0.0
    stale_evidence_rate: float = 0.0
    abstention_correctness: float = 0.0
    unsupported_claim_rate: float = 0.0
    ragas_score: float = 0.0
    ares_score: float = 0.0


@dataclass
class BenchmarkPerformance:
    """Latency and cost metrics for one benchmark result."""

    retrieval_ms: int = 0
    evidence_packaging_ms: int = 0
    answering_ms: int = 0
    verification_ms: int = 0
    trace_persistence_ms: int = 0
    total_latency_ms: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass
class BenchmarkBehavior:
    """Behavioral signals that should be easy to audit."""

    degraded: bool = False
    degraded_reasons: list[str] = field(default_factory=list)
    unsupported_claims: list[str] = field(default_factory=list)
    source_policy_violations: list[str] = field(default_factory=list)


@dataclass
class BenchmarkResult:
    """Canonical benchmark output for any variant."""

    run_id: str
    variant: str
    query_id: str
    query: str
    answer: str
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    selected_evidence_ids: list[str] = field(default_factory=list)
    retrieved_chunks: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    metrics: BenchmarkMetrics = field(default_factory=BenchmarkMetrics)
    performance: BenchmarkPerformance = field(default_factory=BenchmarkPerformance)
    behavior: BenchmarkBehavior = field(default_factory=BenchmarkBehavior)
    query_type: str = "unknown"
    difficulty: str = "unknown"
    domain: str = "unknown"
    suite: str = "default"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_benchmark_cases(paths: list[Path]) -> list[BenchmarkCase]:
    """Load benchmark cases from one or more JSON fixture files.

    Handles two formats:
    1. Canonical BenchmarkCase format (list of dicts with 'id', 'query', etc.)
    2. Legacy standard_quality format (list of dicts with 'name', 'evidence', 'query')
    """

    import json

    cases: list[BenchmarkCase] = []
    for path in paths:
        default_suite = path.stem.replace("_cases", "")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"Benchmark fixture must contain a list: {path}")
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            if "evidence" in entry:
                cases.append(_from_legacy_entry(entry, default_suite))
            else:
                cases.append(BenchmarkCase.from_dict(entry, default_suite=default_suite))
    return cases


def _from_legacy_entry(entry: dict[str, Any], default_suite: str) -> BenchmarkCase:
    evidence: list[dict[str, Any]] = entry.get("evidence", [])
    return BenchmarkCase(
        id=str(entry["name"]),
        query=str(entry["query"]),
        query_type="grounded",
        difficulty="unknown",
        expected_answer=None,
        ground_truth_chunk_ids=[
            str(e["chunk_id"]) for e in evidence if e.get("chunk_id")
        ],
        ground_truth_statements=[],
        domain="mixed",
        suite="standard_quality",
        expected_behavior=None,
        stale_chunk_ids=[],
        candidate_chunks=[
            {
                "chunk_id": str(e.get("chunk_id", "")),
                "citation_id": str(e.get("citation_id", "")),
                "text": str(e.get("text", "")),
                "score": float(e.get("score", 0.0)),
            }
            for e in evidence
        ],
        variant_outputs={},
    )
