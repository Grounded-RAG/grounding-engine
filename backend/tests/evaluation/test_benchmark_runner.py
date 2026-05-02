"""Tests for the benchmark runner foundation."""

from __future__ import annotations

import pytest

from tests.evaluation.benchmark_runner import load_cases_for_suites, run_benchmark


@pytest.mark.asyncio
async def test_fixture_benchmark_runs_temporal_variants() -> None:
    cases = load_cases_for_suites(["temporal_freshness"])

    results = await run_benchmark(
        cases=cases,
        variant_names=["enterprise_temporal_rag", "enterprise_temporal_no_freshness"],
        run_id="test-run",
    )

    assert results
    assert {result.variant for result in results} == {
        "enterprise_temporal_rag",
        "enterprise_temporal_no_freshness",
    }
    temporal = [result for result in results if result.variant == "enterprise_temporal_rag"]
    non_temporal = [
        result for result in results if result.variant == "enterprise_temporal_no_freshness"
    ]
    assert sum(result.metrics.temporal_accuracy for result in temporal) > sum(
        result.metrics.temporal_accuracy for result in non_temporal
    )


@pytest.mark.asyncio
async def test_fixture_benchmark_records_unknown_variant_error() -> None:
    cases = load_cases_for_suites(["temporal_freshness"])

    with pytest.raises(ValueError, match="Unknown benchmark variants"):
        await run_benchmark(cases=cases, variant_names=["missing_variant"])
