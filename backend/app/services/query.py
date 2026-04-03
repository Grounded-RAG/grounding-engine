"""Standard query orchestration and trace persistence."""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext
from app.core.llm_client import GroundedGenerationError
from app.models import ExecutionTier, Namespace, QueryTrace, UserFacingMode
from app.schemas.query import GroundedAnswerResponse, QueryRequest
from app.services.evidence import package_evidence
from app.services.generation import generate_answer_from_evidence
from app.services.response_shaping import (
    ResponseShapingError,
    shape_degraded_response,
    shape_grounded_response,
)
from app.services.retrieval import RetrievalBundle, RetrievalError, retrieve_hybrid_candidates


class QueryServiceError(RuntimeError):
    """Raised when a Standard query cannot be completed."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


_SMALLTALK_QUERIES = {
    "hi",
    "hello",
    "hey",
    "hiya",
    "yo",
    "good day",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "how are you doing",
    "can you help me",
    "help me",
    "who are you",
    "what can you do",
    "nice to meet you",
    "ok",
    "okay",
    "thanks",
    "thank you",
    "thank you so much",
}


def _degraded_reason_for_generation_exception(exc: Exception) -> tuple[str, str]:
    """Map generator/shaping failures to clearer Standard degraded outcomes."""

    message = str(exc).lower()
    if "meaningful query terms" in message:
        return (
            "QUERY_REQUIRES_CLARIFICATION",
            "Please ask a more specific grounded question so I can search the attached evidence.",
        )
    if "query-aligned support" in message:
        return (
            "INSUFFICIENT_QUERY_ALIGNMENT",
            "I found related material, but not enough evidence that directly answers this question.",
        )
    return (
        "INSUFFICIENT_SUPPORT",
        "I found some related material, but not enough grounded evidence to answer confidently.",
    )


def _is_smalltalk_query(query_text: str) -> bool:
    """Detect greetings and conversational filler that should clarify scope."""

    normalized = re.sub(r"[^a-z0-9\s]+", " ", query_text.strip().casefold())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return False
    if normalized in _SMALLTALK_QUERIES:
        return True
    tokens = normalized.split()
    return len(tokens) <= 4 and all(
        token in {"hi", "hello", "hey", "hiya", "yo", "thanks", "thank", "okay", "ok"}
        for token in tokens
    )


def _smalltalk_response() -> GroundedAnswerResponse:
    """Return a friendly scoped reply for greetings and conversational filler."""

    return shape_degraded_response(
        reason="QUERY_REQUIRES_CLARIFICATION",
        answer_text=(
            "Hi. I am ready to help with the attached dataset. "
            "Ask me a question about the uploaded documents and I will answer with citations when grounded evidence is available."
        ),
    )


@dataclass(frozen=True)
class QueryExecutionResult:
    """Completed Standard query result including persisted trace metadata."""

    response: GroundedAnswerResponse
    trace_id: uuid.UUID


async def _get_namespace_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    namespace_id: uuid.UUID,
) -> Namespace:
    """Resolve a namespace only if it belongs to the authenticated tenant."""

    statement = select(Namespace).where(
        Namespace.tenant_id == tenant_id,
        Namespace.namespace_id == namespace_id,
    )
    result = await session.execute(statement)
    namespace = result.scalar_one_or_none()
    if namespace is None:
        raise QueryServiceError(
            "Namespace not found for tenant.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return namespace


async def _persist_query_trace(
    *,
    session: AsyncSession,
    tenant_context: TenantContext,
    query_request: QueryRequest,
    response: GroundedAnswerResponse,
    retrieval_bundle: RetrievalBundle,
    stage_latencies_ms: dict[str, int],
    total_latency_ms: int,
    generator_provider: str,
    agent_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
    selected_mode: UserFacingMode | None = None,
) -> QueryTrace:
    """Persist one Standard query trace for later debugging and evaluation."""

    trace = QueryTrace(
        tenant_id=tenant_context.tenant_id,
        namespace_id=query_request.namespace_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        selected_mode=selected_mode,
        requested_tier=ExecutionTier.STANDARD,
        router_recommendation=ExecutionTier.STANDARD,
        effective_tier=ExecutionTier.STANDARD,
        routing_reason="phase1_standard_query",
        query_redacted=query_request.query,
        query_ciphertext=None,
        retrieved_chunk_ids=[hit.chunk_id for hit in retrieval_bundle.fused_hits],
        selected_evidence_ids=[citation.chunk_id for citation in response.citations],
        generator_provider=generator_provider,
        verifier_result={"status": response.verification_status},
        final_answer_redacted=response.answer,
        citations=[citation.model_dump(mode="json") for citation in response.citations],
        overall_confidence=response.confidence_score,
        degraded_reasons=list(response.degraded_reasons),
        stage_latencies_ms=stage_latencies_ms,
        total_latency_ms=total_latency_ms,
        token_usage={
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    )
    session.add(trace)
    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise QueryServiceError(
            "Failed to persist query trace.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(trace)
    return trace


async def _update_query_trace_timings(
    *,
    session: AsyncSession,
    trace: QueryTrace,
    stage_latencies_ms: dict[str, int],
    total_latency_ms: int,
) -> None:
    """Persist finalized timing metadata after the initial trace write completes."""

    trace.stage_latencies_ms = stage_latencies_ms
    trace.total_latency_ms = total_latency_ms
    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise QueryServiceError(
            "Failed to finalize query trace timings.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc


async def execute_standard_query(
    *,
    session: AsyncSession,
    tenant_context: TenantContext,
    query_request: QueryRequest,
    agent_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
    selected_mode: UserFacingMode | None = None,
) -> QueryExecutionResult:
    """Run the Standard query path and persist a trace for the result."""

    namespace = await _get_namespace_for_tenant(
        session=session,
        tenant_id=tenant_context.tenant_id,
        namespace_id=query_request.namespace_id,
    )
    if namespace.min_execution_tier is not ExecutionTier.STANDARD:
        raise QueryServiceError(
            "Namespace requires a higher execution tier than Standard.",
            status_code=status.HTTP_409_CONFLICT,
        )

    started_at = time.perf_counter()

    if _is_smalltalk_query(query_request.query):
        retrieval_bundle = RetrievalBundle(sparse_hits=[], dense_hits=[], fused_hits=[])
        response = _smalltalk_response()
        stage_latencies_ms = {
            "retrieval_ms": 0,
            "evidence_packaging_ms": 0,
            "answering_ms": 0,
        }
        trace_started = time.perf_counter()
        trace = await _persist_query_trace(
            session=session,
            tenant_context=tenant_context,
            query_request=query_request,
            response=response,
            retrieval_bundle=retrieval_bundle,
            stage_latencies_ms=stage_latencies_ms,
            total_latency_ms=int((time.perf_counter() - started_at) * 1000),
            generator_provider="clarification-handler-v1",
            agent_id=agent_id,
            conversation_id=conversation_id,
            selected_mode=selected_mode,
        )
        trace_ms = int((time.perf_counter() - trace_started) * 1000)
        await _update_query_trace_timings(
            session=session,
            trace=trace,
            stage_latencies_ms={
                **stage_latencies_ms,
                "trace_persistence_ms": trace_ms,
            },
            total_latency_ms=int((time.perf_counter() - started_at) * 1000),
        )
        return QueryExecutionResult(
            response=response,
            trace_id=trace.trace_id,
        )

    retrieval_started = time.perf_counter()
    try:
        retrieval_bundle = await retrieve_hybrid_candidates(
            session=session,
            tenant_id=tenant_context.tenant_id,
            namespace_id=query_request.namespace_id,
            query_text=query_request.query,
        )
    except RetrievalError as exc:
        raise QueryServiceError(
            "Failed to retrieve grounded evidence for the query.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    retrieval_ms = int((time.perf_counter() - retrieval_started) * 1000)

    evidence_started = time.perf_counter()
    evidence_package = package_evidence(retrieval_bundle)
    evidence_ms = int((time.perf_counter() - evidence_started) * 1000)

    answering_started = time.perf_counter()
    if not evidence_package.items:
        response = shape_degraded_response(
            reason="NO_GROUNDED_EVIDENCE",
            answer_text="I could not find grounded evidence for this query.",
        )
        generator_provider = "degraded-handler-v1"
    else:
        try:
            draft = await generate_answer_from_evidence(
                query_text=query_request.query,
                evidence_package=evidence_package,
            )
            response = shape_grounded_response(
                draft=draft,
                evidence_package=evidence_package,
            )
            generator_provider = draft.generator_provider
        except (GroundedGenerationError, ResponseShapingError) as exc:
            degraded_reason, answer_text = _degraded_reason_for_generation_exception(exc)
            response = shape_degraded_response(
                reason=degraded_reason,
                answer_text=answer_text,
            )
            generator_provider = "degraded-handler-v1"
    answering_ms = int((time.perf_counter() - answering_started) * 1000)

    stage_latencies_ms = {
        "retrieval_ms": retrieval_ms,
        "evidence_packaging_ms": evidence_ms,
        "answering_ms": answering_ms,
    }

    trace_started = time.perf_counter()
    trace = await _persist_query_trace(
        session=session,
        tenant_context=tenant_context,
        query_request=query_request,
        response=response,
        retrieval_bundle=retrieval_bundle,
        stage_latencies_ms=stage_latencies_ms,
        total_latency_ms=int((time.perf_counter() - started_at) * 1000),
        generator_provider=generator_provider,
        agent_id=agent_id,
        conversation_id=conversation_id,
        selected_mode=selected_mode,
    )
    trace_ms = int((time.perf_counter() - trace_started) * 1000)

    finalized_stage_latencies_ms = {
        **stage_latencies_ms,
        "trace_persistence_ms": trace_ms,
    }
    await _update_query_trace_timings(
        session=session,
        trace=trace,
        stage_latencies_ms=finalized_stage_latencies_ms,
        total_latency_ms=int((time.perf_counter() - started_at) * 1000),
    )

    return QueryExecutionResult(
        response=response,
        trace_id=trace.trace_id,
    )
