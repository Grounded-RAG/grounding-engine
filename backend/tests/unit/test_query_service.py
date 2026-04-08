"""Unit tests for Standard query orchestration and trace persistence."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.api.deps import TenantContext
from app.models import ExecutionTier, UserFacingMode
from app.pipeline.contracts import EvidencePackage, FusedRetrievedChunk, RetrievedChunk
from app.schemas.query import QueryRequest
from app.services.generation import GenerationBackend
from app.services.query import QueryServiceError, execute_standard_query
from app.services.retrieval import RetrievalBundle


@dataclass
class FakeScalarResult:
    """Minimal scalar result wrapper for namespace lookups."""

    value: object | None

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return []


class FakeAsyncSession:
    """Minimal async session stub for query service tests."""

    def __init__(self, namespace: object | None) -> None:
        self.namespace = namespace
        self.added = []
        self.committed = False
        self.refreshed = []

    async def execute(self, statement, params=None):
        del statement, params
        return FakeScalarResult(self.namespace)

    def add(self, value) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.committed = False

    async def refresh(self, value) -> None:
        self.refreshed.append(value)


def _tenant_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid.uuid4(),
        tenant_name="tenant",
        subscription_plan="pro",  # type: ignore[arg-type]
        max_execution_tier=ExecutionTier.ENTERPRISE,
        api_key_id=uuid.uuid4(),
        api_key_label="test-key",
    )


def _retrieval_bundle(tenant_id: uuid.UUID, namespace_id: uuid.UUID) -> RetrievalBundle:
    document_id = uuid.uuid4()
    sparse_hit = RetrievedChunk(
        chunk_id="chunk-1",
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        document_id=document_id,
        chunk_index=0,
        text="Grounded supports tenant-safe uploads.",
        score=0.8,
        rank=1,
        source="sparse",
    )
    dense_hit = RetrievedChunk(
        chunk_id="chunk-1",
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        document_id=document_id,
        chunk_index=0,
        text="Grounded supports tenant-safe uploads.",
        score=0.9,
        rank=1,
        source="dense",
    )
    fused_hit = FusedRetrievedChunk(
        chunk_id="chunk-1",
        tenant_id=tenant_id,
        namespace_id=namespace_id,
        document_id=document_id,
        chunk_index=0,
        text="Grounded supports tenant-safe uploads.",
        fused_score=0.95,
        sources=("dense", "sparse"),
    )
    return RetrievalBundle(
        sparse_hits=[sparse_hit],
        dense_hits=[dense_hit],
        fused_hits=[fused_hit],
    )


@pytest.mark.asyncio()
async def test_execute_standard_query_persists_trace_for_grounded_answer(monkeypatch) -> None:
    """Standard query execution should persist a trace for grounded answers."""

    tenant_context = _tenant_context()
    namespace_id = uuid.uuid4()
    query_request = QueryRequest(namespace_id=namespace_id, query="How does grounded work?")
    namespace = type(
        "NamespaceStub",
        (),
        {"min_execution_tier": ExecutionTier.STANDARD},
    )()
    session = FakeAsyncSession(namespace=namespace)

    async def fake_retrieve_hybrid_candidates(**kwargs):
        assert kwargs["tenant_id"] == tenant_context.tenant_id
        assert kwargs["namespace_id"] == namespace_id
        return _retrieval_bundle(tenant_context.tenant_id, namespace_id)

    monkeypatch.setattr(
        "app.services.query.retrieve_hybrid_candidates",
        fake_retrieve_hybrid_candidates,
    )
    monkeypatch.setattr(
        "app.services.generation.resolve_generation_backend",
        lambda: GenerationBackend(
            provider_name="local_grounded_v1",
            implementation="local",
        ),
    )

    result = await execute_standard_query(
        session=session,
        tenant_context=tenant_context,
        query_request=query_request,
    )

    assert result.response.verification_status == "passed"
    assert result.response.confidence_label == "high"
    assert result.response.support_summary == "grounded"
    assert result.response.degraded_reasons == []
    assert session.committed is True
    assert len(session.added) == 1
    trace = session.added[0]
    assert trace.tenant_id == tenant_context.tenant_id
    assert trace.namespace_id == namespace_id
    assert trace.requested_tier is ExecutionTier.STANDARD
    assert trace.agent_id is None
    assert trace.conversation_id is None
    assert trace.selected_mode is None
    assert trace.generator_provider == "local-grounded-v1"
    assert trace.retrieved_chunk_ids == ["chunk-1"]
    assert trace.selected_evidence_ids == ["chunk-1"]
    assert trace.verifier_result["query_plan"]["query_kind"] == "open"


@pytest.mark.asyncio()
async def test_execute_standard_query_persists_agent_chat_context(monkeypatch) -> None:
    """Agent chat should persist agent, conversation, and selected mode on the trace."""

    tenant_context = _tenant_context()
    namespace_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    query_request = QueryRequest(namespace_id=namespace_id, query="How does grounded work?")
    namespace = type(
        "NamespaceStub",
        (),
        {"min_execution_tier": ExecutionTier.STANDARD},
    )()
    session = FakeAsyncSession(namespace=namespace)

    async def fake_retrieve_hybrid_candidates(**kwargs):
        del kwargs
        return _retrieval_bundle(tenant_context.tenant_id, namespace_id)

    monkeypatch.setattr(
        "app.services.query.retrieve_hybrid_candidates",
        fake_retrieve_hybrid_candidates,
    )

    await execute_standard_query(
        session=session,
        tenant_context=tenant_context,
        query_request=query_request,
        agent_id=agent_id,
        conversation_id=conversation_id,
        selected_mode=UserFacingMode.INSTANT,
    )

    trace = session.added[0]
    assert trace.agent_id == agent_id
    assert trace.conversation_id == conversation_id
    assert trace.selected_mode is UserFacingMode.INSTANT


@pytest.mark.asyncio()
async def test_execute_standard_query_degrades_when_no_evidence(monkeypatch) -> None:
    """Standard query execution should return a degraded response when nothing is found."""

    tenant_context = _tenant_context()
    namespace_id = uuid.uuid4()
    query_request = QueryRequest(namespace_id=namespace_id, query="Unknown topic")
    namespace = type(
        "NamespaceStub",
        (),
        {"min_execution_tier": ExecutionTier.STANDARD},
    )()
    session = FakeAsyncSession(namespace=namespace)

    async def fake_retrieve_hybrid_candidates(**kwargs):
        del kwargs
        return RetrievalBundle(sparse_hits=[], dense_hits=[], fused_hits=[])

    monkeypatch.setattr(
        "app.services.query.retrieve_hybrid_candidates",
        fake_retrieve_hybrid_candidates,
    )

    result = await execute_standard_query(
        session=session,
        tenant_context=tenant_context,
        query_request=query_request,
    )

    assert result.response.verification_status == "degraded"
    assert result.response.degraded_reasons == ["NO_GROUNDED_EVIDENCE"]
    assert result.response.citations == []
    assert result.response.support_summary == "insufficient"


@pytest.mark.asyncio()
async def test_execute_standard_query_requests_clarification_for_vague_query(monkeypatch) -> None:
    """Very vague chat prompts should degrade as clarification requests, not false answers."""

    tenant_context = _tenant_context()
    namespace_id = uuid.uuid4()
    query_request = QueryRequest(namespace_id=namespace_id, query="hi")
    namespace = type(
        "NamespaceStub",
        (),
        {"min_execution_tier": ExecutionTier.STANDARD},
    )()
    session = FakeAsyncSession(namespace=namespace)

    async def fail_retrieve_hybrid_candidates(**kwargs):
        del kwargs
        raise AssertionError("Small-talk clarification should bypass retrieval.")

    monkeypatch.setattr(
        "app.services.query.retrieve_hybrid_candidates",
        fail_retrieve_hybrid_candidates,
    )

    result = await execute_standard_query(
        session=session,
        tenant_context=tenant_context,
        query_request=query_request,
    )

    assert result.response.verification_status == "degraded"
    assert result.response.degraded_reasons == ["QUERY_REQUIRES_CLARIFICATION"]
    assert "Ask me a question about the uploaded documents" in result.response.answer


@pytest.mark.asyncio()
async def test_execute_standard_query_requests_clarification_for_combined_greeting(monkeypatch) -> None:
    """Combined greetings like 'hi how are you' should also bypass retrieval."""

    tenant_context = _tenant_context()
    namespace_id = uuid.uuid4()
    query_request = QueryRequest(namespace_id=namespace_id, query="hi how are you")
    namespace = type(
        "NamespaceStub",
        (),
        {"min_execution_tier": ExecutionTier.STANDARD},
    )()
    session = FakeAsyncSession(namespace=namespace)

    async def fail_retrieve_hybrid_candidates(**kwargs):
        del kwargs
        raise AssertionError("Combined greeting clarification should bypass retrieval.")

    monkeypatch.setattr(
        "app.services.query.retrieve_hybrid_candidates",
        fail_retrieve_hybrid_candidates,
    )

    result = await execute_standard_query(
        session=session,
        tenant_context=tenant_context,
        query_request=query_request,
    )

    assert result.response.verification_status == "degraded"
    assert result.response.degraded_reasons == ["QUERY_REQUIRES_CLARIFICATION"]
    assert "attached dataset" in result.response.answer.lower()


@pytest.mark.asyncio()
async def test_execute_standard_query_rejects_higher_tier_namespace() -> None:
    """Standard query execution should reject namespaces that require a higher tier."""

    tenant_context = _tenant_context()
    query_request = QueryRequest(namespace_id=uuid.uuid4(), query="Question")
    namespace = type(
        "NamespaceStub",
        (),
        {"min_execution_tier": ExecutionTier.ENTERPRISE},
    )()
    session = FakeAsyncSession(namespace=namespace)

    with pytest.raises(QueryServiceError, match="requires a higher execution tier"):
        await execute_standard_query(
            session=session,
            tenant_context=tenant_context,
            query_request=query_request,
        )


@pytest.mark.asyncio()
async def test_execute_standard_query_uses_follow_up_context_for_second_document(monkeypatch) -> None:
    """Follow-up summary queries should preserve document-order references in the query plan."""

    tenant_context = _tenant_context()
    namespace_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    query_request = QueryRequest(
        namespace_id=namespace_id,
        query="what about the second document",
    )
    namespace = type(
        "NamespaceStub",
        (),
        {"min_execution_tier": ExecutionTier.STANDARD},
    )()
    session = FakeAsyncSession(namespace=namespace)

    captured_query_plan = None

    from app.models import MessageRole

    message = type("MessageStub", (), {"role": MessageRole.USER, "content": "What is the dataset about?"})()

    async def fake_messages(**kwargs):
        del kwargs
        return [message]

    async def fake_retrieve_hybrid_candidates(**kwargs):
        nonlocal captured_query_plan
        captured_query_plan = kwargs["query_plan"]
        return RetrievalBundle(sparse_hits=[], dense_hits=[], fused_hits=[])

    monkeypatch.setattr(
        "app.services.query.list_conversation_messages",
        fake_messages,
    )
    monkeypatch.setattr(
        "app.services.query.retrieve_hybrid_candidates",
        fake_retrieve_hybrid_candidates,
    )

    await execute_standard_query(
        session=session,
        tenant_context=tenant_context,
        query_request=query_request,
        conversation_id=conversation_id,
    )

    assert captured_query_plan is not None
    assert captured_query_plan.profile.document_reference_rank == 2
    assert captured_query_plan.profile.query_kind == "summary"


@pytest.mark.asyncio()
async def test_execute_standard_query_uses_multi_turn_conversation_context(monkeypatch) -> None:
    """Multi-turn chat history should inform reference-heavy follow-ups beyond one prior turn."""

    tenant_context = _tenant_context()
    namespace_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    query_request = QueryRequest(
        namespace_id=namespace_id,
        query="did it mention pattern miner there",
    )
    namespace = type(
        "NamespaceStub",
        (),
        {"min_execution_tier": ExecutionTier.STANDARD},
    )()
    session = FakeAsyncSession(namespace=namespace)

    captured_query_plan = None

    from app.models import MessageRole

    messages = [
        type("MessageStub", (), {"role": MessageRole.USER, "content": "What is her work experience?"})(),
        type(
            "MessageStub",
            (),
            {
                "role": MessageRole.ASSISTANT,
                "content": "She has experience as an AI Engineer at iCog Labs and as a Backend | AI Developer Intern at iCog Labs.",
            },
        )(),
        type("MessageStub", (), {"role": MessageRole.USER, "content": "What did she do at iCog Labs?"})(),
    ]

    async def fake_messages(**kwargs):
        del kwargs
        return messages

    async def fake_retrieve_hybrid_candidates(**kwargs):
        nonlocal captured_query_plan
        captured_query_plan = kwargs["query_plan"]
        return RetrievalBundle(sparse_hits=[], dense_hits=[], fused_hits=[])

    monkeypatch.setattr(
        "app.services.query.list_conversation_messages",
        fake_messages,
    )
    monkeypatch.setattr(
        "app.services.query.retrieve_hybrid_candidates",
        fake_retrieve_hybrid_candidates,
    )

    await execute_standard_query(
        session=session,
        tenant_context=tenant_context,
        query_request=query_request,
        conversation_id=conversation_id,
    )

    assert captured_query_plan is not None
    assert captured_query_plan.used_conversation_context is True
    assert "icog labs" in captured_query_plan.resolved_query_text.casefold()
