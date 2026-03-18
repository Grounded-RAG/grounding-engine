"""Unit tests for Phase 0 model metadata."""

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.orm import configure_mappers

from app.core.database import Base
from app.models import APIKey, Document, IngestionJob, Namespace, QueryTrace, Tenant


def test_model_metadata_registers_all_phase_zero_tables() -> None:
    """The Base metadata should include the expected Phase 0 tables."""

    assert set(Base.metadata.tables) >= {
        "tenants",
        "namespaces",
        "api_keys",
        "documents",
        "ingestion_jobs",
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


def test_document_enforces_tenant_safe_constraints() -> None:
    """Documents should enforce checksum uniqueness and tenant-namespace pairing."""

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

    assert "uq_documents_tenant_checksum" in unique_constraints
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


def test_tenant_relationships_cover_all_phase_zero_children() -> None:
    """Tenant should expose the core Phase 0 relationships."""

    relationship_names = set(Tenant.__mapper__.relationships.keys())

    assert relationship_names >= {
        "namespaces",
        "api_keys",
        "documents",
        "ingestion_jobs",
        "query_traces",
    }


def test_api_key_relationship_points_to_tenant() -> None:
    """API keys should resolve back to their owning tenant."""

    assert APIKey.__mapper__.relationships["tenant"].mapper.class_ is Tenant
