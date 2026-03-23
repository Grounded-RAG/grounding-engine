"""Run-history services over persisted query traces."""

from __future__ import annotations

import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import QueryTrace, UserFacingMode
from app.schemas.query import CitationResponse
from app.schemas.runs import RunResponse


class RunServiceError(RuntimeError):
    """Raised when a run-history operation cannot be completed."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _verification_status_for_trace(trace: QueryTrace) -> str:
    """Derive a stable verification status from persisted trace metadata."""

    status_value = trace.verifier_result.get("status")
    if status_value in {"passed", "degraded"}:
        return status_value
    if trace.degraded_reasons:
        return "degraded"
    return "passed"


def _selected_mode_for_trace(trace: QueryTrace) -> UserFacingMode | None:
    """Map the persisted trace mode into the product-facing run contract."""

    return trace.selected_mode


def _build_run_response(trace: QueryTrace) -> RunResponse:
    """Project one persisted query trace into the product-facing run contract."""

    return RunResponse(
        run_id=trace.trace_id,
        dataset_id=trace.namespace_id,
        agent_id=trace.agent_id,
        conversation_id=trace.conversation_id,
        requested_tier=trace.requested_tier,
        router_recommendation=trace.router_recommendation,
        effective_tier=trace.effective_tier,
        routing_reason=trace.routing_reason,
        query=trace.query_redacted,
        answer=trace.final_answer_redacted,
        citations=[
            CitationResponse.model_validate(citation)
            for citation in trace.citations
        ],
        confidence_score=trace.overall_confidence,
        verification_status=_verification_status_for_trace(trace),
        degraded_reasons=list(trace.degraded_reasons),
        generator_provider=trace.generator_provider,
        retrieved_chunk_ids=list(trace.retrieved_chunk_ids),
        selected_evidence_ids=list(trace.selected_evidence_ids),
        total_latency_ms=trace.total_latency_ms,
        created_at=trace.created_at,
        selected_mode=_selected_mode_for_trace(trace),
    )


async def list_runs_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    dataset_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[RunResponse]:
    """List recent runs for one tenant, optionally filtered by dataset."""

    statement = select(QueryTrace).where(QueryTrace.tenant_id == tenant_id)
    if dataset_id is not None:
        statement = statement.where(QueryTrace.namespace_id == dataset_id)
    statement = statement.order_by(
        QueryTrace.created_at.desc(),
        QueryTrace.trace_id.desc(),
    ).limit(limit)

    result = await session.execute(statement)
    traces = list(result.scalars().all())
    return [_build_run_response(trace) for trace in traces]


async def get_run_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    run_id: uuid.UUID,
) -> RunResponse:
    """Return one persisted run only if it belongs to the authenticated tenant."""

    statement = select(QueryTrace).where(
        QueryTrace.tenant_id == tenant_id,
        QueryTrace.trace_id == run_id,
    )
    result = await session.execute(statement)
    trace = result.scalar_one_or_none()
    if trace is None:
        raise RunServiceError(
            "Run not found for tenant.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return _build_run_response(trace)
