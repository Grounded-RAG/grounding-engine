"""Report generation for benchmark results."""

from __future__ import annotations

import json
from collections import defaultdict
from math import ceil
from pathlib import Path
from statistics import mean

from tests.evaluation.benchmark_schema import BenchmarkResult


def write_benchmark_outputs(results: list[BenchmarkResult], output_dir: Path) -> None:
    """Write JSONL, JSON summary, and Markdown benchmark reports."""

    output_dir.mkdir(parents=True, exist_ok=True)
    write_results_jsonl(results, output_dir / "benchmark_results.jsonl")
    summary = build_summary(results)
    (output_dir / "benchmark_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "benchmark_report.md").write_text(
        render_markdown_report(summary, results),
        encoding="utf-8",
    )
    write_queries_csv(results, output_dir / "benchmark_queries.csv")


def write_results_jsonl(results: list[BenchmarkResult], path: Path) -> None:
    """Write one canonical benchmark result per line."""

    lines = [json.dumps(result.to_dict(), sort_keys=True) for result in results]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def build_summary(results: list[BenchmarkResult]) -> dict[str, object]:
    """Aggregate benchmark results by variant and query type."""

    by_variant: dict[str, list[BenchmarkResult]] = defaultdict(list)
    by_query_type: dict[str, list[BenchmarkResult]] = defaultdict(list)
    for result in results:
        by_variant[result.variant].append(result)
        by_query_type[result.query_type].append(result)

    return {
        "total_results": len(results),
        "variants": {
            variant: _summarize_results(items)
            for variant, items in sorted(by_variant.items())
        },
        "query_types": {
            query_type: _summarize_results(items)
            for query_type, items in sorted(by_query_type.items())
        },
        "component_comparisons": _component_comparisons(by_variant),
    }


def render_markdown_report(summary: dict[str, object], results: list[BenchmarkResult] | None = None) -> str:
    """Render a compact human-readable benchmark report."""

    variants = summary.get("variants", {})
    query_types = summary.get("query_types", {})
    comparisons = summary.get("component_comparisons", [])
    lines = [
        "# Benchmark Report",
        "",
        f"Total results: {summary.get('total_results', 0)}",
        "",
        "## Variant Summary",
        "",
        "| Variant | RAGAS | Recall@5 | Faithfulness | Citation Accuracy | Temporal Accuracy | P95 Latency | Cost |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if isinstance(variants, dict):
        for variant, metrics in variants.items():
            if not isinstance(metrics, dict):
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        variant,
                        _fmt(metrics.get("ragas_score")),
                        _fmt(metrics.get("recall_at_k")),
                        _fmt(metrics.get("faithfulness")),
                        _fmt(metrics.get("citation_accuracy")),
                        _fmt(metrics.get("temporal_accuracy")),
                        f"{int(metrics.get('p95_total_latency_ms', 0))}ms",
                        _fmt(metrics.get("estimated_cost_usd"), digits=4),
                    ]
                )
                + " |"
            )

    lines.extend([
        "",
        "## Query Type Breakdown",
        "",
        "| Query Type | Best Variant | Worst Variant | Main Failure |",
        "|---|---|---|---|",
    ])
    if isinstance(query_types, dict):
        for query_type, metrics in query_types.items():
            if not isinstance(metrics, dict):
                continue
            lines.append(
                f"| {query_type} | {metrics.get('best_variant', '')} | "
                f"{metrics.get('worst_variant', '')} | {metrics.get('main_failure', '')} |"
            )

    lines.extend([
        "",
        "## Component Contribution",
        "",
        "| Component | Quality Gain | Latency Cost | Recommendation |",
        "|---|---:|---:|---|",
    ])
    if isinstance(comparisons, list):
        for comparison in comparisons:
            if not isinstance(comparison, dict):
                continue
            lines.append(
                f"| {comparison.get('component', '')} | "
                f"{_fmt(comparison.get('quality_gain'))} | "
                f"{int(comparison.get('latency_cost_ms', 0))}ms | "
                f"{comparison.get('recommendation', '')} |"
            )

    if results:
        lines.extend([
            "",
            "## Sample Queries",
            "",
            "| Query | Type | Best Variant |",
            "|---|---|---|",
        ])
        unique_queries = {r.query_id: r for r in results}.values()
        for r in list(unique_queries)[:20]:
            best = max(
                [res for res in results if res.query_id == r.query_id],
                key=lambda x: x.metrics.ragas_score,
                default=None,
            )
            best_variant = best.variant if best else "N/A"
            query_text = r.query[:60] + "..." if len(r.query) > 60 else r.query
            lines.append(f"| {query_text} | {r.query_type} | {best_variant} |")

    return "\n".join(lines) + "\n"


def _summarize_results(results: list[BenchmarkResult]) -> dict[str, object]:
    latencies = sorted(result.performance.total_latency_ms for result in results)
    by_variant: dict[str, list[BenchmarkResult]] = defaultdict(list)
    for result in results:
        by_variant[result.variant].append(result)
    variant_scores = {
        variant: mean(item.metrics.ragas_score for item in items)
        for variant, items in by_variant.items()
    }
    return {
        "count": len(results),
        "precision_at_k": _avg(result.metrics.precision_at_k for result in results),
        "recall_at_k": _avg(result.metrics.recall_at_k for result in results),
        "mrr": _avg(result.metrics.mrr for result in results),
        "ndcg_at_k": _avg(result.metrics.ndcg_at_k for result in results),
        "faithfulness": _avg(result.metrics.faithfulness for result in results),
        "answer_relevancy": _avg(result.metrics.answer_relevancy for result in results),
        "context_precision": _avg(result.metrics.context_precision for result in results),
        "context_recall": _avg(result.metrics.context_recall for result in results),
        "citation_accuracy": _avg(result.metrics.citation_accuracy for result in results),
        "temporal_accuracy": _avg(result.metrics.temporal_accuracy for result in results),
        "unsupported_claim_rate": _avg(result.metrics.unsupported_claim_rate for result in results),
        "ragas_score": _avg(result.metrics.ragas_score for result in results),
        "ares_score": _avg(result.metrics.ares_score for result in results),
        "p95_total_latency_ms": _percentile(latencies, 0.95),
        "estimated_cost_usd": _avg(result.performance.estimated_cost_usd for result in results),
        "best_variant": max(variant_scores, key=variant_scores.get) if variant_scores else "",
        "worst_variant": min(variant_scores, key=variant_scores.get) if variant_scores else "",
        "main_failure": _main_failure(results),
    }


def _component_comparisons(
    by_variant: dict[str, list[BenchmarkResult]],
) -> list[dict[str, object]]:
    comparisons = [
        ("Query planning", "standard_hybrid", "standard_no_query_plan"),
        ("Reranking", "standard_hybrid", "standard_no_rerank"),
        ("Evidence packaging", "standard_hybrid", "standard_no_evidence_packaging"),
        ("Temporal scoring", "enterprise_temporal_rag", "enterprise_temporal_no_freshness"),
    ]
    rows: list[dict[str, object]] = []
    for component, full_variant, ablated_variant in comparisons:
        full = by_variant.get(full_variant, [])
        ablated = by_variant.get(ablated_variant, [])
        if not full or not ablated:
            continue
        quality_gain = _avg(result.metrics.ragas_score for result in full) - _avg(
            result.metrics.ragas_score for result in ablated
        )
        latency_cost = _avg(result.performance.total_latency_ms for result in full) - _avg(
            result.performance.total_latency_ms for result in ablated
        )
        recommendation = "keep" if quality_gain >= 0 else "review"
        rows.append(
            {
                "component": component,
                "quality_gain": quality_gain,
                "latency_cost_ms": latency_cost,
                "recommendation": recommendation,
            }
        )
    return rows


def _avg(values) -> float:
    items = list(values)
    return mean(items) if items else 0.0


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    index = min(max(ceil(len(values) * percentile) - 1, 0), len(values) - 1)
    return values[index]


def _main_failure(results: list[BenchmarkResult]) -> str:
    if _avg(result.metrics.recall_at_k for result in results) < 0.8:
        return "low_recall"
    if _avg(result.metrics.faithfulness for result in results) < 0.85:
        return "low_faithfulness"
    if _avg(result.metrics.citation_accuracy for result in results) < 0.9:
        return "weak_citations"
    return "none"


def _fmt(value, *, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "0.000"


def write_queries_csv(results: list[BenchmarkResult], path: Path) -> None:
    """Write all queries to a CSV file for analysis."""
    import csv

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["query_id", "variant", "query", "query_type", "ragas_score", "recall_at_k", "faithfulness", "answer"])
        for r in results:
            writer.writerow([
                r.query_id,
                r.variant,
                r.query[:500],  # truncate for CSV
                r.query_type,
                _fmt(r.metrics.ragas_score),
                _fmt(r.metrics.recall_at_k),
                _fmt(r.metrics.faithfulness),
                r.answer[:200] if r.answer else "",
            ])
