"""Integration tests for dashboard summary and activity routes."""

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
from app.models import (
    DocumentStatus,
    ExecutionTier,
    FreshnessProfile,
    IngestionJobStatus,
    SensitivityLevel,
    SubscriptionPlan,
)


@dataclass(frozen=True)
class SeededDashboardData:
    """Seeded dashboard data for one authenticated tenant."""

    dataset_id: uuid.UUID
    secondary_dataset_id: uuid.UUID
    newest_run_id: uuid.UUID
    older_run_id: uuid.UUID
    failed_job_id: uuid.UUID
    running_job_id: uuid.UUID
    indexed_job_id: uuid.UUID
    raw_api_key: str


@pytest.fixture()
def dashboard_auth_env(monkeypatch) -> str:
    """Configure a deterministic API key salt for dashboard tests."""

    salt = "integration-test-api-key-salt"
    monkeypatch.setenv("API_KEY_SALT", salt)
    get_settings.cache_clear()
    yield salt
    get_settings.cache_clear()


@pytest.fixture()
def dashboard_client(dashboard_auth_env: str) -> TestClient:
    """Create a test client after dashboard auth settings are configured."""

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(dispose_database())


def _sync_database_url() -> str:
    """Return a sync Postgres URL suitable for psycopg."""

    return get_settings().alembic_database_url.replace("+psycopg", "")


@pytest.fixture()
def seeded_dashboard_data(dashboard_auth_env: str) -> SeededDashboardData:
    """Insert enough tenant-scoped data to exercise dashboard routes."""

    tenant_id = uuid.uuid4()
    foreign_tenant_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    foreign_workspace_id = uuid.uuid4()
    dataset_id = uuid.uuid4()
    secondary_dataset_id = uuid.uuid4()
    foreign_dataset_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    foreign_agent_id = uuid.uuid4()
    primary_conversation_id = uuid.uuid4()
    secondary_conversation_id = uuid.uuid4()
    foreign_conversation_id = uuid.uuid4()
    indexed_document_id = uuid.uuid4()
    running_document_id = uuid.uuid4()
    failed_document_id = uuid.uuid4()
    foreign_document_id = uuid.uuid4()
    indexed_job_id = uuid.uuid4()
    running_job_id = uuid.uuid4()
    failed_job_id = uuid.uuid4()
    foreign_job_id = uuid.uuid4()
    newest_run_id = uuid.uuid4()
    older_run_id = uuid.uuid4()
    foreign_run_id = uuid.uuid4()
    raw_api_key = f"grd_dashboard_{uuid.uuid4().hex}"

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
                    hash_api_key(raw_api_key, dashboard_auth_env),
                    "integration-dashboard",
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
                    "policy-dataset",
                    "policy",
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
                    last_used_mode,
                    created_at,
                    updated_at
                )
                values
                (%s, %s, %s, %s, %s, %s, %s, now() - interval '10 minutes', now() - interval '2 minutes'),
                (%s, %s, %s, %s, %s, %s, %s, now() - interval '5 minutes', now() - interval '1 minute'),
                (%s, %s, %s, %s, %s, %s, %s, now(), now())
                """,
                (
                    primary_conversation_id,
                    tenant_id,
                    workspace_id,
                    agent_id,
                    None,
                    "Ops Thread",
                    "instant",
                    secondary_conversation_id,
                    tenant_id,
                    workspace_id,
                    agent_id,
                    None,
                    "Policy Thread",
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
                insert into documents (
                    doc_id,
                    tenant_id,
                    namespace_id,
                    object_key,
                    source_uri,
                    mime_type,
                    title,
                    checksum,
                    file_size_bytes,
                    status,
                    created_at
                )
                values
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now() - interval '20 minutes'),
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now() - interval '10 minutes'),
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now() - interval '5 minutes'),
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
                """,
                (
                    indexed_document_id,
                    tenant_id,
                    dataset_id,
                    "documents/indexed.txt",
                    None,
                    "text/plain",
                    "Ops Manual",
                    "1" * 64,
                    128,
                    DocumentStatus.INDEXED.value,
                    running_document_id,
                    tenant_id,
                    dataset_id,
                    "documents/running.txt",
                    None,
                    "text/plain",
                    "Incident Playbook",
                    "2" * 64,
                    256,
                    DocumentStatus.PROCESSING.value,
                    failed_document_id,
                    tenant_id,
                    secondary_dataset_id,
                    "documents/failed.txt",
                    None,
                    "text/plain",
                    "Policy Draft",
                    "3" * 64,
                    512,
                    DocumentStatus.FAILED.value,
                    foreign_document_id,
                    foreign_tenant_id,
                    foreign_dataset_id,
                    "documents/foreign.txt",
                    None,
                    "text/plain",
                    "Foreign Manual",
                    "4" * 64,
                    64,
                    DocumentStatus.INDEXED.value,
                ),
            )
            cursor.execute(
                """
                insert into ingestion_jobs (
                    job_id,
                    tenant_id,
                    doc_id,
                    status,
                    attempt_count,
                    error_code,
                    error_detail,
                    started_at,
                    completed_at,
                    created_at
                )
                values
                (%s, %s, %s, %s, %s, %s, %s, now() - interval '3 minutes', now() - interval '2 minutes', now() - interval '2 minutes'),
                (%s, %s, %s, %s, %s, %s, %s, now() - interval '90 seconds', null, now() - interval '1 minute'),
                (%s, %s, %s, %s, %s, %s, %s, now() - interval '20 seconds', now() - interval '10 seconds', now()),
                (%s, %s, %s, %s, %s, %s, %s, now() - interval '30 seconds', null, now())
                """,
                (
                    indexed_job_id,
                    tenant_id,
                    indexed_document_id,
                    IngestionJobStatus.INDEXED.value,
                    1,
                    None,
                    None,
                    running_job_id,
                    tenant_id,
                    running_document_id,
                    IngestionJobStatus.RUNNING.value,
                    1,
                    None,
                    None,
                    failed_job_id,
                    tenant_id,
                    failed_document_id,
                    IngestionJobStatus.FAILED.value,
                    2,
                    "EXTRACTION_FAILED",
                    "Unable to parse uploaded document.",
                    foreign_job_id,
                    foreign_tenant_id,
                    foreign_document_id,
                    IngestionJobStatus.RUNNING.value,
                    1,
                    None,
                    None,
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
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, now() - interval '2 minutes'),
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, now())
                """,
                (
                    newest_run_id,
                    tenant_id,
                    dataset_id,
                    agent_id,
                    primary_conversation_id,
                    "instant",
                    ExecutionTier.STANDARD.value,
                    ExecutionTier.STANDARD.value,
                    ExecutionTier.STANDARD.value,
                    "phase1_standard_query",
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
                                "document_id": str(indexed_document_id),
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
                    "phase1_standard_query",
                    "What changed in the policy draft?",
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
                    "phase1_standard_query",
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

    yield SeededDashboardData(
        dataset_id=dataset_id,
        secondary_dataset_id=secondary_dataset_id,
        newest_run_id=newest_run_id,
        older_run_id=older_run_id,
        failed_job_id=failed_job_id,
        running_job_id=running_job_id,
        indexed_job_id=indexed_job_id,
        raw_api_key=raw_api_key,
    )

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
                "delete from documents where tenant_id in (%s, %s)",
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


def test_dashboard_summary_requires_api_key(dashboard_client: TestClient) -> None:
    """Dashboard summary should reject unauthenticated callers."""

    response = dashboard_client.get("/v1/dashboard/summary")

    assert response.status_code == 401
    assert response.json() == {"detail": "API key is required."}


def test_dashboard_summary_returns_tenant_scoped_counts(
    dashboard_client: TestClient,
    seeded_dashboard_data: SeededDashboardData,
) -> None:
    """Dashboard summary should aggregate only the authenticated tenant."""

    response = dashboard_client.get(
        "/v1/dashboard/summary",
        headers={"X-API-Key": seeded_dashboard_data.raw_api_key},
    )

    assert response.status_code == 200
    assert response.json() == {
        "dataset_count": 2,
        "document_count": 3,
        "indexed_document_count": 1,
        "running_job_count": 1,
        "failed_job_count": 1,
        "agent_count": 1,
        "conversation_count": 2,
    }


def test_dashboard_recent_activity_returns_runs_and_jobs_newest_first(
    dashboard_client: TestClient,
    seeded_dashboard_data: SeededDashboardData,
) -> None:
    """Dashboard activity endpoints should stay tenant-scoped and ordered."""

    headers = {"X-API-Key": seeded_dashboard_data.raw_api_key}

    recent_runs_response = dashboard_client.get(
        "/v1/dashboard/recent-runs",
        headers=headers,
        params={"limit": 1},
    )

    assert recent_runs_response.status_code == 200
    recent_runs_payload = recent_runs_response.json()
    assert len(recent_runs_payload) == 1
    assert recent_runs_payload[0]["run_id"] == str(seeded_dashboard_data.newest_run_id)
    assert recent_runs_payload[0]["dataset_id"] == str(seeded_dashboard_data.dataset_id)
    assert recent_runs_payload[0]["selected_mode"] == "instant"

    recent_jobs_response = dashboard_client.get(
        "/v1/dashboard/recent-jobs",
        headers=headers,
    )

    assert recent_jobs_response.status_code == 200
    recent_jobs_payload = recent_jobs_response.json()
    assert [item["job_id"] for item in recent_jobs_payload] == [
        str(seeded_dashboard_data.failed_job_id),
        str(seeded_dashboard_data.running_job_id),
        str(seeded_dashboard_data.indexed_job_id),
    ]
    assert recent_jobs_payload[0]["dataset_id"] == str(
        seeded_dashboard_data.secondary_dataset_id
    )
    assert recent_jobs_payload[0]["document_title"] == "Policy Draft"
    assert recent_jobs_payload[0]["status"] == "failed"
    assert recent_jobs_payload[0]["error_code"] == "EXTRACTION_FAILED"
