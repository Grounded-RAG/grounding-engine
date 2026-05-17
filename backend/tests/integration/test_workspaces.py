"""Integration tests for workspace routes."""

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
class SeededWorkspaceData:
    """Seeded tenants, API key, and workspaces for workspace route tests."""

    tenant_id: uuid.UUID
    existing_workspace_id: uuid.UUID
    foreign_workspace_id: uuid.UUID
    raw_api_key: str


@pytest.fixture()
def workspace_auth_env(monkeypatch) -> str:
    """Configure a deterministic API key salt for workspace route tests."""

    salt = "integration-test-api-key-salt"
    monkeypatch.setenv("API_KEY_SALT", salt)
    get_settings.cache_clear()
    yield salt
    get_settings.cache_clear()


@pytest.fixture()
def workspace_client(workspace_auth_env: str) -> TestClient:
    """Create a test client after workspace-related auth settings are configured."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(dispose_database())


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def seeded_workspace_data(workspace_auth_env: str) -> SeededWorkspaceData:
    """Insert tenants, API keys, and baseline workspaces for CRUD tests."""

    tenant_id = uuid.uuid4()
    foreign_tenant_id = uuid.uuid4()
    existing_workspace_id = uuid.uuid4()
    foreign_workspace_id = uuid.uuid4()
    raw_api_key = f"grd_workspace_{uuid.uuid4().hex}"

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
                    hash_api_key(raw_api_key, workspace_auth_env),
                    "integration-workspace",
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
                    existing_workspace_id,
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
                    "Foreign Workspace",
                    "foreign-workspace",
                    "Should stay hidden",
                ),
            )

    yield SeededWorkspaceData(
        tenant_id=tenant_id,
        existing_workspace_id=existing_workspace_id,
        foreign_workspace_id=foreign_workspace_id,
        raw_api_key=raw_api_key,
    )

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
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


def test_workspace_create_requires_api_key(
    workspace_client: TestClient,
) -> None:
    """Workspace creation should reject unauthenticated callers."""

    response = workspace_client.post(
        "/v1/workspaces",
        json={"name": "Operations"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is required."}


def test_workspace_create_generates_slug_and_persists_row(
    workspace_client: TestClient,
    seeded_workspace_data: SeededWorkspaceData,
) -> None:
    """Workspace creation should auto-generate a slug and persist the row."""

    response = workspace_client.post(
        "/v1/workspaces",
        headers={"X-API-Key": seeded_workspace_data.raw_api_key},
        json={
            "name": "Platform Research",
            "description": "Research and advisor demos",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "Platform Research"
    assert payload["slug"] == "platform-research"
    assert payload["description"] == "Research and advisor demos"

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select name, slug, description
                from workspaces
                where workspace_id = %s and tenant_id = %s
                """,
                (payload["workspace_id"], seeded_workspace_data.tenant_id),
            )
            workspace_row = cursor.fetchone()

    assert workspace_row == (
        "Platform Research",
        "platform-research",
        "Research and advisor demos",
    )


def test_workspace_list_is_tenant_scoped(
    workspace_client: TestClient,
    seeded_workspace_data: SeededWorkspaceData,
) -> None:
    """Workspace listing should only return rows owned by the authenticated tenant."""

    response = workspace_client.get(
        "/v1/workspaces",
        headers={"X-API-Key": seeded_workspace_data.raw_api_key},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["workspace_id"] == str(seeded_workspace_data.existing_workspace_id)
    assert payload[0]["name"] == "Operations"
    assert payload[0]["slug"] == "operations"


def test_workspace_get_rejects_foreign_workspace(
    workspace_client: TestClient,
    seeded_workspace_data: SeededWorkspaceData,
) -> None:
    """Tenants should not be able to fetch workspaces owned by another tenant."""

    response = workspace_client.get(
        f"/v1/workspaces/{seeded_workspace_data.foreign_workspace_id}",
        headers={"X-API-Key": seeded_workspace_data.raw_api_key},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Workspace not found for tenant."}


def test_workspace_patch_updates_fields(
    workspace_client: TestClient,
    seeded_workspace_data: SeededWorkspaceData,
) -> None:
    """Workspace patch should update the requested fields for the tenant."""

    response = workspace_client.patch(
        f"/v1/workspaces/{seeded_workspace_data.existing_workspace_id}",
        headers={"X-API-Key": seeded_workspace_data.raw_api_key},
        json={
            "name": "Platform Workspace",
            "slug": "platform-workspace",
            "description": "Main product shell workspace",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Platform Workspace"
    assert payload["slug"] == "platform-workspace"
    assert payload["description"] == "Main product shell workspace"

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select name, slug, description
                from workspaces
                where workspace_id = %s and tenant_id = %s
                """,
                (
                    seeded_workspace_data.existing_workspace_id,
                    seeded_workspace_data.tenant_id,
                ),
            )
            workspace_row = cursor.fetchone()

    assert workspace_row == (
        "Platform Workspace",
        "platform-workspace",
        "Main product shell workspace",
    )


def test_workspace_create_rejects_duplicate_slug(
    workspace_client: TestClient,
    seeded_workspace_data: SeededWorkspaceData,
) -> None:
    """Workspace creation should reject duplicate slugs for the same tenant."""

    response = workspace_client.post(
        "/v1/workspaces",
        headers={"X-API-Key": seeded_workspace_data.raw_api_key},
        json={
            "name": "Another Name",
            "slug": "operations",
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Workspace slug already exists for tenant."}
