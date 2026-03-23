"""Integration tests for conversation routes."""

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
class SeededConversationData:
    """Seeded tenant, agent, and conversation data for conversation tests."""

    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    agent_id: uuid.UUID
    instant_only_agent_id: uuid.UUID
    foreign_conversation_id: uuid.UUID
    raw_api_key: str


@pytest.fixture()
def conversation_auth_env(monkeypatch) -> str:
    """Configure a deterministic API key salt for conversation route tests."""

    salt = "integration-test-api-key-salt"
    monkeypatch.setenv("API_KEY_SALT", salt)
    get_settings.cache_clear()
    yield salt
    get_settings.cache_clear()


@pytest.fixture()
def conversation_client(conversation_auth_env: str) -> TestClient:
    """Create a test client after conversation auth settings are configured."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(dispose_database())


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def seeded_conversation_data(conversation_auth_env: str) -> SeededConversationData:
    """Insert tenants, API keys, workspaces, agents, and baseline conversations."""

    tenant_id = uuid.uuid4()
    foreign_tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    foreign_workspace_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    instant_only_agent_id = uuid.uuid4()
    foreign_agent_id = uuid.uuid4()
    foreign_conversation_id = uuid.uuid4()
    api_key_id = uuid.uuid4()
    raw_api_key = f"grd_conversation_{uuid.uuid4().hex}"

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
                    hash_api_key(raw_api_key, conversation_auth_env),
                    "integration-conversation",
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
                    instant_only_agent_id,
                    tenant_id,
                    workspace_id,
                    "Instant Assistant",
                    "Instant only",
                    "",
                    "instant",
                    json.dumps(["instant"]),
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
                values (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    foreign_conversation_id,
                    foreign_tenant_id,
                    foreign_workspace_id,
                    foreign_agent_id,
                    None,
                    "Foreign Thread",
                    "auto",
                ),
            )

    yield SeededConversationData(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        agent_id=agent_id,
        instant_only_agent_id=instant_only_agent_id,
        foreign_conversation_id=foreign_conversation_id,
        raw_api_key=raw_api_key,
    )

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
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


def test_conversation_create_requires_api_key(
    conversation_client: TestClient,
) -> None:
    """Conversation creation should reject unauthenticated callers."""

    response = conversation_client.post(
        f"/v1/agents/{uuid.uuid4()}/conversations",
        json={"title": "Advisor demo"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is required."}


def test_conversation_create_inherits_agent_defaults(
    conversation_client: TestClient,
    seeded_conversation_data: SeededConversationData,
) -> None:
    """Conversation creation should inherit workspace and default mode from the agent."""

    response = conversation_client.post(
        f"/v1/agents/{seeded_conversation_data.agent_id}/conversations",
        headers={"X-API-Key": seeded_conversation_data.raw_api_key},
        json={"title": "Advisor Demo Thread"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["agent_id"] == str(seeded_conversation_data.agent_id)
    assert payload["workspace_id"] == str(seeded_conversation_data.workspace_id)
    assert payload["title"] == "Advisor Demo Thread"
    assert payload["last_used_mode"] == "auto"
    assert payload["created_by_api_key_id"] is not None


def test_conversation_create_rejects_mode_outside_agent_allowlist(
    conversation_client: TestClient,
    seeded_conversation_data: SeededConversationData,
) -> None:
    """Conversation creation should respect the agent's allowed modes."""

    response = conversation_client.post(
        f"/v1/agents/{seeded_conversation_data.instant_only_agent_id}/conversations",
        headers={"X-API-Key": seeded_conversation_data.raw_api_key},
        json={"mode": "auto"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Conversation mode must be one of the agent's allowed modes."
    }


def test_conversation_list_is_agent_scoped_and_newest_first(
    conversation_client: TestClient,
    seeded_conversation_data: SeededConversationData,
) -> None:
    """Conversation listing should stay scoped to one agent and order newest first."""

    first_response = conversation_client.post(
        f"/v1/agents/{seeded_conversation_data.agent_id}/conversations",
        headers={"X-API-Key": seeded_conversation_data.raw_api_key},
        json={"title": "First Thread"},
    )
    second_response = conversation_client.post(
        f"/v1/agents/{seeded_conversation_data.agent_id}/conversations",
        headers={"X-API-Key": seeded_conversation_data.raw_api_key},
        json={"title": "Second Thread", "mode": "instant"},
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    response = conversation_client.get(
        f"/v1/agents/{seeded_conversation_data.agent_id}/conversations",
        headers={"X-API-Key": seeded_conversation_data.raw_api_key},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["title"] for item in payload] == ["Second Thread", "First Thread"]


def test_conversation_get_rejects_foreign_conversation(
    conversation_client: TestClient,
    seeded_conversation_data: SeededConversationData,
) -> None:
    """Tenants should not be able to fetch another tenant's conversation."""

    response = conversation_client.get(
        f"/v1/conversations/{seeded_conversation_data.foreign_conversation_id}",
        headers={"X-API-Key": seeded_conversation_data.raw_api_key},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found for tenant."}


def test_conversation_patch_updates_title_and_mode(
    conversation_client: TestClient,
    seeded_conversation_data: SeededConversationData,
) -> None:
    """Conversation patch should update the title and last used mode."""

    create_response = conversation_client.post(
        f"/v1/agents/{seeded_conversation_data.agent_id}/conversations",
        headers={"X-API-Key": seeded_conversation_data.raw_api_key},
        json={"title": "Ops Thread"},
    )
    conversation_id = create_response.json()["conversation_id"]

    response = conversation_client.patch(
        f"/v1/conversations/{conversation_id}",
        headers={"X-API-Key": seeded_conversation_data.raw_api_key},
        json={
            "title": "Renamed Ops Thread",
            "mode": "instant",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Renamed Ops Thread"
    assert payload["last_used_mode"] == "instant"
