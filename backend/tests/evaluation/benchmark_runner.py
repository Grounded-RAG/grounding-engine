"""CLI and orchestration for RAG benchmark runs."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path

from tests.evaluation.benchmark_report import write_benchmark_outputs
from tests.evaluation.benchmark_schema import (
    BenchmarkCase,
    BenchmarkMetrics,
    BenchmarkPerformance,
    BenchmarkResult,
    load_benchmark_cases,
)
from tests.evaluation.benchmark_variants import BenchmarkExecutionContext, get_variants


FIXTURE_DIR = Path(__file__).with_name("fixtures")
DEFAULT_FIXTURES = [
    FIXTURE_DIR / "standard_quality_cases.json",
    FIXTURE_DIR / "temporal_cases.json",
    FIXTURE_DIR / "contradiction_cases.json",
    FIXTURE_DIR / "insufficient_evidence_cases.json",
]


async def run_benchmark(
    *,
    cases: list[BenchmarkCase],
    variant_names: list[str],
    run_id: str | None = None,
    context: BenchmarkExecutionContext | None = None,
    include_live: bool = False,
) -> list[BenchmarkResult]:
    """Run selected variants against selected cases."""

    variants = get_variants(include_live=include_live)
    unknown_variants = [name for name in variant_names if name not in variants]
    if unknown_variants:
        raise ValueError(f"Unknown benchmark variants: {', '.join(unknown_variants)}")

    actual_run_id = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    results: list[BenchmarkResult] = []
    for case in cases:
        for variant_name in variant_names:
            variant = variants[variant_name]
            try:
                result = await variant.run(
                    case=case,
                    run_id=actual_run_id,
                    context=context,
                )
            except Exception as exc:  # benchmark should record failures, not hide them
                result = BenchmarkResult(
                    run_id=actual_run_id,
                    variant=variant_name,
                    query_id=case.id,
                    query=case.query,
                    answer="",
                    metrics=BenchmarkMetrics(),
                    performance=BenchmarkPerformance(),
                    query_type=case.query_type,
                    difficulty=case.difficulty,
                    domain=case.domain,
                    suite=case.suite,
                    error=str(exc),
                )
            results.append(result)
    return results


def load_cases_for_suites(suites: list[str], fixtures: list[Path] | None = None) -> list[BenchmarkCase]:
    """Load benchmark fixtures and filter by suite name."""

    cases = load_benchmark_cases(fixtures or DEFAULT_FIXTURES)
    if not suites:
        return cases
    requested = set(suites)
    return [case for case in cases if case.suite in requested]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RAG benchmark variants.")
    parser.add_argument(
        "--suites",
        default="",
        help="Comma-separated suite names. Empty means all default fixtures.",
    )
    parser.add_argument(
        "--variants",
        default="naive_dense_only,standard_hybrid,standard_no_rerank",
        help="Comma-separated benchmark variant names.",
    )
    parser.add_argument(
        "--output",
        default="reports/benchmark",
        help="Output directory for JSONL, JSON summary, and Markdown report.",
    )
    parser.add_argument(
        "--beir-dataset",
        default="",
        help="Path to a BEIR dataset directory (corpus.jsonl + queries.jsonl + qrels/dev.tsv). "
             "When provided, cases are loaded from the dataset instead of fixture files.",
    )
    parser.add_argument(
        "--beir-limit",
        type=int,
        default=None,
        help="Limit the number of BEIR queries to run (useful for smoke runs).",
    )
    return parser.parse_args()


def load_cases_for_beir(dataset_path: Path, limit: int | None = None) -> list[BenchmarkCase]:
    """Load benchmark cases from a BEIR-formatted dataset directory."""
    from tests.evaluation.datasets.beir_loader import BEIRLoader

    loader = BEIRLoader(root=dataset_path).load()
    cases = loader.to_benchmark_cases(limit=limit)
    print(f"Loaded {len(cases)} BEIR cases from {dataset_path}")
    return cases


async def main() -> None:
    args = parse_args()
    variants = [item.strip() for item in args.variants.split(",") if item.strip()]

    if args.beir_dataset:
        cases = load_cases_for_beir(Path(args.beir_dataset), limit=args.beir_limit)
    else:
        suites = [item.strip() for item in args.suites.split(",") if item.strip()]
        cases = load_cases_for_suites(suites)

    results = await run_benchmark(cases=cases, variant_names=variants)
    write_benchmark_outputs(results, Path(args.output))


if __name__ == "__main__":
    asyncio.run(main())
