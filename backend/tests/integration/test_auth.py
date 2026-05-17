"""Integration tests for API key authentication and tenant resolution."""

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
from app.core.telemetry import REQUEST_ID_HEADER
from app.main import create_app
from app.models import ExecutionTier, SubscriptionPlan


@dataclass(frozen=True)
class SeededAuthData:
    """Seeded API key data for auth integration tests."""

    tenant_id: uuid.UUID
    tenant_name: str
    valid_key_id: uuid.UUID
    valid_raw_api_key: str
    revoked_raw_api_key: str


@pytest.fixture()
def auth_env(monkeypatch) -> str:
    """Configure a deterministic API key salt for auth tests."""

    salt = "integration-test-api-key-salt"
    monkeypatch.setenv("API_KEY_SALT", salt)
    get_settings.cache_clear()
    yield salt
    get_settings.cache_clear()


@pytest.fixture()
def auth_client(auth_env: str) -> TestClient:
    """Create a test client after auth-related settings are configured."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(dispose_database())


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def seeded_auth_data(auth_env: str) -> SeededAuthData:
    """Insert tenant and API key rows used by auth route tests."""

    tenant_id = uuid.uuid4()
    tenant_name = f"tenant-{tenant_id}"
    valid_key_id = uuid.uuid4()
    revoked_key_id = uuid.uuid4()
    valid_raw_api_key = f"grd_valid_{uuid.uuid4().hex}"
    revoked_raw_api_key = f"grd_revoked_{uuid.uuid4().hex}"

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
                    tenant_name,
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
                    valid_key_id,
                    tenant_id,
                    hash_api_key(valid_raw_api_key, auth_env),
                    "integration-valid",
                ),
            )
            cursor.execute(
                """
                insert into api_keys (
                    key_id,
                    tenant_id,
                    key_hash,
                    label,
                    revoked_at
                )
                values (%s, %s, %s, %s, %s)
                """,
                (
                    revoked_key_id,
                    tenant_id,
                    hash_api_key(revoked_raw_api_key, auth_env),
                    "integration-revoked",
                    datetime.now(UTC),
                ),
            )

    yield SeededAuthData(
        tenant_id=tenant_id,
        tenant_name=tenant_name,
        valid_key_id=valid_key_id,
        valid_raw_api_key=valid_raw_api_key,
        revoked_raw_api_key=revoked_raw_api_key,
    )

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "delete from api_keys where tenant_id = %s",
                (tenant_id,),
            )
            cursor.execute(
                "delete from tenants where tenant_id = %s",
                (tenant_id,),
            )


def test_auth_smoke_requires_api_key(auth_client: TestClient) -> None:
    """Authenticated smoke route should reject requests without an API key."""

    response = auth_client.get("/v1/auth/smoke")

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is required."}


def test_auth_smoke_rejects_unknown_api_key(auth_client: TestClient) -> None:
    """Authenticated smoke route should reject unknown API keys."""

    response = auth_client.get(
        "/v1/auth/smoke",
        headers={"X-API-Key": "grd_unknown_key"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is invalid."}


def test_auth_smoke_rejects_revoked_api_key(
    auth_client: TestClient,
    seeded_auth_data: SeededAuthData,
) -> None:
    """Revoked API keys should no longer authenticate."""

    response = auth_client.get(
        "/v1/auth/smoke",
        headers={"X-API-Key": seeded_auth_data.revoked_raw_api_key},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "API key has been revoked."}


def test_auth_smoke_returns_resolved_tenant_context(
    auth_client: TestClient,
    seeded_auth_data: SeededAuthData,
) -> None:
    """Valid API keys should resolve the tenant context for the request."""

    response = auth_client.get(
        "/v1/auth/smoke",
        headers={"X-API-Key": seeded_auth_data.valid_raw_api_key},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "authenticated",
        "tenant_id": str(seeded_auth_data.tenant_id),
        "tenant_name": seeded_auth_data.tenant_name,
        "subscription_plan": "free",
        "max_execution_tier": "standard",
        "api_key_id": str(seeded_auth_data.valid_key_id),
        "api_key_label": "integration-valid",
    }


def test_auth_smoke_updates_api_key_last_used_at(
    auth_client: TestClient,
    seeded_auth_data: SeededAuthData,
) -> None:
    """Successful authentication should update the API key last-used timestamp."""

    response = auth_client.get(
        "/v1/auth/smoke",
        headers={"X-API-Key": seeded_auth_data.valid_raw_api_key},
    )

    assert response.status_code == 200

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select last_used_at from api_keys where key_id = %s",
                (seeded_auth_data.valid_key_id,),
            )
            row = cursor.fetchone()

    assert row is not None
    assert row[0] is not None


def test_auth_smoke_preserves_request_id_header(
    auth_client: TestClient,
    seeded_auth_data: SeededAuthData,
) -> None:
    """Authenticated routes should preserve the request ID header."""

    response = auth_client.get(
        "/v1/auth/smoke",
        headers={
            "X-API-Key": seeded_auth_data.valid_raw_api_key,
            REQUEST_ID_HEADER: "req-auth-123",
        },
    )

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "req-auth-123"


def test_email_sign_up_and_sign_in_work_with_password_auth(
    auth_client: TestClient,
) -> None:
    """Email/password auth should support sign-up followed by sign-in."""

    email = f"preview-{uuid.uuid4().hex[:10]}@example.com"
    tenant_id: uuid.UUID | None = None
    password = "preview-pass-123"

    try:
        sign_up_response = auth_client.post(
            "/v1/auth/email/sign-up",
            json={
                "email": email,
                "password": password,
                "full_name": "Samra Demo",
                "organization_name": "Grounded Preview Org",
                "workspace_name": "Grounded Preview Workspace",
            },
        )

        assert sign_up_response.status_code == 200
        payload = sign_up_response.json()
        tenant_id = uuid.UUID(payload["tenant_id"])

        assert payload["status"] == "authenticated"
        assert payload["tenant_name"] == "Grounded Preview Org"
        assert payload["subscription_plan"] == "free"
        assert payload["max_execution_tier"] == "standard"
        assert payload["workspace_name"] == "Grounded Preview Workspace"
        assert payload["workspace_slug"] == "grounded-preview-workspace"
        assert payload["created_tenant"] is True
        assert payload["created_workspace"] is True
        assert payload["api_key"].startswith("grd_")

        sign_in_response = auth_client.post(
            "/v1/auth/email/sign-in",
            json={
                "email": email,
                "password": password,
            },
        )

        assert sign_in_response.status_code == 200
        sign_in_payload = sign_in_response.json()
        assert sign_in_payload["tenant_id"] == payload["tenant_id"]
        assert sign_in_payload["workspace_id"] == payload["workspace_id"]
        assert sign_in_payload["created_tenant"] is False
        assert sign_in_payload["created_workspace"] is False

        smoke_response = auth_client.get(
            "/v1/auth/smoke",
            headers={"X-API-Key": sign_in_payload["api_key"]},
        )

        assert smoke_response.status_code == 200
        assert smoke_response.json()["tenant_id"] == payload["tenant_id"]
        assert smoke_response.json()["tenant_name"] == payload["tenant_name"]
    finally:
        if tenant_id is not None:
            with psycopg.connect(_sync_database_url()) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("delete from workspaces where tenant_id = %s", (tenant_id,))
                    cursor.execute("delete from api_keys where tenant_id = %s", (tenant_id,))
                    cursor.execute("delete from tenants where tenant_id = %s", (tenant_id,))
