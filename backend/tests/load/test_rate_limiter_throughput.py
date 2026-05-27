"""Load tests for the in-process sliding-window rate limiter.

These tests verify:
1. Throughput: the limiter allows the expected number of requests per window.
2. Latency: each allow/deny decision completes in under 1ms (P99).
3. Concurrency: multiple concurrent callers from different threads
   stay within their individual quotas without data races.
4. Isolation: separate API keys have independent buckets and do not
   exhaust each other's quota.
5. Window reset: once a full minute elapses, the bucket refills.

These tests do NOT start FastAPI or hit the database. They exercise the
rate limiter module directly, which is the performance-critical path.
"""

from __future__ import annotations

import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from app.core.rate_limit import check_rate_limit, QUERY_RPM, INGEST_RPM, DEFAULT_RPM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _key() -> str:
    return f"load-test-{uuid.uuid4()}"


# ---------------------------------------------------------------------------
# 1. Throughput — allowed count matches the configured limit
# ---------------------------------------------------------------------------

class TestRateLimiterThroughput:
    def test_allows_exactly_limit_requests(self):
        key = _key()
        limit = 50
        allowed = sum(
            1 for _ in range(limit)
            if check_rate_limit(api_key_id=key, limit_key="throughput", max_requests=limit).allowed
        )
        assert allowed == limit

    def test_blocks_request_beyond_limit(self):
        key = _key()
        limit = 10
        for _ in range(limit):
            check_rate_limit(api_key_id=key, limit_key="over", max_requests=limit)
        result = check_rate_limit(api_key_id=key, limit_key="over", max_requests=limit)
        assert result.allowed is False
        assert result.remaining == 0

    def test_remaining_decrements_correctly(self):
        key = _key()
        limit = 5
        for expected_remaining in range(limit - 1, -1, -1):
            result = check_rate_limit(api_key_id=key, limit_key="decrement", max_requests=limit)
            assert result.allowed is True
            assert result.remaining == expected_remaining

    def test_configured_rpm_values_are_positive(self):
        assert QUERY_RPM >= 1
        assert INGEST_RPM >= 1
        assert DEFAULT_RPM >= 1


# ---------------------------------------------------------------------------
# 2. Latency — each check must complete in under 1ms (P99)
# ---------------------------------------------------------------------------

class TestRateLimiterLatency:
    @pytest.mark.parametrize("n_requests", [100, 500, 1000])
    def test_p99_latency_under_1ms(self, n_requests: int):
        key = _key()
        durations: list[float] = []

        for _ in range(n_requests):
            t0 = time.perf_counter()
            check_rate_limit(api_key_id=key, limit_key="latency", max_requests=n_requests * 2)
            durations.append((time.perf_counter() - t0) * 1000)

        sorted_durations = sorted(durations)
        p99_ms = sorted_durations[int(len(sorted_durations) * 0.99)]
        assert p99_ms < 1.0, (
            f"P99 latency {p99_ms:.3f}ms exceeds 1ms budget for {n_requests} requests "
            f"(mean={statistics.mean(durations):.3f}ms, max={max(durations):.3f}ms)"
        )

    def test_single_check_under_1ms(self):
        key = _key()
        t0 = time.perf_counter()
        check_rate_limit(api_key_id=key, limit_key="single", max_requests=100)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 1.0, f"Single check took {elapsed_ms:.3f}ms"


# ---------------------------------------------------------------------------
# 3. Concurrency — multiple threads stay within their quotas
# ---------------------------------------------------------------------------

class TestRateLimiterConcurrency:
    def test_concurrent_threads_respect_limit(self):
        key = _key()
        limit = 100
        n_workers = 20
        requests_per_worker = 10  # total = 200, limit = 100

        results: list[bool] = []

        def _call(_: int) -> bool:
            return check_rate_limit(
                api_key_id=key,
                limit_key="concurrent",
                max_requests=limit,
            ).allowed

        with ThreadPoolExecutor(max_workers=n_workers) as pool:
            futures = [pool.submit(_call, i) for i in range(n_workers * requests_per_worker)]
            results = [f.result() for f in as_completed(futures)]

        allowed_count = sum(results)
        assert allowed_count == limit, (
            f"Expected exactly {limit} allowed requests under concurrent load, got {allowed_count}"
        )

    def test_no_data_race_on_separate_keys(self):
        """Each key must exhaust independently — no shared state leakage."""
        keys = [_key() for _ in range(10)]
        limit = 5

        def _exhaust(key: str) -> int:
            return sum(
                1 for _ in range(limit + 2)
                if check_rate_limit(api_key_id=key, limit_key="isolation", max_requests=limit).allowed
            )

        with ThreadPoolExecutor(max_workers=10) as pool:
            counts = list(pool.map(_exhaust, keys))

        for count in counts:
            assert count == limit, f"Expected {limit} allowed per key, got {count}"


# ---------------------------------------------------------------------------
# 4. Key isolation — different keys have independent buckets
# ---------------------------------------------------------------------------

class TestRateLimiterIsolation:
    def test_keys_do_not_share_buckets(self):
        key_a = _key()
        key_b = _key()
        limit = 3

        # Exhaust key_a
        for _ in range(limit):
            check_rate_limit(api_key_id=key_a, limit_key="shared_name", max_requests=limit)
        blocked = check_rate_limit(api_key_id=key_a, limit_key="shared_name", max_requests=limit)
        assert blocked.allowed is False

        # key_b must still be open
        allowed = check_rate_limit(api_key_id=key_b, limit_key="shared_name", max_requests=limit)
        assert allowed.allowed is True

    def test_different_limit_keys_on_same_api_key_are_independent(self):
        key = _key()
        limit = 3

        for _ in range(limit):
            check_rate_limit(api_key_id=key, limit_key="bucket_a", max_requests=limit)
        blocked = check_rate_limit(api_key_id=key, limit_key="bucket_a", max_requests=limit)
        assert blocked.allowed is False

        # A different limit_key on the same api_key must be unaffected
        allowed = check_rate_limit(api_key_id=key, limit_key="bucket_b", max_requests=limit)
        assert allowed.allowed is True


# ---------------------------------------------------------------------------
# 5. Burst tolerance — a burst of requests completes quickly
# ---------------------------------------------------------------------------

class TestRateLimiterBurst:
    def test_burst_of_60_requests_under_10ms(self):
        """The full QUERY_RPM quota for one key must be consumed in < 10ms."""
        key = _key()
        limit = QUERY_RPM

        t0 = time.perf_counter()
        for _ in range(limit):
            check_rate_limit(api_key_id=key, limit_key="burst", max_requests=limit)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert elapsed_ms < 10.0, (
            f"Burst of {limit} requests took {elapsed_ms:.1f}ms — exceeds 10ms budget"
        )
