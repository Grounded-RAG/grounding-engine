"""Integration tests for run-history routes."""

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
class SeededRunData:
    """Seeded tenant, dataset, and run data for run-history tests."""

    tenant_id: uuid.UUID
    dataset_id: uuid.UUID
    secondary_dataset_id: uuid.UUID
    agent_id: uuid.UUID
    conversation_id: uuid.UUID
    newest_run_id: uuid.UUID
    older_run_id: uuid.UUID
    foreign_run_id: uuid.UUID
    raw_api_key: str


@pytest.fixture()
def run_auth_env(monkeypatch) -> str:
    """Configure a deterministic API key salt for run-history tests."""

    salt = "integration-test-api-key-salt"
    monkeypatch.setenv("API_KEY_SALT", salt)
    get_settings.cache_clear()
    yield salt
    get_settings.cache_clear()


@pytest.fixture()
def run_client(run_auth_env: str) -> TestClient:
    """Create a test client after run-history auth settings are configured."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(dispose_database())


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def seeded_run_data(run_auth_env: str) -> SeededRunData:
    """Insert tenants, datasets, API key, and persisted query traces."""

    tenant_id = uuid.uuid4()
    foreign_tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    foreign_workspace_id = uuid.uuid4()
    dataset_id = uuid.uuid4()
    secondary_dataset_id = uuid.uuid4()
    foreign_dataset_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    foreign_agent_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    foreign_conversation_id = uuid.uuid4()
    newest_run_id = uuid.uuid4()
    older_run_id = uuid.uuid4()
    foreign_run_id = uuid.uuid4()
    raw_api_key = f"grd_runs_{uuid.uuid4().hex}"

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
                insert into workspaces (
                    workspace_id,
                    tenant_id,
                    name,
                    slug,
                    description
                )
                values
                (%s, %s, %s, %s, %s),
                (%s, %s, %s, %s, %s)
                """,
                (
                    workspace_id,
                    tenant_id,
                    "Operations",
                    "operations",
                    "Primary workspace",
                    foreign_workspace_id,
                    foreign_tenant_id,
                    "Foreign",
                    "foreign",
                    "Foreign workspace",
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
                    hash_api_key(raw_api_key, run_auth_env),
                    "integration-runs",
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
                    workspace_id,
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
                    "Grounded ops agent",
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
                    None,
                    "Ops Thread",
                    "instant",
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
                insert into query_traces (
                    trace_id,
                    tenant_id,
                    namespace_id,
                    agent_id,
                    conversation_id,
                    selected_mode,
                    requested_tier,
                    router_recommendation,
                    effective_tier,
                    routing_reason,
                    query_redacted,
                    query_ciphertext,
                    retrieved_chunk_ids,
                    selected_evidence_ids,
                    generator_provider,
                    verifier_result,
                    final_answer_redacted,
                    citations,
                    overall_confidence,
                    degraded_reasons,
                    stage_latencies_ms,
                    total_latency_ms,
                    token_usage,
                    created_at
                )
                values
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, now()),
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, now() - interval '1 minute'),
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, now())
                """,
                (
                    newest_run_id,
                    tenant_id,
                    dataset_id,
                    agent_id,
                    conversation_id,
                    "instant",
                    ExecutionTier.STANDARD.value,
                    ExecutionTier.STANDARD.value,
                    ExecutionTier.STANDARD.value,
                    "standard_default",
                    "What is the maintenance window?",
                    None,
                    json.dumps(["chunk-2"]),
                    json.dumps(["chunk-2"]),
                    "local-grounded-v1",
                    json.dumps({"status": "passed"}),
                    "Maintenance window: Friday at 22:00 UTC. [E001]",
                    json.dumps(
                        [
                            {
                                "citation_id": "E001",
                                "chunk_id": "chunk-2",
                                "document_id": str(uuid.uuid4()),
                                "chunk_index": 0,
                                "quote": "Maintenance window: Friday at 22:00 UTC.",
                            }
                        ]
                    ),
                    0.92,
                    json.dumps([]),
                    json.dumps({"retrieval_ms": 12}),
                    28,
                    json.dumps({"total_tokens": 0}),
                    older_run_id,
                    tenant_id,
                    secondary_dataset_id,
                    None,
                    None,
                    None,
                    ExecutionTier.STANDARD.value,
                    ExecutionTier.STANDARD.value,
                    ExecutionTier.STANDARD.value,
                    "standard_default",
                    "How does the system stay grounded?",
                    None,
                    json.dumps(["chunk-1"]),
                    json.dumps(["chunk-1"]),
                    "local-grounded-v1",
                    json.dumps({"status": "degraded"}),
                    "I could not find grounded evidence for this query.",
                    json.dumps([]),
                    0.0,
                    json.dumps(["NO_GROUNDED_EVIDENCE"]),
                    json.dumps({"retrieval_ms": 8}),
                    19,
                    json.dumps({"total_tokens": 0}),
                    foreign_run_id,
                    foreign_tenant_id,
                    foreign_dataset_id,
                    foreign_agent_id,
                    foreign_conversation_id,
                    "auto",
                    ExecutionTier.STANDARD.value,
                    ExecutionTier.STANDARD.value,
                    ExecutionTier.STANDARD.value,
                    "standard_default",
                    "Foreign question",
                    None,
                    json.dumps(["foreign-chunk"]),
                    json.dumps(["foreign-chunk"]),
                    "local-grounded-v1",
                    json.dumps({"status": "passed"}),
                    "Foreign answer [E001]",
                    json.dumps([]),
                    0.5,
                    json.dumps([]),
                    json.dumps({"retrieval_ms": 4}),
                    11,
                    json.dumps({"total_tokens": 0}),
                ),
            )

    yield SeededRunData(
        tenant_id=tenant_id,
        dataset_id=dataset_id,
        secondary_dataset_id=secondary_dataset_id,
        agent_id=agent_id,
        conversation_id=conversation_id,
        newest_run_id=newest_run_id,
        older_run_id=older_run_id,
        foreign_run_id=foreign_run_id,
        raw_api_key=raw_api_key,
    )

    with psycopg.connect(_sync_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "delete from query_traces where tenant_id in (%s, %s)",
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


def test_run_list_requires_api_key(run_client: TestClient) -> None:
    """Run listing should reject unauthenticated callers."""

    response = run_client.get("/v1/runs")

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is required."}


def test_run_list_returns_recent_runs_and_supports_dataset_filter(
    run_client: TestClient,
    seeded_run_data: SeededRunData,
) -> None:
    """Run listing should stay tenant-scoped, newest first, and dataset-filterable."""

    response = run_client.get(
        "/v1/runs",
        headers={"X-API-Key": seeded_run_data.raw_api_key},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert [item["run_id"] for item in payload] == [
        str(seeded_run_data.newest_run_id),
        str(seeded_run_data.older_run_id),
    ]
    assert payload[0]["dataset_id"] == str(seeded_run_data.dataset_id)
    assert payload[0]["agent_id"] == str(seeded_run_data.agent_id)
    assert payload[0]["conversation_id"] == str(seeded_run_data.conversation_id)
    assert payload[0]["selected_mode"] == "instant"
    assert payload[0]["verification_status"] == "passed"
    assert payload[0]["confidence_label"] == "high"
    assert payload[0]["support_summary"] == "grounded"
    assert payload[1]["dataset_id"] == str(seeded_run_data.secondary_dataset_id)
    assert payload[1]["selected_mode"] is None
    assert payload[1]["verification_status"] == "degraded"
    assert payload[1]["confidence_label"] == "low"
    assert payload[1]["support_summary"] == "insufficient"

    filtered_response = run_client.get(
        "/v1/runs",
        headers={"X-API-Key": seeded_run_data.raw_api_key},
        params={"dataset_id": str(seeded_run_data.dataset_id)},
    )

    assert filtered_response.status_code == 200
    filtered_payload = filtered_response.json()
    assert len(filtered_payload) == 1
    assert filtered_payload[0]["run_id"] == str(seeded_run_data.newest_run_id)


def test_run_get_rejects_foreign_run(
    run_client: TestClient,
    seeded_run_data: SeededRunData,
) -> None:
    """Tenants should not be able to fetch another tenant's run."""

    response = run_client.get(
        f"/v1/runs/{seeded_run_data.foreign_run_id}",
        headers={"X-API-Key": seeded_run_data.raw_api_key},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Run not found for tenant."}


def test_run_get_returns_structured_run_details(
    run_client: TestClient,
    seeded_run_data: SeededRunData,
) -> None:
    """Run detail should project the persisted query trace cleanly."""

    response = run_client.get(
        f"/v1/runs/{seeded_run_data.newest_run_id}",
        headers={"X-API-Key": seeded_run_data.raw_api_key},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == str(seeded_run_data.newest_run_id)
    assert payload["dataset_id"] == str(seeded_run_data.dataset_id)
    assert payload["agent_id"] == str(seeded_run_data.agent_id)
    assert payload["conversation_id"] == str(seeded_run_data.conversation_id)
    assert payload["selected_mode"] == "instant"
    assert payload["requested_tier"] == "standard"
    assert payload["effective_tier"] == "standard"
    assert payload["query"] == "What is the maintenance window?"
    assert payload["answer"] == "Maintenance window: Friday at 22:00 UTC. [E001]"
    assert payload["confidence_score"] == 0.92
    assert payload["confidence_label"] == "high"
    assert payload["support_summary"] == "grounded"
    assert payload["provider_backend"] == "local_grounded_v1"
    assert payload["provider_fallback_used"] is False
    assert payload["citations"][0]["citation_id"] == "E001"
