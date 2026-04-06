"""Evaluation-style checks for conversational edge cases in Standard."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from app.api.deps import TenantContext
from app.models import ExecutionTier
from app.schemas.query import QueryRequest
from app.services.query import execute_standard_query


@dataclass
class _FakeScalarResult:
    value: object | None

    def scalar_one_or_none(self):
        return self.value


class _FakeAsyncSession:
    def __init__(self, namespace: object | None) -> None:
        self.namespace = namespace
        self.added: list[object] = []

    async def execute(self, statement, params=None):
        del statement, params
        return _FakeScalarResult(self.namespace)

    def add(self, value) -> None:
        self.added.append(value)

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def refresh(self, value) -> None:
        return None


def _tenant_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid.uuid4(),
        tenant_name="tenant",
        subscription_plan="pro",  # type: ignore[arg-type]
        max_execution_tier=ExecutionTier.ENTERPRISE,
        api_key_id=uuid.uuid4(),
        api_key_label="test-key",
    )


@pytest.mark.asyncio()
@pytest.mark.parametrize(
    "query_text",
    ["hi", "hello!", "thanks", "what can you do", "hi how are you", "hello can you help me"],
)
async def test_standard_smalltalk_queries_return_friendly_clarification(query_text: str) -> None:
    """Conversational filler should stay friendly without pretending to be grounded."""

    namespace = type(
        "NamespaceStub",
        (),
        {"min_execution_tier": ExecutionTier.STANDARD},
    )()
    session = _FakeAsyncSession(namespace)

    result = await execute_standard_query(
        session=session,
        tenant_context=_tenant_context(),
        query_request=QueryRequest(namespace_id=uuid.uuid4(), query=query_text),
    )

    assert result.response.verification_status == "degraded"
    assert result.response.degraded_reasons == ["QUERY_REQUIRES_CLARIFICATION"]
    assert "attached dataset" in result.response.answer.lower()
