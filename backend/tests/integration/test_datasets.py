"""Integration tests for dataset product APIs."""

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
from app.core.storage import StorageError, delete_object
from app.main import create_app
from app.models import ExecutionTier, FreshnessProfile, SensitivityLevel, SubscriptionPlan


@dataclass(frozen=True)
class SeededDatasetData:
    """Seeded tenant, workspace, and dataset data for dataset route tests."""

    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    secondary_workspace_id: uuid.UUID
    existing_dataset_id: uuid.UUID
    foreign_workspace_id: uuid.UUID
    foreign_dataset_id: uuid.UUID
    raw_api_key: str


@pytest.fixture()
def dataset_auth_env(monkeypatch) -> str:
    """Configure a deterministic API key salt for dataset route tests."""

    salt = "integration-test-api-key-salt"
    monkeypatch.setenv("API_KEY_SALT", salt)
    monkeypatch.setenv("INGESTION_AUTORUN_ENABLED", "false")
    get_settings.cache_clear()
    yield salt
    get_settings.cache_clear()


@pytest.fixture()
def dataset_client(dataset_auth_env: str) -> TestClient:
    """Create a test client after dataset settings are configured."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(dispose_database())


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def seeded_dataset_data(dataset_auth_env: str) -> SeededDatasetData:
    """Insert tenants, workspaces, datasets, and API keys used by dataset tests."""

    tenant_id = uuid.uuid4()
    foreign_tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    secondary_workspace_id = uuid.uuid4()
    foreign_workspace_id = uuid.uuid4()
    existing_dataset_id = uuid.uuid4()
    foreign_dataset_id = uuid.uuid4()
    raw_api_key = f"grd_dataset_{uuid.uuid4().hex}"

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
                    SubscriptionPlan.PRO.value,
                    ExecutionTier.ENTERPRISE.value,
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
                    hash_api_key(raw_api_key, dataset_auth_env),
                    "integration-dataset",
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
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    existing_dataset_id,
                    tenant_id,
                    workspace_id,
                    "operations-dataset",
                    "general",
                    SensitivityLevel.INTERNAL.value,
                    FreshnessProfile.BALANCED.value,
                    ExecutionTier.STANDARD.value,
                    False,
                    False,
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
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
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

    yield SeededDatasetData(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        secondary_workspace_id=secondary_workspace_id,
        existing_dataset_id=existing_dataset_id,
        foreign_workspace_id=foreign_workspace_id,
        foreign_dataset_id=foreign_dataset_id,
        raw_api_key=raw_api_key,
    )

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select object_key from documents where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            object_keys = [row[0] for row in cursor.fetchall()]

    for object_key in object_keys:
        try:
            asyncio.run(delete_object(object_key))
        except StorageError:
            pass

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "delete from query_traces where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            cursor.execute(
                "delete from ingestion_jobs where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            cursor.execute(
                "delete from document_chunks where tenant_id in (%s, %s)",
                (tenant_id, foreign_tenant_id),
            )
            cursor.execute(
                "delete from documents where tenant_id in (%s, %s)",
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


def test_dataset_create_requires_api_key(dataset_client: TestClient) -> None:
    """Dataset creation should reject unauthenticated callers."""

    response = dataset_client.post(
        "/v1/datasets",
        json={
            "workspace_id": str(uuid.uuid4()),
            "name": "operations",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is required."}


def test_dataset_create_rejects_foreign_workspace(
    dataset_client: TestClient,
    seeded_dataset_data: SeededDatasetData,
) -> None:
    """Datasets should not be creatable in another tenant's workspace."""

    response = dataset_client.post(
        "/v1/datasets",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
        json={
            "workspace_id": str(seeded_dataset_data.foreign_workspace_id),
            "name": "bad-dataset",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Workspace not found for tenant."}


def test_dataset_create_and_list_support_workspace_filter(
    dataset_client: TestClient,
    seeded_dataset_data: SeededDatasetData,
) -> None:
    """Datasets should be creatable and listable by workspace."""

    response = dataset_client.post(
        "/v1/datasets",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
        json={
            "workspace_id": str(seeded_dataset_data.secondary_workspace_id),
            "name": "research-dataset",
            "domain": "research",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["workspace_id"] == str(seeded_dataset_data.secondary_workspace_id)
    assert created["name"] == "research-dataset"
    assert created["domain"] == "research"

    list_response = dataset_client.get(
        "/v1/datasets",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
        params={"workspace_id": str(seeded_dataset_data.secondary_workspace_id)},
    )

    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["dataset_id"] == created["dataset_id"]


def test_dataset_get_rejects_foreign_dataset(
    dataset_client: TestClient,
    seeded_dataset_data: SeededDatasetData,
) -> None:
    """Tenants should not be able to fetch another tenant's dataset."""

    response = dataset_client.get(
        f"/v1/datasets/{seeded_dataset_data.foreign_dataset_id}",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Dataset not found for tenant."}


def test_dataset_patch_updates_workspace_and_policy_fields(
    dataset_client: TestClient,
    seeded_dataset_data: SeededDatasetData,
) -> None:
    """Dataset patch should support moving workspaces and updating policy fields."""

    response = dataset_client.patch(
        f"/v1/datasets/{seeded_dataset_data.existing_dataset_id}",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
        json={
            "workspace_id": str(seeded_dataset_data.secondary_workspace_id),
            "domain": "operations",
            "min_execution_tier": "enterprise",
            "allow_web_fallback": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == str(seeded_dataset_data.secondary_workspace_id)
    assert payload["domain"] == "operations"
    assert payload["min_execution_tier"] == "enterprise"
    assert payload["allow_web_fallback"] is True


def test_dataset_upload_lists_documents_and_jobs(
    dataset_client: TestClient,
    seeded_dataset_data: SeededDatasetData,
) -> None:
    """Dataset upload should create records visible through dataset document and job APIs."""

    response = dataset_client.post(
        f"/v1/datasets/{seeded_dataset_data.existing_dataset_id}/upload",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
        data={"title": "Dataset Manual"},
        files={"file": ("manual.txt", b"hello grounded dataset", "text/plain")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["already_exists"] is False
    assert payload["dataset_id"] == str(seeded_dataset_data.existing_dataset_id)
    assert payload["document_status"] == "uploaded"
    assert payload["job_status"] == "queued"

    documents_response = dataset_client.get(
        f"/v1/datasets/{seeded_dataset_data.existing_dataset_id}/documents",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
    )
    assert documents_response.status_code == 200
    documents_payload = documents_response.json()
    assert len(documents_payload) == 1
    assert documents_payload[0]["dataset_id"] == str(seeded_dataset_data.existing_dataset_id)
    assert documents_payload[0]["title"] == "Dataset Manual"

    jobs_response = dataset_client.get(
        f"/v1/datasets/{seeded_dataset_data.existing_dataset_id}/ingestion-jobs",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
    )
    assert jobs_response.status_code == 200
    jobs_payload = jobs_response.json()
    assert len(jobs_payload) == 1
    assert jobs_payload[0]["dataset_id"] == str(seeded_dataset_data.existing_dataset_id)
    assert jobs_payload[0]["document_id"] == payload["document_id"]
    assert jobs_payload[0]["status"] == "queued"


def test_dataset_upload_is_idempotent_for_duplicate_content(
    dataset_client: TestClient,
    seeded_dataset_data: SeededDatasetData,
) -> None:
    """Uploading the same bytes twice into one dataset should reuse the existing records."""

    payload = b"duplicate dataset handbook"

    first_response = dataset_client.post(
        f"/v1/datasets/{seeded_dataset_data.existing_dataset_id}/upload",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
        data={"title": "Dataset Manual"},
        files={"file": ("manual.txt", payload, "text/plain")},
    )

    assert first_response.status_code == 201
    assert first_response.json()["already_exists"] is False

    duplicate_response = dataset_client.post(
        f"/v1/datasets/{seeded_dataset_data.existing_dataset_id}/upload",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
        data={"title": "Dataset Manual Copy"},
        files={"file": ("manual-copy.txt", payload, "text/plain")},
    )

    assert duplicate_response.status_code == 200
    duplicate_payload = duplicate_response.json()
    assert duplicate_payload["already_exists"] is True
    assert duplicate_payload["dataset_id"] == str(seeded_dataset_data.existing_dataset_id)
    assert duplicate_payload["document_id"] == first_response.json()["document_id"]
    assert duplicate_payload["job_id"] == first_response.json()["job_id"]


def test_dataset_upload_allows_same_content_in_different_datasets(
    dataset_client: TestClient,
    seeded_dataset_data: SeededDatasetData,
) -> None:
    """The same file bytes should be accepted in different datasets for the same tenant."""

    create_dataset_response = dataset_client.post(
        "/v1/datasets",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
        json={
            "workspace_id": str(seeded_dataset_data.secondary_workspace_id),
            "name": "shared-content-dataset",
        },
    )

    assert create_dataset_response.status_code == 201
    second_dataset_id = create_dataset_response.json()["dataset_id"]

    payload = b"shared tenant content"

    first_upload = dataset_client.post(
        f"/v1/datasets/{seeded_dataset_data.existing_dataset_id}/upload",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
        files={"file": ("shared.txt", payload, "text/plain")},
    )
    second_upload = dataset_client.post(
        f"/v1/datasets/{second_dataset_id}/upload",
        headers={"X-API-Key": seeded_dataset_data.raw_api_key},
        files={"file": ("shared.txt", payload, "text/plain")},
    )

    assert first_upload.status_code == 201
    assert second_upload.status_code == 201
    assert first_upload.json()["already_exists"] is False
    assert second_upload.json()["already_exists"] is False
    assert first_upload.json()["document_id"] != second_upload.json()["document_id"]
