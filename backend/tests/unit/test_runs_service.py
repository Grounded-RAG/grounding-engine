"""Unit tests for run-history projection helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, UTC

from app.models import ExecutionTier, QueryTrace, UserFacingMode
from app.services.runs import _build_run_response


def _trace(*, run_status: str | None = None) -> QueryTrace:
    trace = QueryTrace(
        trace_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        namespace_id=uuid.uuid4(),
        agent_id=None,
        conversation_id=None,
        selected_mode=UserFacingMode.VERIFIED,
        requested_tier=ExecutionTier.CRITICAL,
        router_recommendation=ExecutionTier.CRITICAL,
        effective_tier=ExecutionTier.CRITICAL,
        routing_reason="critical_requested_enabled",
        query_redacted="Verify the policy",
        query_ciphertext=None,
        retrieved_chunk_ids=[],
        selected_evidence_ids=[],
        generator_provider="async-verified-run-v1",
        verifier_result={
            "status": "degraded",
            **({"run_status": run_status} if run_status is not None else {}),
        },
        final_answer_redacted="Verified request queued. Poll the run endpoint for the completed result.",
        citations=[],
        overall_confidence=0.0,
        degraded_reasons=["RUN_QUEUED"],
        stage_latencies_ms={"retrieval_ms": 0},
        total_latency_ms=0,
        token_usage={"total_tokens": 0},
        created_at=datetime.now(UTC),
    )
    return trace


def test_build_run_response_defaults_to_completed_when_run_status_missing() -> None:
    response = _build_run_response(_trace(run_status=None))

    assert response.status == "completed"
    assert response.selected_mode is UserFacingMode.VERIFIED
    assert response.requested_tier is ExecutionTier.CRITICAL


def test_build_run_response_projects_async_run_status_values() -> None:
    assert _build_run_response(_trace(run_status="queued")).status == "queued"
    assert _build_run_response(_trace(run_status="running")).status == "running"
    assert _build_run_response(_trace(run_status="failed")).status == "failed"
    assert _build_run_response(_trace(run_status="completed")).status == "completed"
