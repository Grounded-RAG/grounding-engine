"""created core models

Revision ID: 903d46f03385
Revises: 
Create Date: 2026-03-18 16:15:26.049311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '903d46f03385'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

plan_tier_enum = postgresql.ENUM(
    'standard',
    'enterprise',
    'critical',
    name='plan_tier_enum',
    create_type=False,
)
sensitivity_level_enum = postgresql.ENUM(
    'public',
    'internal',
    'confidential',
    'restricted',
    name='sensitivity_level_enum',
    create_type=False,
)
document_status_enum = postgresql.ENUM(
    'uploaded',
    'processing',
    'indexed',
    'failed',
    'archived',
    name='document_status_enum',
    create_type=False,
)
ingestion_job_status_enum = postgresql.ENUM(
    'queued',
    'running',
    'indexed',
    'failed',
    'dead_letter',
    name='ingestion_job_status_enum',
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    plan_tier_enum.create(bind, checkfirst=True)
    sensitivity_level_enum.create(bind, checkfirst=True)
    document_status_enum.create(bind, checkfirst=True)
    ingestion_job_status_enum.create(bind, checkfirst=True)

    op.create_table('tenants',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('plan_tier', plan_tier_enum, nullable=False),
    sa.Column('default_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('retention_days', sa.Integer(), server_default=sa.text('365'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('retention_days >= 1', name='ck_tenants_retention_days_positive'),
    sa.PrimaryKeyConstraint('tenant_id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('api_keys',
    sa.Column('key_id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('key_hash', sa.String(length=255), nullable=False),
    sa.Column('label', sa.String(length=255), nullable=False),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ),
    sa.PrimaryKeyConstraint('key_id'),
    sa.UniqueConstraint('key_hash')
    )
    op.create_index('ix_api_keys_tenant_id', 'api_keys', ['tenant_id'], unique=False)
    op.create_table('namespaces',
    sa.Column('namespace_id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('sensitivity_level', sensitivity_level_enum, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ),
    sa.PrimaryKeyConstraint('namespace_id'),
    sa.UniqueConstraint('tenant_id', 'name', name='uq_namespaces_tenant_name'),
    sa.UniqueConstraint('tenant_id', 'namespace_id', name='uq_namespaces_tenant_namespace_id')
    )
    op.create_index('ix_namespaces_tenant_id', 'namespaces', ['tenant_id'], unique=False)
    op.create_table('query_traces',
    sa.Column('trace_id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('tier', plan_tier_enum, nullable=False),
    sa.Column('query_redacted', sa.Text(), nullable=False),
    sa.Column('query_ciphertext', sa.LargeBinary(), nullable=True),
    sa.Column('retrieved_chunk_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('selected_evidence_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('generator_provider', sa.String(length=100), nullable=False),
    sa.Column('verifier_result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('final_answer_redacted', sa.Text(), nullable=False),
    sa.Column('citations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('overall_confidence', sa.Float(), nullable=False),
    sa.Column('degraded_reasons', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('stage_latencies_ms', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('total_latency_ms', sa.Integer(), nullable=False),
    sa.Column('token_usage', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('overall_confidence >= 0 AND overall_confidence <= 1', name='ck_query_traces_overall_confidence'),
    sa.CheckConstraint('total_latency_ms >= 0', name='ck_query_traces_total_latency_non_negative'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ),
    sa.PrimaryKeyConstraint('trace_id')
    )
    op.create_index('ix_query_traces_created_at', 'query_traces', ['created_at'], unique=False)
    op.create_index('ix_query_traces_tenant_created_at', 'query_traces', ['tenant_id', 'created_at'], unique=False)
    op.create_index('ix_query_traces_tenant_id', 'query_traces', ['tenant_id'], unique=False)
    op.create_table('documents',
    sa.Column('doc_id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('namespace_id', sa.UUID(), nullable=False),
    sa.Column('object_key', sa.Text(), nullable=False),
    sa.Column('source_uri', sa.Text(), nullable=True),
    sa.Column('mime_type', sa.String(length=100), nullable=False),
    sa.Column('title', sa.String(length=500), nullable=True),
    sa.Column('checksum', sa.String(length=64), nullable=False),
    sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('version', sa.String(length=100), nullable=True),
    sa.Column('status', document_status_enum, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('file_size_bytes >= 0', name='ck_documents_file_size_non_negative'),
    sa.ForeignKeyConstraint(['namespace_id'], ['namespaces.namespace_id'], ),
    sa.ForeignKeyConstraint(['tenant_id', 'namespace_id'], ['namespaces.tenant_id', 'namespaces.namespace_id'], name='fk_documents_tenant_namespace'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ),
    sa.PrimaryKeyConstraint('doc_id'),
    sa.UniqueConstraint('tenant_id', 'checksum', name='uq_documents_tenant_checksum'),
    sa.UniqueConstraint('tenant_id', 'doc_id', name='uq_documents_tenant_doc_id')
    )
    op.create_index('ix_documents_namespace_id', 'documents', ['namespace_id'], unique=False)
    op.create_index('ix_documents_status', 'documents', ['status'], unique=False)
    op.create_index('ix_documents_tenant_id', 'documents', ['tenant_id'], unique=False)
    op.create_table('ingestion_jobs',
    sa.Column('job_id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('doc_id', sa.UUID(), nullable=False),
    sa.Column('status', ingestion_job_status_enum, nullable=False),
    sa.Column('attempt_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('error_code', sa.String(length=100), nullable=True),
    sa.Column('error_detail', sa.Text(), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('attempt_count >= 0', name='ck_ingestion_jobs_attempt_count'),
    sa.ForeignKeyConstraint(['doc_id'], ['documents.doc_id'], ),
    sa.ForeignKeyConstraint(['tenant_id', 'doc_id'], ['documents.tenant_id', 'documents.doc_id'], name='fk_ingestion_jobs_tenant_document'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id'], ),
    sa.PrimaryKeyConstraint('job_id')
    )
    op.create_index('ix_ingestion_jobs_doc_id', 'ingestion_jobs', ['doc_id'], unique=False)
    op.create_index('ix_ingestion_jobs_status', 'ingestion_jobs', ['status'], unique=False)
    op.create_index('ix_ingestion_jobs_tenant_id', 'ingestion_jobs', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ingestion_jobs_tenant_id', table_name='ingestion_jobs')
    op.drop_index('ix_ingestion_jobs_status', table_name='ingestion_jobs')
    op.drop_index('ix_ingestion_jobs_doc_id', table_name='ingestion_jobs')
    op.drop_table('ingestion_jobs')
    op.drop_index('ix_documents_tenant_id', table_name='documents')
    op.drop_index('ix_documents_status', table_name='documents')
    op.drop_index('ix_documents_namespace_id', table_name='documents')
    op.drop_table('documents')
    op.drop_index('ix_query_traces_tenant_id', table_name='query_traces')
    op.drop_index('ix_query_traces_tenant_created_at', table_name='query_traces')
    op.drop_index('ix_query_traces_created_at', table_name='query_traces')
    op.drop_table('query_traces')
    op.drop_index('ix_namespaces_tenant_id', table_name='namespaces')
    op.drop_table('namespaces')
    op.drop_index('ix_api_keys_tenant_id', table_name='api_keys')
    op.drop_table('api_keys')
    op.drop_table('tenants')

    bind = op.get_bind()
    ingestion_job_status_enum.drop(bind, checkfirst=True)
    document_status_enum.drop(bind, checkfirst=True)
    sensitivity_level_enum.drop(bind, checkfirst=True)
    plan_tier_enum.drop(bind, checkfirst=True)
