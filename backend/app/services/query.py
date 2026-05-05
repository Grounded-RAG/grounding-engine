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
from app.config import get_settings
from app.core.llm_client import GroundedGenerationError
from app.core.query_analysis import (
    ConversationContext,
    build_conversation_context,
    build_query_plan,
    refine_query_plan_for_execution_tier,
    query_plan_metadata,
    QueryPlan,
)
from app.core.telemetry import bind_execution_context
from app.models import ExecutionTier, FreshnessProfile, MessageRole, Namespace, QueryTrace, UserFacingMode
from app.schemas.query import GroundedAnswerResponse, QueryRequest
from app.services.messages import MessageServiceError, list_conversation_messages
from app.services.evidence import package_evidence
from app.services.generation import generate_answer_from_evidence
from app.services.response_shaping import (
    ResponseShapingError,
    shape_degraded_response,
    shape_grounded_response,
)
from app.services.retrieval import RetrievalBundle, RetrievalError, retrieve_hybrid_candidates
from app.services.verification import verify_critical_response


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
    "how are u",
    "how r u",
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

_GREETING_PREFIXES = ("hi", "hello", "hey", "hiya", "yo")

_TIER_RANK: dict[ExecutionTier, int] = {
    ExecutionTier.STANDARD: 1,
    ExecutionTier.ENTERPRISE: 2,
    ExecutionTier.CRITICAL: 3,
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


def _evidence_debug_summary(*, selected_evidence_ids: list[str], evidence_package) -> dict[str, object]:
    """Build a compact evidence summary for persisted trace inspection."""

    return {
        "selected_evidence_ids": list(selected_evidence_ids),
        "item_count": len(evidence_package.items),
        "document_count": len({item.document_id for item in evidence_package.items}),
        "section_slugs": sorted(
            {
                item.section_slug
                for item in evidence_package.items
                if item.section_slug
            }
        )[:5],
    }


def _build_verifier_trace_result(
    *,
    response: GroundedAnswerResponse,
    query_plan: QueryPlan | None,
    routing_decision: ExecutionRoutingDecision,
    retrieval_bundle: RetrievalBundle,
    evidence_debug: dict[str, object] | None,
    enterprise_trace_metadata_enabled: bool,
    enterprise_enabled: bool,
) -> dict[str, object]:
    """Build persisted verification metadata for current and future Critical flows."""

    degraded_reasons = list(response.degraded_reasons)
    verification_outcome = "accepted" if response.verification_status == "passed" else "degraded"

    return {
        "status": response.verification_status,
        "verification_applied": routing_decision.requested_tier is ExecutionTier.CRITICAL,
        "verification_outcome": verification_outcome,
        "verification_reason": degraded_reasons[0] if degraded_reasons else None,
        "verification_mode": (
            "critical_requested_fallback_standard"
            if routing_decision.requested_tier is ExecutionTier.CRITICAL
            else "standard_response_shaping"
        ),
        "bounded_correction_attempted": False,
        "contradiction_detected": False,
        "unsupported_claims_detected": bool(degraded_reasons),
        "critical_verifier": (
            evidence_debug.get("critical_verifier")
            if isinstance(evidence_debug, dict)
            else None
        ),
        "query_plan": query_plan_metadata(query_plan) if query_plan is not None else None,
        "execution_routing": (
            routing_decision.trace_metadata(enterprise_enabled=enterprise_enabled)
            if enterprise_trace_metadata_enabled
            else None
        ),
        "retrieval_debug": retrieval_bundle.debug if enterprise_trace_metadata_enabled else None,
        "evidence_debug": evidence_debug if enterprise_trace_metadata_enabled else None,
    }


def _supports_execution_tier(*, available_tier: ExecutionTier, required_tier: ExecutionTier) -> bool:
    """Return whether the resolved execution tier satisfies one namespace requirement."""

    return _TIER_RANK[available_tier] >= _TIER_RANK[required_tier]


def _is_smalltalk_query(query_text: str) -> bool:
    """Detect greetings and conversational filler that should clarify scope."""

    normalized = re.sub(r"[^a-z0-9\s]+", " ", query_text.strip().casefold())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return False
    if re.fullmatch(r"(?:h+i+|h+e+y+|hello+|hiya+|yo+)", normalized):
        return True
    if normalized in _SMALLTALK_QUERIES:
        return True

    for prefix in _GREETING_PREFIXES:
        if normalized.startswith(f"{prefix} "):
            remainder = normalized[len(prefix) :].strip()
            if (
                remainder in _SMALLTALK_QUERIES
                or remainder in {"there", "there there"}
                or remainder.startswith("how are you")
                or remainder.startswith("can you help me")
                or remainder.startswith("help me")
                or remainder.startswith("what can you do")
                or remainder.startswith("who are you")
                or remainder.startswith("nice to meet you")
            ):
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


def _requested_tier_from_mode(selected_mode: UserFacingMode | None) -> ExecutionTier | None:
    """Map user-facing modes into their backing execution tiers."""

    if selected_mode is UserFacingMode.THINKING:
        return ExecutionTier.ENTERPRISE
    if selected_mode is UserFacingMode.VERIFIED:
        return ExecutionTier.CRITICAL
    return None


def _enterprise_route_reasons(query_plan: QueryPlan) -> tuple[str, ...]:
    """Return explainable triggers for minimal hard-query Enterprise routing."""

    profile = query_plan.profile
    reasons: list[str] = []

    if profile.query_kind == "comparison":
        reasons.append("comparison_query")
    if profile.query_kind == "action":
        reasons.append("action_query")
    if len(profile.attribute_terms) > 1 and profile.query_kind in {"comparison", "list", "lookup"}:
        reasons.append("multi_attribute_query")
    if profile.document_reference_rank is not None:
        reasons.append("document_reference_query")
    if query_plan.used_conversation_context and profile.query_kind in {"comparison", "entity", "open", "summary"}:
        reasons.append("follow_up_context_query")
    if len(query_plan.retrieval_queries) >= 3 and profile.query_kind in {"comparison", "action", "entity"}:
        reasons.append("multi_intent_retrieval")

    deduped_reasons: list[str] = []
    for reason in reasons:
        if reason not in deduped_reasons:
            deduped_reasons.append(reason)
    return tuple(deduped_reasons)


def _resolve_execution_routing(
    *,
    query_request: QueryRequest,
    selected_mode: UserFacingMode | None,
    query_plan: QueryPlan | None = None,
) -> ExecutionRoutingDecision:
    """Resolve which execution tier is being requested and which is currently active."""

    settings = get_settings()
    requested_from_mode = _requested_tier_from_mode(selected_mode)

    if query_request.requested_tier is not None:
        requested_tier = query_request.requested_tier
        request_source = "query_request"
    elif requested_from_mode is not None:
        requested_tier = requested_from_mode
        request_source = "selected_mode"
    elif (
        query_plan is not None
        and selected_mode in {None, UserFacingMode.AUTO}
        and settings.enterprise_enabled
        and settings.enterprise_auto_routing_enabled
        and _enterprise_route_reasons(query_plan)
    ):
        requested_tier = ExecutionTier.ENTERPRISE
        request_source = "auto_router"
    else:
        requested_tier = ExecutionTier.STANDARD
        request_source = "default"

    route_triggers = _enterprise_route_reasons(query_plan) if query_plan is not None else ()
    router_recommendation = requested_tier

    if requested_tier is ExecutionTier.ENTERPRISE:
        if settings.enterprise_enabled:
            effective_tier = ExecutionTier.ENTERPRISE
            if request_source == "auto_router":
                routing_reason = "enterprise_auto_hard_query"
            elif selected_mode is UserFacingMode.THINKING:
                routing_reason = "thinking_mode_enterprise"
            else:
                routing_reason = "enterprise_requested_enabled"
        else:
            effective_tier = ExecutionTier.STANDARD
            routing_reason = (
                "thinking_mode_fallback_standard"
                if selected_mode is UserFacingMode.THINKING
                else "enterprise_requested_fallback_standard"
            )
    elif requested_tier is ExecutionTier.CRITICAL:
        if settings.critical_enabled:
            effective_tier = ExecutionTier.CRITICAL
            routing_reason = "critical_requested_enabled"
        else:
            effective_tier = ExecutionTier.STANDARD
            routing_reason = "critical_requested_fallback_standard"
    else:
        effective_tier = ExecutionTier.STANDARD
        routing_reason = "standard_default"

    return ExecutionRoutingDecision(
        requested_tier=requested_tier,
        router_recommendation=router_recommendation,
        effective_tier=effective_tier,
        routing_reason=routing_reason,
        request_source=request_source,
        route_triggers=route_triggers,
    )


@dataclass(frozen=True)
class QueryExecutionResult:
    """Completed Standard query result including persisted trace metadata."""

    response: GroundedAnswerResponse
    trace_id: uuid.UUID


@dataclass(frozen=True)
class ExecutionRoutingDecision:
    """Resolved execution-tier decision for one query request."""

    requested_tier: ExecutionTier
    router_recommendation: ExecutionTier
    effective_tier: ExecutionTier
    routing_reason: str
    request_source: str
    route_triggers: tuple[str, ...] = ()

    def trace_metadata(self, *, enterprise_enabled: bool) -> dict[str, object]:
        """Return compact routing metadata for persisted traces and debugging."""

        return {
            "requested_tier": self.requested_tier.value,
            "router_recommendation": self.router_recommendation.value,
            "effective_tier": self.effective_tier.value,
            "routing_reason": self.routing_reason,
            "request_source": self.request_source,
            "route_triggers": list(self.route_triggers),
            "enterprise_enabled": enterprise_enabled,
        }


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
    query_plan: QueryPlan | None = None,
    evidence_debug: dict[str, object] | None = None,
    routing_decision: ExecutionRoutingDecision | None = None,
    agent_id: uuid.UUID | None = None,
    conversation_id: uuid.UUID | None = None,
    selected_mode: UserFacingMode | None = None,
) -> QueryTrace:
    """Persist one Standard query trace for later debugging and evaluation."""

    settings = get_settings()
    resolved_routing = routing_decision or ExecutionRoutingDecision(
        requested_tier=ExecutionTier.STANDARD,
        router_recommendation=ExecutionTier.STANDARD,
        effective_tier=ExecutionTier.STANDARD,
        routing_reason="standard_default",
        request_source="default",
    )

    trace = QueryTrace(
        tenant_id=tenant_context.tenant_id,
        namespace_id=query_request.namespace_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        selected_mode=selected_mode,
        requested_tier=resolved_routing.requested_tier,
        router_recommendation=resolved_routing.router_recommendation,
        effective_tier=resolved_routing.effective_tier,
        routing_reason=resolved_routing.routing_reason,
        query_redacted=query_request.query,
        query_ciphertext=None,
        retrieved_chunk_ids=[hit.chunk_id for hit in retrieval_bundle.fused_hits],
        selected_evidence_ids=[citation.chunk_id for citation in response.citations],
        generator_provider=generator_provider,
        verifier_result=_build_verifier_trace_result(
            response=response,
            query_plan=query_plan,
            routing_decision=resolved_routing,
            retrieval_bundle=retrieval_bundle,
            evidence_debug=evidence_debug,
            enterprise_trace_metadata_enabled=settings.enterprise_trace_metadata_enabled,
            enterprise_enabled=settings.enterprise_enabled,
        ),
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


async def _resolve_conversation_context(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID | None,
    current_query: str,
) -> ConversationContext | None:
    """Return a lightweight rolling conversation context for follow-up expansion."""

    if conversation_id is None:
        return None
    try:
        messages = await list_conversation_messages(
            session=session,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )
    except MessageServiceError:
        return None

    history = list(messages)
    if (
        history
        and history[-1].role is MessageRole.USER
        and history[-1].content.strip() == current_query.strip()
    ):
        history = history[:-1]
    if not history:
        return None
    recent_user_queries = [
        message.content
        for message in history
        if message.role is MessageRole.USER
    ][-4:]
    recent_assistant_messages = [
        message.content
        for message in history
        if message.role is MessageRole.ASSISTANT
    ][-2:]
    return build_conversation_context(
        recent_user_queries=recent_user_queries,
        recent_assistant_messages=recent_assistant_messages,
    )


def _apply_critical_verification(
    *,
    response: GroundedAnswerResponse,
    evidence_package,
) -> tuple[GroundedAnswerResponse, dict[str, object]]:
    """Apply the first strict verification pass for Critical responses."""

    verifier_result = verify_critical_response(
        response=response,
        evidence_package=evidence_package,
    )

    metadata = {
        "decision": verifier_result.decision,
        "reason": verifier_result.reason,
        "supported_claim_count": verifier_result.supported_claim_count,
        "partially_supported_claim_count": verifier_result.partially_supported_claim_count,
        "unsupported_claim_count": verifier_result.unsupported_claim_count,
        "claims": [
            {
                "text": claim.text,
                "status": claim.status,
                "matched_chunk_ids": list(claim.matched_chunk_ids),
                "missing_terms": list(claim.missing_terms),
            }
            for claim in verifier_result.claims
        ],
        "unsupported_claims_detected": verifier_result.unsupported_claims_detected,
        "contradiction_detected": verifier_result.contradiction_detected,
        "bounded_correction_attempted": verifier_result.bounded_correction_attempted,
    }

    if verifier_result.decision == "accept":
        return response, metadata

    degraded_reasons = list(response.degraded_reasons)
    if verifier_result.reason and verifier_result.reason not in degraded_reasons:
        degraded_reasons.append(verifier_result.reason)

    degraded_response = response.model_copy(
        update={
            "verification_status": "degraded",
            "degraded_reasons": degraded_reasons,
            "support_summary": "insufficient" if verifier_result.decision == "refuse" else "partial",
            "confidence_label": "low" if verifier_result.decision == "refuse" else response.confidence_label,
            "confidence_score": (
                0.0
                if verifier_result.decision == "refuse"
                else min(response.confidence_score, 0.49)
            ),
        }
    )
    return degraded_response, metadata


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
    started_at = time.perf_counter()
    query_plan: QueryPlan | None = None

    if _is_smalltalk_query(query_request.query):
        routing_decision = _resolve_execution_routing(
            query_request=query_request,
            selected_mode=selected_mode,
        )
    else:
        query_plan = build_query_plan(
            query_request.query,
            conversation_context=await _resolve_conversation_context(
                session=session,
                tenant_id=tenant_context.tenant_id,
                conversation_id=conversation_id,
                current_query=query_request.query,
            ),
        )
        routing_decision = _resolve_execution_routing(
            query_request=query_request,
            selected_mode=selected_mode,
            query_plan=query_plan,
        )
        query_plan = refine_query_plan_for_execution_tier(
            query_plan,
            execution_tier=routing_decision.effective_tier,
        )

    if not _supports_execution_tier(
        available_tier=routing_decision.effective_tier,
        required_tier=namespace.min_execution_tier,
    ):
        raise QueryServiceError(
            "Namespace requires a higher execution tier than the resolved query path.",
            status_code=status.HTTP_409_CONFLICT,
        )

    bind_execution_context(
        requested_tier=routing_decision.requested_tier.value,
        router_recommendation=routing_decision.router_recommendation.value,
        effective_tier=routing_decision.effective_tier.value,
        routing_reason=routing_decision.routing_reason,
        selected_mode=selected_mode.value if selected_mode is not None else None,
    )

    if query_plan is None:
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
            query_plan=None,
            evidence_debug=None,
            routing_decision=routing_decision,
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
            query_plan=query_plan,
            execution_tier=routing_decision.effective_tier,
            freshness_profile=getattr(
                namespace,
                "freshness_profile",
                FreshnessProfile.BALANCED,
            ),
        )
    except RetrievalError as exc:
        raise QueryServiceError(
            "Failed to retrieve grounded evidence for the query.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    retrieval_ms = int((time.perf_counter() - retrieval_started) * 1000)

    evidence_started = time.perf_counter()
    evidence_package = package_evidence(
        retrieval_bundle,
        query_text=query_plan.resolved_query_text,
        execution_tier=routing_decision.effective_tier,
    )
    evidence_ms = int((time.perf_counter() - evidence_started) * 1000)

    answering_started = time.perf_counter()
    if not evidence_package.items:
        response = shape_degraded_response(
            reason="NO_GROUNDED_EVIDENCE",
            answer_text="I could not find grounded evidence for this query.",
        )
        generator_provider = "degraded-handler-v1"
        critical_verifier_metadata = None
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
            if routing_decision.effective_tier is ExecutionTier.CRITICAL:
                response, critical_verifier_metadata = _apply_critical_verification(
                    response=response,
                    evidence_package=evidence_package,
                )
            else:
                critical_verifier_metadata = None
        except (GroundedGenerationError, ResponseShapingError) as exc:
            degraded_reason, answer_text = _degraded_reason_for_generation_exception(exc)
            response = shape_degraded_response(
                reason=degraded_reason,
                answer_text=answer_text,
            )
            generator_provider = "degraded-handler-v1"
            critical_verifier_metadata = None
    answering_ms = int((time.perf_counter() - answering_started) * 1000)

    stage_latencies_ms = {
        "retrieval_ms": retrieval_ms,
        "evidence_packaging_ms": evidence_ms,
        "answering_ms": answering_ms,
    }
    evidence_debug = _evidence_debug_summary(
        selected_evidence_ids=evidence_package.selected_evidence_ids,
        evidence_package=evidence_package,
    )
    if critical_verifier_metadata is not None:
        evidence_debug = {
            **evidence_debug,
            "critical_verifier": critical_verifier_metadata,
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
        query_plan=query_plan,
        evidence_debug=evidence_debug,
        routing_decision=routing_decision,
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
