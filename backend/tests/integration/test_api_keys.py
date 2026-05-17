"""Integration tests for API key management routes."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.core.database import dispose_database
from app.core.security import hash_api_key
from app.main import create_app
from app.models import ExecutionTier, SubscriptionPlan


@dataclass(frozen=True)
class SeededAPIKeyData:
    """Seeded tenant and API key data for API key management tests."""

    tenant_id: uuid.UUID
    management_key_id: uuid.UUID
    management_raw_api_key: str
    secondary_key_id: uuid.UUID
    secondary_raw_api_key: str
    foreign_key_id: uuid.UUID


@pytest.fixture()
def api_key_env(monkeypatch) -> str:
    """Configure a deterministic API key salt for API key tests."""

    salt = "integration-test-api-key-salt"
    monkeypatch.setenv("API_KEY_SALT", salt)
    get_settings.cache_clear()
    yield salt
    get_settings.cache_clear()


@pytest.fixture()
def api_key_client(api_key_env: str) -> TestClient:
    """Create a test client after API key auth settings are configured."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(dispose_database())


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def seeded_api_key_data(api_key_env: str) -> SeededAPIKeyData:
    """Insert tenant-scoped API key rows for management route tests."""

    tenant_id = uuid.uuid4()
    foreign_tenant_id = uuid.uuid4()
    management_key_id = uuid.uuid4()
    secondary_key_id = uuid.uuid4()
    foreign_key_id = uuid.uuid4()
    management_raw_api_key = f"grd_manage_{uuid.uuid4().hex}"
    secondary_raw_api_key = f"grd_secondary_{uuid.uuid4().hex}"
    foreign_raw_api_key = f"grd_foreign_{uuid.uuid4().hex}"

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
                    label,
                    last_used_at
                )
                values
                (%s, %s, %s, %s, %s),
                (%s, %s, %s, %s, %s),
                (%s, %s, %s, %s, %s)
                """,
                (
                    management_key_id,
                    tenant_id,
                    hash_api_key(management_raw_api_key, api_key_env),
                    "management-key",
                    datetime(2026, 3, 20, tzinfo=UTC),
                    secondary_key_id,
                    tenant_id,
                    hash_api_key(secondary_raw_api_key, api_key_env),
                    "secondary-key",
                    None,
                    foreign_key_id,
                    foreign_tenant_id,
                    hash_api_key(foreign_raw_api_key, api_key_env),
                    "foreign-key",
                    None,
                ),
            )

    yield SeededAPIKeyData(
        tenant_id=tenant_id,
        management_key_id=management_key_id,
        management_raw_api_key=management_raw_api_key,
        secondary_key_id=secondary_key_id,
        secondary_raw_api_key=secondary_raw_api_key,
        foreign_key_id=foreign_key_id,
    )

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "delete from api_keys where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            cursor.execute(
                "delete from tenants where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )


def test_api_key_list_requires_authentication(api_key_client: TestClient) -> None:
    """API key listing should reject unauthenticated callers."""

    response = api_key_client.get("/v1/api-keys")

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is required."}


def test_api_key_list_returns_tenant_scoped_metadata(
    api_key_client: TestClient,
    seeded_api_key_data: SeededAPIKeyData,
) -> None:
    """API key listing should only return the authenticated tenant's keys."""

    response = api_key_client.get(
        "/v1/api-keys",
        headers={"X-API-Key": seeded_api_key_data.management_raw_api_key},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert {item["key_id"] for item in payload} == {
        str(seeded_api_key_data.management_key_id),
        str(seeded_api_key_data.secondary_key_id),
    }
    assert all("api_key" not in item for item in payload)


def test_api_key_create_returns_raw_secret_once_and_persists_hash(
    api_key_client: TestClient,
    seeded_api_key_data: SeededAPIKeyData,
    api_key_env: str,
) -> None:
    """API key creation should return the secret once and persist only its hash."""

    response = api_key_client.post(
        "/v1/api-keys",
        headers={"X-API-Key": seeded_api_key_data.management_raw_api_key},
        json={"label": "Frontend Integration"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["label"] == "Frontend Integration"
    assert payload["api_key"].startswith("grd_")
    assert payload["revoked_at"] is None

    created_key_id = uuid.UUID(payload["key_id"])

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select label, key_hash from api_keys where key_id = %s",
                (created_key_id,),
            )
            persisted = cursor.fetchone()

    assert persisted is not None
    assert persisted[0] == "Frontend Integration"
    assert persisted[1] == hash_api_key(payload["api_key"], api_key_env)
    assert persisted[1] != payload["api_key"]


def test_api_key_revoke_is_tenant_scoped_and_blocks_future_authentication(
    api_key_client: TestClient,
    seeded_api_key_data: SeededAPIKeyData,
) -> None:
    """Revoking a tenant key should mark it revoked and block future auth."""

    revoke_response = api_key_client.post(
        f"/v1/api-keys/{seeded_api_key_data.secondary_key_id}/revoke",
        headers={"X-API-Key": seeded_api_key_data.management_raw_api_key},
    )

    assert revoke_response.status_code == 200
    revoke_payload = revoke_response.json()
    assert revoke_payload["key_id"] == str(seeded_api_key_data.secondary_key_id)
    assert revoke_payload["revoked_at"] is not None

    auth_response = api_key_client.get(
        "/v1/auth/smoke",
        headers={"X-API-Key": seeded_api_key_data.secondary_raw_api_key},
    )

    assert auth_response.status_code == 401
    assert auth_response.json() == {"detail": "API key has been revoked."}

    foreign_response = api_key_client.post(
        f"/v1/api-keys/{seeded_api_key_data.foreign_key_id}/revoke",
        headers={"X-API-Key": seeded_api_key_data.management_raw_api_key},
    )

    assert foreign_response.status_code == 404
    assert foreign_response.json() == {"detail": "API key not found for tenant."}
