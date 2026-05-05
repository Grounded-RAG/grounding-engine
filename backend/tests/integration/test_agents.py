"""Integration tests for agent routes and dataset attachments."""

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


@dataclass(frozen=True)
class SeededAgentData:
    """Seeded tenant, workspaces, and datasets for agent route tests."""

    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    secondary_workspace_id: uuid.UUID
    dataset_id: uuid.UUID
    secondary_dataset_id: uuid.UUID
    foreign_dataset_id: uuid.UUID
    raw_api_key: str


@pytest.fixture()
def agent_auth_env(monkeypatch) -> str:
    """Configure a deterministic API key salt for agent route tests."""

    salt = "integration-test-api-key-salt"
    monkeypatch.setenv("API_KEY_SALT", salt)
    get_settings.cache_clear()
    yield salt
    get_settings.cache_clear()


@pytest.fixture()
def agent_client(agent_auth_env: str) -> TestClient:
    """Create a test client after agent settings are configured."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(dispose_database())


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def seeded_agent_data(agent_auth_env: str) -> SeededAgentData:
    """Insert tenants, workspaces, datasets, and one API key for agent tests."""

    tenant_id = uuid.uuid4()
    foreign_tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    secondary_workspace_id = uuid.uuid4()
    foreign_workspace_id = uuid.uuid4()
    dataset_id = uuid.uuid4()
    secondary_dataset_id = uuid.uuid4()
    foreign_dataset_id = uuid.uuid4()
    raw_api_key = f"grd_agent_{uuid.uuid4().hex}"

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
                    uuid.uuid4(),
                    tenant_id,
                    hash_api_key(raw_api_key, agent_auth_env),
                    "integration-agent",
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
                values (%s, %s, %s, %s, %s), (%s, %s, %s, %s, %s)
                """,
                (
                    workspace_id,
                    tenant_id,
                    "Operations",
                    "operations",
                    "Primary workspace",
                    secondary_workspace_id,
                    tenant_id,
                    "Research",
                    "research",
                    "Secondary workspace",
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
                    secondary_workspace_id,
                    "research-dataset",
                    "research",
                    SensitivityLevel.INTERNAL.value,
                    FreshnessProfile.BALANCED.value,
                    ExecutionTier.STANDARD.value,
                    False,
                    False,
                    foreign_dataset_id,
                    foreign_tenant_id,
                    foreign_workspace_id,
                    "foreign-dataset",
                    "general",
                    SensitivityLevel.INTERNAL.value,
                    FreshnessProfile.BALANCED.value,
                    ExecutionTier.STANDARD.value,
                    False,
                    False,
                ),
            )

    yield SeededAgentData(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        secondary_workspace_id=secondary_workspace_id,
        dataset_id=dataset_id,
        secondary_dataset_id=secondary_dataset_id,
        foreign_dataset_id=foreign_dataset_id,
        raw_api_key=raw_api_key,
    )

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "delete from agent_datasets where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            cursor.execute(
                "delete from agents where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            cursor.execute(
                "delete from namespaces where tenant_id in (%s, %s)",
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


def test_agent_create_requires_api_key(agent_client: TestClient) -> None:
    """Agent creation should reject unauthenticated callers."""

    response = agent_client.post(
        "/v1/agents",
        json={
            "workspace_id": str(uuid.uuid4()),
            "name": "Ops Assistant",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is required."}


def test_agent_create_persists_supported_modes_only(
    agent_client: TestClient,
    seeded_agent_data: SeededAgentData,
) -> None:
    """Agent creation should persist supported modes and reject future ones."""

    response = agent_client.post(
        "/v1/agents",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
        json={
            "workspace_id": str(seeded_agent_data.workspace_id),
            "name": "Ops Assistant",
            "description": "Handles everyday operations questions",
            "system_instructions": "Answer only from attached datasets.",
            "default_mode": "auto",
            "allowed_modes": ["auto", "instant"],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Ops Assistant"
    assert payload["default_mode"] == "auto"
    assert payload["allowed_modes"] == ["auto", "instant"]
    assert payload["dataset_ids"] == []
    assert payload["status"] == "active"


def test_agent_create_allows_thinking_mode(
    agent_client: TestClient,
    seeded_agent_data: SeededAgentData,
) -> None:
    """Agent configuration should allow Thinking now that Enterprise is live."""

    response = agent_client.post(
        "/v1/agents",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
        json={
            "workspace_id": str(seeded_agent_data.workspace_id),
            "name": "Future Agent",
            "default_mode": "thinking",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["default_mode"] == "thinking"
    assert payload["allowed_modes"] == ["auto", "instant", "thinking"]


def test_agent_create_defaults_include_thinking_when_enterprise_is_live(
    agent_client: TestClient,
    seeded_agent_data: SeededAgentData,
) -> None:
    """Agent creation should include Thinking by default while Enterprise is live."""

    response = agent_client.post(
        "/v1/agents",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
        json={
            "workspace_id": str(seeded_agent_data.workspace_id),
            "name": "Default Modes Agent",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["default_mode"] == "auto"
    assert payload["allowed_modes"] == ["auto", "instant", "thinking"]


def test_agent_attach_dataset_requires_same_workspace(
    agent_client: TestClient,
    seeded_agent_data: SeededAgentData,
) -> None:
    """Agents should only attach datasets from the same workspace."""

    create_response = agent_client.post(
        "/v1/agents",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
        json={
            "workspace_id": str(seeded_agent_data.workspace_id),
            "name": "Ops Assistant",
        },
    )
    agent_id = create_response.json()["agent_id"]

    attach_response = agent_client.post(
        f"/v1/agents/{agent_id}/datasets",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
        json={"dataset_id": str(seeded_agent_data.secondary_dataset_id)},
    )

    assert attach_response.status_code == 409
    assert attach_response.json() == {
        "detail": "Dataset must belong to the same workspace as the agent."
    }


def test_agent_attach_and_detach_dataset_updates_response(
    agent_client: TestClient,
    seeded_agent_data: SeededAgentData,
) -> None:
    """Dataset attachment and detachment should update the agent view cleanly."""

    create_response = agent_client.post(
        "/v1/agents",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
        json={
            "workspace_id": str(seeded_agent_data.workspace_id),
            "name": "Ops Assistant",
        },
    )
    agent_id = create_response.json()["agent_id"]

    attach_response = agent_client.post(
        f"/v1/agents/{agent_id}/datasets",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
        json={"dataset_id": str(seeded_agent_data.dataset_id)},
    )

    assert attach_response.status_code == 200
    assert attach_response.json()["dataset_ids"] == [str(seeded_agent_data.dataset_id)]

    detach_response = agent_client.delete(
        f"/v1/agents/{agent_id}/datasets/{seeded_agent_data.dataset_id}",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
    )

    assert detach_response.status_code == 204

    get_response = agent_client.get(
        f"/v1/agents/{agent_id}",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
    )
    assert get_response.status_code == 200
    assert get_response.json()["dataset_ids"] == []


def test_agent_list_filters_by_workspace_and_hides_foreign_rows(
    agent_client: TestClient,
    seeded_agent_data: SeededAgentData,
) -> None:
    """Agent listing should stay tenant-scoped and support workspace filters."""

    for workspace_id, name in (
        (seeded_agent_data.workspace_id, "Ops Assistant"),
        (seeded_agent_data.secondary_workspace_id, "Research Assistant"),
    ):
        response = agent_client.post(
            "/v1/agents",
            headers={"X-API-Key": seeded_agent_data.raw_api_key},
            json={
                "workspace_id": str(workspace_id),
                "name": name,
            },
        )
        assert response.status_code == 201

    list_response = agent_client.get(
        "/v1/agents",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
        params={"workspace_id": str(seeded_agent_data.secondary_workspace_id)},
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["name"] == "Research Assistant"


def test_agent_patch_updates_metadata_and_modes(
    agent_client: TestClient,
    seeded_agent_data: SeededAgentData,
) -> None:
    """Agent patch should update metadata and current-mode settings."""

    create_response = agent_client.post(
        "/v1/agents",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
        json={
            "workspace_id": str(seeded_agent_data.workspace_id),
            "name": "Ops Assistant",
        },
    )
    agent_id = create_response.json()["agent_id"]

    patch_response = agent_client.patch(
        f"/v1/agents/{agent_id}",
        headers={"X-API-Key": seeded_agent_data.raw_api_key},
        json={
            "description": "Operations helper",
            "system_instructions": "Stay grounded and concise.",
            "default_mode": "instant",
            "allowed_modes": ["instant"],
        },
    )

    assert patch_response.status_code == 200
    payload = patch_response.json()
    assert payload["description"] == "Operations helper"
    assert payload["system_instructions"] == "Stay grounded and concise."
    assert payload["default_mode"] == "instant"
    assert payload["allowed_modes"] == ["instant"]
