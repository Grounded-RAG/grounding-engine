"""Integration tests for the agent chat route."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.database import dispose_database
from app.core.security import hash_api_key
from app.main import create_app
from app.models import ExecutionTier, FreshnessProfile, SensitivityLevel, SubscriptionPlan
from app.schemas.query import GroundedAnswerResponse
from app.services.query import QueryExecutionResult


@dataclass(frozen=True)
class SeededAgentChatData:
    """Seeded tenant, datasets, agents, and conversations for agent chat tests."""

    tenant_id: uuid.UUID
    single_dataset_agent_id: uuid.UUID
    no_dataset_agent_id: uuid.UUID
    multi_dataset_agent_id: uuid.UUID
    single_conversation_id: uuid.UUID
    no_dataset_conversation_id: uuid.UUID
    multi_conversation_id: uuid.UUID
    dataset_id: uuid.UUID
    secondary_dataset_id: uuid.UUID
    raw_api_key: str


@pytest.fixture()
def agent_chat_auth_env(monkeypatch) -> str:
    """Configure a deterministic API key salt for agent chat tests."""

    salt = "integration-test-api-key-salt"
    monkeypatch.setenv("API_KEY_SALT", salt)
    get_settings.cache_clear()
    yield salt
    get_settings.cache_clear()


@pytest.fixture()
def agent_chat_client(agent_chat_auth_env: str) -> TestClient:
    """Create a test client after agent chat settings are configured."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(dispose_database())


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def seeded_agent_chat_data(agent_chat_auth_env: str) -> SeededAgentChatData:
    """Insert the product-shell rows needed to exercise the chat route."""

    tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    dataset_id = uuid.uuid4()
    secondary_dataset_id = uuid.uuid4()
    single_dataset_agent_id = uuid.uuid4()
    no_dataset_agent_id = uuid.uuid4()
    multi_dataset_agent_id = uuid.uuid4()
    single_conversation_id = uuid.uuid4()
    no_dataset_conversation_id = uuid.uuid4()
    multi_conversation_id = uuid.uuid4()
    api_key_id = uuid.uuid4()
    raw_api_key = f"grd_agent_chat_{uuid.uuid4().hex}"

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                insert into tenants (
                    tenant_id,
                    name,
                    subscription_plan,
                    max_execution_tier,
                    default_policy,
                    retention_days
                )
                values (%s, %s, %s, %s, %s::jsonb, %s)
                """,
                (
                    tenant_id,
                    f"tenant-{tenant_id}",
                    SubscriptionPlan.BUSINESS.value,
                    ExecutionTier.CRITICAL.value,
                    json.dumps({"tier": "standard"}),
                    365,
                ),
            )
            cursor.execute(
                """
                insert into api_keys (
                    key_id,
                    tenant_id,
                    key_hash,
                    label
                )
                values (%s, %s, %s, %s)
                """,
                (
                    api_key_id,
                    tenant_id,
                    hash_api_key(raw_api_key, agent_chat_auth_env),
                    "integration-agent-chat",
                ),
            )
            cursor.execute(
                """
                insert into workspaces (
                    workspace_id,
                    tenant_id,
                    name,
                    slug,
                    description
                )
                values (%s, %s, %s, %s, %s)
                """,
                (
                    workspace_id,
                    tenant_id,
                    "Operations",
                    "operations",
                    "Primary workspace",
                ),
            )
            cursor.execute(
                """
                insert into namespaces (
                    namespace_id,
                    tenant_id,
                    workspace_id,
                    name,
                    domain,
                    sensitivity_level,
                    freshness_profile,
                    min_execution_tier,
                    allow_web_fallback,
                    allow_internal_model_retrieval
                )
                values
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s),
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    dataset_id,
                    tenant_id,
                    workspace_id,
                    "operations-dataset",
                    "general",
                    SensitivityLevel.INTERNAL.value,
                    FreshnessProfile.BALANCED.value,
                    ExecutionTier.STANDARD.value,
                    False,
                    False,
                    secondary_dataset_id,
                    tenant_id,
                    workspace_id,
                    "research-dataset",
                    "research",
                    SensitivityLevel.INTERNAL.value,
                    FreshnessProfile.BALANCED.value,
                    ExecutionTier.STANDARD.value,
                    False,
                    False,
                ),
            )
            cursor.execute(
                """
                insert into agents (
                    agent_id,
                    tenant_id,
                    workspace_id,
                    name,
                    description,
                    system_instructions,
                    default_mode,
                    allowed_modes,
                    status
                )
                values
                (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s),
                (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s),
                (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                """,
                (
                    single_dataset_agent_id,
                    tenant_id,
                    workspace_id,
                    "Ops Assistant",
                    "One dataset attached",
                    "",
                    "auto",
                    json.dumps(["auto", "instant"]),
                    "active",
                    no_dataset_agent_id,
                    tenant_id,
                    workspace_id,
                    "Empty Assistant",
                    "No dataset attached",
                    "",
                    "auto",
                    json.dumps(["auto", "instant"]),
                    "active",
                    multi_dataset_agent_id,
                    tenant_id,
                    workspace_id,
                    "Multi Assistant",
                    "Two datasets attached",
                    "",
                    "instant",
                    json.dumps(["instant"]),
                    "active",
                ),
            )
            cursor.execute(
                """
                insert into agent_datasets (
                    attachment_id,
                    tenant_id,
                    agent_id,
                    dataset_id
                )
                values
                (%s, %s, %s, %s),
                (%s, %s, %s, %s),
                (%s, %s, %s, %s)
                """,
                (
                    uuid.uuid4(),
                    tenant_id,
                    single_dataset_agent_id,
                    dataset_id,
                    uuid.uuid4(),
                    tenant_id,
                    multi_dataset_agent_id,
                    dataset_id,
                    uuid.uuid4(),
                    tenant_id,
                    multi_dataset_agent_id,
                    secondary_dataset_id,
                ),
            )
            cursor.execute(
                """
                insert into conversations (
                    conversation_id,
                    tenant_id,
                    workspace_id,
                    agent_id,
                    created_by_api_key_id,
                    title,
                    last_used_mode
                )
                values
                (%s, %s, %s, %s, %s, %s, %s),
                (%s, %s, %s, %s, %s, %s, %s),
                (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    single_conversation_id,
                    tenant_id,
                    workspace_id,
                    single_dataset_agent_id,
                    api_key_id,
                    "Ops Thread",
                    "auto",
                    no_dataset_conversation_id,
                    tenant_id,
                    workspace_id,
                    no_dataset_agent_id,
                    api_key_id,
                    "Empty Thread",
                    "auto",
                    multi_conversation_id,
                    tenant_id,
                    workspace_id,
                    multi_dataset_agent_id,
                    api_key_id,
                    "Multi Thread",
                    "instant",
                ),
            )

    yield SeededAgentChatData(
        tenant_id=tenant_id,
        single_dataset_agent_id=single_dataset_agent_id,
        no_dataset_agent_id=no_dataset_agent_id,
        multi_dataset_agent_id=multi_dataset_agent_id,
        single_conversation_id=single_conversation_id,
        no_dataset_conversation_id=no_dataset_conversation_id,
        multi_conversation_id=multi_conversation_id,
        dataset_id=dataset_id,
        secondary_dataset_id=secondary_dataset_id,
        raw_api_key=raw_api_key,
    )

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("delete from messages where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from query_traces where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from conversations where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from agent_datasets where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from agents where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from namespaces where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from workspaces where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from api_keys where tenant_id = %s", (tenant_id,))
            cursor.execute("delete from tenants where tenant_id = %s", (tenant_id,))


def test_agent_chat_requires_api_key(agent_chat_client: TestClient) -> None:
    """Agent chat should reject unauthenticated callers."""

    response = agent_chat_client.post(
        f"/v1/agents/{uuid.uuid4()}/chat",
        json={
            "conversation_id": str(uuid.uuid4()),
            "message": "What is the maintenance window?",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is required."}


def test_agent_chat_persists_messages_and_returns_run_headers(
    agent_chat_client: TestClient,
    seeded_agent_chat_data: SeededAgentChatData,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agent chat should persist both message roles and return run metadata."""

    run_id = uuid.uuid4()

    async def fake_execute_standard_query(
        *,
        session,
        tenant_context,
        query_request,
        agent_id,
        conversation_id,
        selected_mode,
    ):
        del session, tenant_context
        assert query_request.namespace_id == seeded_agent_chat_data.dataset_id
        assert query_request.query == "What is the maintenance window?"
        assert agent_id == seeded_agent_chat_data.single_dataset_agent_id
        assert conversation_id == seeded_agent_chat_data.single_conversation_id
        assert selected_mode.value == "auto"
        return QueryExecutionResult(
            response=GroundedAnswerResponse(
                answer="Maintenance window: Friday at 22:00 UTC. [E001]",
                citations=[
                    {
                        "citation_id": "E001",
                        "chunk_id": "chunk-1",
                        "document_id": uuid.uuid4(),
                        "chunk_index": 0,
                        "quote": "Maintenance window: Friday at 22:00 UTC.",
                    }
                ],
                confidence_score=0.91,
                verification_status="passed",
                degraded_reasons=[],
            ),
            trace_id=run_id,
        )

    monkeypatch.setattr(
        "app.services.agent_chat.execute_standard_query",
        fake_execute_standard_query,
    )

    response = agent_chat_client.post(
        f"/v1/agents/{seeded_agent_chat_data.single_dataset_agent_id}/chat",
        headers={"X-API-Key": seeded_agent_chat_data.raw_api_key},
        json={
            "conversation_id": str(seeded_agent_chat_data.single_conversation_id),
            "message": "What is the maintenance window?",
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Run-Id"] == str(run_id)
    assert response.headers["X-Trace-Id"] == str(run_id)
    payload = response.json()
    assert payload["run_id"] == str(run_id)
    assert payload["dataset_id"] == str(seeded_agent_chat_data.dataset_id)
    assert payload["mode"] == "auto"
    assert payload["verification_status"] == "passed"

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select role, content, run_id
                from messages
                where tenant_id = %s and conversation_id = %s
                order by created_at asc, message_id asc
                """,
                (
                    seeded_agent_chat_data.tenant_id,
                    seeded_agent_chat_data.single_conversation_id,
                ),
            )
            message_rows = cursor.fetchall()
            cursor.execute(
                """
                select last_used_mode
                from conversations
                where tenant_id = %s and conversation_id = %s
                """,
                (
                    seeded_agent_chat_data.tenant_id,
                    seeded_agent_chat_data.single_conversation_id,
                ),
            )
            conversation_row = cursor.fetchone()

    assert len(message_rows) == 2
    user_rows = [row for row in message_rows if row[0] == "user"]
    assistant_rows = [row for row in message_rows if row[0] == "assistant"]
    assert len(user_rows) == 1
    assert len(assistant_rows) == 1
    assert user_rows[0][1] == "What is the maintenance window?"
    assert user_rows[0][2] is None
    assert assistant_rows[0][2] == run_id
    assert conversation_row == ("auto",)


def test_agent_chat_rejects_agent_without_attached_dataset(
    agent_chat_client: TestClient,
    seeded_agent_chat_data: SeededAgentChatData,
) -> None:
    """Agents without attached datasets should not accept chat requests."""

    response = agent_chat_client.post(
        f"/v1/agents/{seeded_agent_chat_data.no_dataset_agent_id}/chat",
        headers={"X-API-Key": seeded_agent_chat_data.raw_api_key},
        json={
            "conversation_id": str(seeded_agent_chat_data.no_dataset_conversation_id),
            "message": "Question",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Agent must have at least one attached dataset before chat."
    }


def test_agent_chat_requires_dataset_choice_for_multi_dataset_agent(
    agent_chat_client: TestClient,
    seeded_agent_chat_data: SeededAgentChatData,
) -> None:
    """Multi-dataset agents should require an explicit dataset selection for now."""

    response = agent_chat_client.post(
        f"/v1/agents/{seeded_agent_chat_data.multi_dataset_agent_id}/chat",
        headers={"X-API-Key": seeded_agent_chat_data.raw_api_key},
        json={
            "conversation_id": str(seeded_agent_chat_data.multi_conversation_id),
            "message": "Question",
        },
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Agent has multiple attached datasets. Select one dataset for this chat request."
    }


def test_agent_chat_accepts_explicit_dataset_for_multi_dataset_agent(
    agent_chat_client: TestClient,
    seeded_agent_chat_data: SeededAgentChatData,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multi-dataset agents should chat cleanly once the dataset is chosen explicitly."""

    async def fake_execute_standard_query(
        *,
        session,
        tenant_context,
        query_request,
        agent_id,
        conversation_id,
        selected_mode,
    ):
        del session, tenant_context
        assert query_request.namespace_id == seeded_agent_chat_data.secondary_dataset_id
        assert agent_id == seeded_agent_chat_data.multi_dataset_agent_id
        assert conversation_id == seeded_agent_chat_data.multi_conversation_id
        assert selected_mode.value == "instant"
        return QueryExecutionResult(
            response=GroundedAnswerResponse(
                answer="Research dataset answer. [E001]",
                citations=[],
                confidence_score=0.5,
                verification_status="degraded",
                degraded_reasons=["INSUFFICIENT_SUPPORT"],
            ),
            trace_id=uuid.uuid4(),
        )

    monkeypatch.setattr(
        "app.services.agent_chat.execute_standard_query",
        fake_execute_standard_query,
    )

    response = agent_chat_client.post(
        f"/v1/agents/{seeded_agent_chat_data.multi_dataset_agent_id}/chat",
        headers={"X-API-Key": seeded_agent_chat_data.raw_api_key},
        json={
            "conversation_id": str(seeded_agent_chat_data.multi_conversation_id),
            "message": "Question",
            "dataset_id": str(seeded_agent_chat_data.secondary_dataset_id),
        },
    )

    assert response.status_code == 200
    assert response.json()["dataset_id"] == str(seeded_agent_chat_data.secondary_dataset_id)
    assert response.json()["mode"] == "instant"
