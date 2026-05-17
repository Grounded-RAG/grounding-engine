"""Unit tests for Phase 0 model metadata."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import configure_mappers

from app.core.database import Base
from app.models import (
    APIKey,
    Agent,
    AgentDataset,
    Conversation,
    Document,
    DocumentChunkRecord,
    IngestionJob,
    Message,
    Namespace,
    QueryTrace,
    Tenant,
    Workspace,
)


def test_model_metadata_registers_all_phase_zero_tables() -> None:
    """The Base metadata should include the expected Phase 0 tables."""

    assert set(Base.metadata.tables) >= {
        "tenants",
        "namespaces",
        "workspaces",
        "agents",
        "conversations",
        "agent_datasets",
        "api_keys",
        "documents",
        "document_chunks",
        "ingestion_jobs",
        "messages",
        "query_traces",
    }


def test_model_mappers_configure_without_ambiguity() -> None:
    """Relationship wiring should configure cleanly for SQLAlchemy."""

    configure_mappers()


def test_namespace_enforces_tenant_scoped_uniqueness() -> None:
    """Namespaces should be unique per tenant and support composite tenant FKs."""

    unique_constraints = {
        constraint.name
        for constraint in Namespace.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_namespaces_tenant_name" in unique_constraints
    assert "uq_namespaces_tenant_namespace_id" in unique_constraints

    foreign_key_constraints = {
        constraint.name
        for constraint in Namespace.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    assert "fk_namespaces_tenant_workspace" in foreign_key_constraints


def test_document_enforces_tenant_safe_constraints() -> None:
    """Documents should enforce dataset-scoped checksum uniqueness safely."""

    unique_constraints = {
        constraint.name
        for constraint in Document.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    foreign_key_constraints = {
        constraint.name
        for constraint in Document.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    assert "uq_documents_tenant_namespace_checksum" in unique_constraints
    assert "uq_documents_tenant_doc_id" in unique_constraints
    assert "fk_documents_tenant_namespace" in foreign_key_constraints


def test_ingestion_job_enforces_tenant_document_pairing() -> None:
    """Ingestion jobs should inherit tenant safety from their document link."""

    foreign_key_constraints = {
        constraint.name
        for constraint in IngestionJob.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    assert "fk_ingestion_jobs_tenant_document" in foreign_key_constraints


def test_query_trace_has_guardrail_constraints() -> None:
    """Query traces should enforce confidence and latency bounds."""

    check_constraints = {
        constraint.name
        for constraint in QueryTrace.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_query_traces_overall_confidence" in check_constraints
    assert "ck_query_traces_total_latency_non_negative" in check_constraints

    foreign_key_constraints = {
        constraint.name
        for constraint in QueryTrace.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    assert "fk_query_traces_tenant_namespace" in foreign_key_constraints
    assert "fk_query_traces_tenant_agent" in foreign_key_constraints
    assert "fk_query_traces_tenant_conversation" in foreign_key_constraints


def test_document_chunk_record_has_sparse_index_constraints() -> None:
    """Document chunk rows should enforce tenant-safe sparse indexing invariants."""

    unique_constraints = {
        constraint.name
        for constraint in DocumentChunkRecord.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    foreign_key_constraints = {
        constraint.name
        for constraint in DocumentChunkRecord.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    check_constraints = {
        constraint.name
        for constraint in DocumentChunkRecord.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "uq_document_chunks_tenant_chunk_id" in unique_constraints
    assert "uq_document_chunks_tenant_doc_chunk_index" in unique_constraints
    assert "fk_document_chunks_tenant_namespace" in foreign_key_constraints
    assert "fk_document_chunks_tenant_document" in foreign_key_constraints
    assert {
        "ck_document_chunks_chunk_index",
        "ck_document_chunks_token_count",
        "ck_document_chunks_character_count",
        "ck_document_chunks_start_token",
        "ck_document_chunks_token_span",
    } <= check_constraints

    column_names = set(DocumentChunkRecord.__table__.c.keys())
    assert {
        "section_title",
        "section_slug",
        "chunk_role",
        "starts_with_heading",
        "is_list_block",
    } <= column_names


def test_namespace_exposes_policy_columns() -> None:
    """Namespaces should carry explicit routing and policy fields."""

    column_names = set(Namespace.__table__.c.keys())

    assert {
        "workspace_id",
        "domain",
        "freshness_profile",
        "min_execution_tier",
        "allow_web_fallback",
        "allow_internal_model_retrieval",
    } <= column_names


def test_workspace_enforces_tenant_scoped_uniqueness() -> None:
    """Workspaces should be unique per tenant by both name and slug."""

    unique_constraints = {
        constraint.name
        for constraint in Workspace.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    check_constraints = {
        constraint.name
        for constraint in Workspace.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "uq_workspaces_tenant_name" in unique_constraints
    assert "uq_workspaces_tenant_slug" in unique_constraints
    assert "uq_workspaces_tenant_workspace_id" in unique_constraints
    assert "ck_workspaces_name_non_empty" in check_constraints
    assert "ck_workspaces_slug_non_empty" in check_constraints


def test_agent_and_attachment_constraints_are_tenant_safe() -> None:
    """Agents and agent-dataset attachments should enforce scoped uniqueness."""

    agent_unique_constraints = {
        constraint.name
        for constraint in Agent.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    agent_foreign_key_constraints = {
        constraint.name
        for constraint in Agent.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    attachment_unique_constraints = {
        constraint.name
        for constraint in AgentDataset.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    attachment_foreign_key_constraints = {
        constraint.name
        for constraint in AgentDataset.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }

    assert "uq_agents_workspace_name" in agent_unique_constraints
    assert "uq_agents_tenant_agent_id" in agent_unique_constraints
    assert "fk_agents_tenant_workspace" in agent_foreign_key_constraints
    assert "uq_agent_datasets_tenant_agent_dataset" in attachment_unique_constraints
    assert "fk_agent_datasets_tenant_agent" in attachment_foreign_key_constraints
    assert "fk_agent_datasets_tenant_dataset" in attachment_foreign_key_constraints


def test_conversation_constraints_are_tenant_safe() -> None:
    """Conversations should remain scoped to tenant, workspace, and agent."""

    unique_constraints = {
        constraint.name
        for constraint in Conversation.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    foreign_key_constraints = {
        constraint.name
        for constraint in Conversation.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    check_constraints = {
        constraint.name
        for constraint in Conversation.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "uq_conversations_tenant_conversation_id" in unique_constraints
    assert "fk_conversations_tenant_workspace" in foreign_key_constraints
    assert "fk_conversations_tenant_agent" in foreign_key_constraints
    assert "ck_conversations_title_non_empty" in check_constraints


def test_message_constraints_are_tenant_safe() -> None:
    """Messages should remain scoped to tenant and conversation."""

    unique_constraints = {
        constraint.name
        for constraint in Message.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    foreign_key_constraints = {
        constraint.name
        for constraint in Message.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }
    check_constraints = {
        constraint.name
        for constraint in Message.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "uq_messages_tenant_message_id" in unique_constraints
    assert "fk_messages_tenant_conversation" in foreign_key_constraints
    assert "ck_messages_content_non_empty" in check_constraints


def test_query_trace_exposes_routing_columns() -> None:
    """Query traces should capture routing metadata explicitly."""

    column_names = set(QueryTrace.__table__.c.keys())

    assert {
        "namespace_id",
        "agent_id",
        "conversation_id",
        "selected_mode",
        "requested_tier",
        "router_recommendation",
        "effective_tier",
        "routing_reason",
    } <= column_names


def test_tenant_relationships_cover_all_phase_zero_children() -> None:
    """Tenant should expose the core Phase 0 relationships."""

    relationship_names = set(Tenant.__mapper__.relationships.keys())

    assert relationship_names >= {
        "namespaces",
        "api_keys",
        "documents",
        "ingestion_jobs",
        "query_traces",
        "workspaces",
        "agents",
        "conversations",
        "messages",
    }


def test_api_key_relationship_points_to_tenant() -> None:
    """API keys should resolve back to their owning tenant."""

    assert APIKey.__mapper__.relationships["tenant"].mapper.class_ is Tenant


def test_enums_persist_design_doc_values() -> None:
    """Persisted enum values should match the lowercase design-doc contract."""

    assert Tenant.__table__.c.subscription_plan.type.enums == [
        "free",
        "pro",
        "business",
        "enterprise",
    ]
    assert Tenant.__table__.c.max_execution_tier.type.enums == [
        "standard",
        "enterprise",
        "critical",
    ]
    assert Namespace.__table__.c.sensitivity_level.type.enums == [
        "public",
        "internal",
        "confidential",
        "restricted",
    ]
    assert Namespace.__table__.c.freshness_profile.type.enums == [
        "stable",
        "balanced",
        "aggressive",
    ]
    assert Namespace.__table__.c.min_execution_tier.type.enums == [
        "standard",
        "enterprise",
        "critical",
    ]
    assert QueryTrace.__table__.c.router_recommendation.type.enums == [
        "standard",
        "enterprise",
        "critical",
    ]
    assert QueryTrace.__table__.c.effective_tier.type.enums == [
        "standard",
        "enterprise",
        "critical",
    ]
    assert QueryTrace.__table__.c.selected_mode.type.enums == [
        "auto",
        "instant",
        "thinking",
        "verified",
    ]
    assert Document.__table__.c.status.type.enums == [
        "uploaded",
        "processing",
        "indexed",
        "failed",
        "archived",
    ]
    assert IngestionJob.__table__.c.status.type.enums == [
        "queued",
        "running",
        "indexed",
        "failed",
        "dead_letter",
    ]
    assert Agent.__table__.c.default_mode.type.enums == [
        "auto",
        "instant",
        "thinking",
        "verified",
    ]
    assert Agent.__table__.c.status.type.enums == [
        "active",
        "archived",
    ]
    assert Message.__table__.c.role.type.enums == [
        "user",
        "assistant",
        "system",
    ]
