"""Compatibility wrapper for generating benchmark comparison reports.

The previous implementation produced synthetic Standard RAG results. This module
now delegates to the shared benchmark runner so comparison reports use canonical
benchmark outputs and can call live variants when live context is provided.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from tests.evaluation.benchmark_report import build_summary
from tests.evaluation.benchmark_runner import run_benchmark
from tests.evaluation.benchmark_schema import BenchmarkCase, BenchmarkResult
from tests.evaluation.benchmark_variants import BenchmarkExecutionContext


@dataclass
class RAGComparisonReport:
    """Full comparison report between RAG systems."""

    report_date: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    variants: list[str] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    query_results: list[dict[str, Any]] = field(default_factory=list)
    failure_cases: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


async def generate_comparison_report(
    test_queries: list[dict[str, Any]],
    tenant_id: str | None = None,
    namespace_id: str | None = None,
    session: Any = None,
    *,
    variants: list[str] | None = None,
    context: BenchmarkExecutionContext | None = None,
) -> RAGComparisonReport:
    """Generate a comparison report without synthetic Standard output.

    By default this uses deterministic fixture variants. To run the real live
    Standard path, pass a `BenchmarkExecutionContext` with `session`,
    `tenant_context`, and `namespace_id`, then include `standard_hybrid_live` in
    `variants`.
    """

    selected_variants = variants or ["naive_dense_only", "standard_hybrid"]
    cases = [
        BenchmarkCase.from_dict(payload, default_suite="legacy")
        for payload in test_queries
    ]
    include_live = any(name.endswith("_live") for name in selected_variants)
    results = await run_benchmark(
        cases=cases,
        variant_names=selected_variants,
        context=context,
        include_live=include_live,
    )
    summary = build_summary(results)
    return RAGComparisonReport(
        variants=selected_variants,
        summary=summary,
        query_results=[result.to_dict() for result in results],
        failure_cases=_failure_cases(results),
        recommendations=_recommendations(summary),
    )


def _failure_cases(results: list[BenchmarkResult]) -> list[dict[str, Any]]:
    failures = []
    for result in results:
        if result.error or result.metrics.ragas_score < 0.5:
            failures.append(
                {
                    "query_id": result.query_id,
                    "query": result.query,
                    "variant": result.variant,
                    "ragas_score": result.metrics.ragas_score,
                    "error": result.error,
                }
            )
    return failures


def _recommendations(summary: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    variants = summary.get("variants", {})
    if not isinstance(variants, dict):
        return ["Benchmark summary is unavailable."]
    for variant, metrics in variants.items():
        if not isinstance(metrics, dict):
            continue
        if float(metrics.get("recall_at_k", 0.0)) < 0.8:
            recommendations.append(f"Improve retrieval recall for {variant}.")
        if float(metrics.get("faithfulness", 0.0)) < 0.85:
            recommendations.append(f"Strengthen answer grounding for {variant}.")
        if float(metrics.get("citation_accuracy", 0.0)) < 0.9:
            recommendations.append(f"Improve citation selection for {variant}.")
    return recommendations or ["System performing well - continue monitoring."]
