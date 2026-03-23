"""Integration tests for conversation message history routes."""

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
from app.models import ExecutionTier, SubscriptionPlan


@dataclass(frozen=True)
class SeededMessageData:
    """Seeded tenant, conversation, and message data for history tests."""

    tenant_id: uuid.UUID
    conversation_id: uuid.UUID
    foreign_conversation_id: uuid.UUID
    user_message_id: uuid.UUID
    assistant_run_id: uuid.UUID
    raw_api_key: str


@pytest.fixture()
def message_auth_env(monkeypatch) -> str:
    """Configure a deterministic API key salt for message route tests."""

    salt = "integration-test-api-key-salt"
    monkeypatch.setenv("API_KEY_SALT", salt)
    get_settings.cache_clear()
    yield salt
    get_settings.cache_clear()


@pytest.fixture()
def message_client(message_auth_env: str) -> TestClient:
    """Create a test client after message auth settings are configured."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(dispose_database())


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def seeded_message_data(message_auth_env: str) -> SeededMessageData:
    """Insert tenants, API keys, conversations, and persisted messages."""

    tenant_id = uuid.uuid4()
    foreign_tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    foreign_workspace_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    foreign_agent_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    foreign_conversation_id = uuid.uuid4()
    api_key_id = uuid.uuid4()
    user_message_id = uuid.uuid4()
    assistant_message_id = uuid.uuid4()
    assistant_run_id = uuid.uuid4()
    raw_api_key = f"grd_message_{uuid.uuid4().hex}"

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
                    foreign_tenant_id,
                    f"tenant-{foreign_tenant_id}",
                    SubscriptionPlan.FREE.value,
                    ExecutionTier.STANDARD.value,
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
                    hash_api_key(raw_api_key, message_auth_env),
                    "integration-message",
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
                    foreign_workspace_id,
                    foreign_tenant_id,
                    "Foreign",
                    "foreign",
                    "Foreign workspace",
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
                (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                """,
                (
                    agent_id,
                    tenant_id,
                    workspace_id,
                    "Ops Assistant",
                    "Default auto agent",
                    "",
                    "auto",
                    json.dumps(["auto", "instant"]),
                    "active",
                    foreign_agent_id,
                    foreign_tenant_id,
                    foreign_workspace_id,
                    "Foreign Assistant",
                    "Foreign only",
                    "",
                    "auto",
                    json.dumps(["auto", "instant"]),
                    "active",
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
                (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    conversation_id,
                    tenant_id,
                    workspace_id,
                    agent_id,
                    api_key_id,
                    "Advisor Thread",
                    "auto",
                    foreign_conversation_id,
                    foreign_tenant_id,
                    foreign_workspace_id,
                    foreign_agent_id,
                    None,
                    "Foreign Thread",
                    "auto",
                ),
            )
            cursor.execute(
                """
                insert into messages (
                    message_id,
                    tenant_id,
                    conversation_id,
                    created_by_api_key_id,
                    run_id,
                    role,
                    content,
                    created_at
                )
                values
                (%s, %s, %s, %s, %s, %s, %s, now() - interval '1 minute'),
                (%s, %s, %s, %s, %s, %s, %s, now())
                """,
                (
                    user_message_id,
                    tenant_id,
                    conversation_id,
                    api_key_id,
                    None,
                    "user",
                    "What is the maintenance window?",
                    assistant_message_id,
                    tenant_id,
                    conversation_id,
                    None,
                    assistant_run_id,
                    "assistant",
                    "Maintenance window: Friday at 22:00 UTC. [E001]",
                ),
            )

    yield SeededMessageData(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        foreign_conversation_id=foreign_conversation_id,
        user_message_id=user_message_id,
        assistant_run_id=assistant_run_id,
        raw_api_key=raw_api_key,
    )

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "delete from messages where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            cursor.execute(
                "delete from conversations where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            cursor.execute(
                "delete from agents where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            cursor.execute(
                "delete from workspaces where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            cursor.execute(
                "delete from api_keys where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            cursor.execute(
                "delete from tenants where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )


def test_message_list_requires_api_key(message_client: TestClient) -> None:
    """Message history should reject unauthenticated callers."""

    response = message_client.get(f"/v1/conversations/{uuid.uuid4()}/messages")

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is required."}


def test_message_list_returns_ordered_history_for_conversation(
    message_client: TestClient,
    seeded_message_data: SeededMessageData,
) -> None:
    """Message history should return ordered messages with role and run metadata."""

    response = message_client.get(
        f"/v1/conversations/{seeded_message_data.conversation_id}/messages",
        headers={"X-API-Key": seeded_message_data.raw_api_key},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["role"] for item in payload] == ["user", "assistant"]
    assert payload[0]["message_id"] == str(seeded_message_data.user_message_id)
    assert payload[0]["run_id"] is None
    assert payload[1]["run_id"] == str(seeded_message_data.assistant_run_id)


def test_message_list_rejects_foreign_conversation(
    message_client: TestClient,
    seeded_message_data: SeededMessageData,
) -> None:
    """Tenants should not be able to list another tenant's messages."""

    response = message_client.get(
        f"/v1/conversations/{seeded_message_data.foreign_conversation_id}/messages",
        headers={"X-API-Key": seeded_message_data.raw_api_key},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found for tenant."}
