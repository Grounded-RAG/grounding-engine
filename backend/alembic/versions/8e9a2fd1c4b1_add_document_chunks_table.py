"""add document chunks table

Revision ID: 8e9a2fd1c4b1
Revises: 4f5f0dfc3f2a
Create Date: 2026-03-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8e9a2fd1c4b1"
down_revision: Union[str, Sequence[str], None] = "4f5f0dfc3f2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("chunk_row_id", sa.UUID(), nullable=False),
        sa.Column("chunk_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("namespace_id", sa.UUID(), nullable=False),
        sa.Column("doc_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english'::regconfig, chunk_text)", persisted=True),
            nullable=False,
        ),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("start_token", sa.Integer(), nullable=False),
        sa.Column("end_token", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("chunk_index >= 0", name="ck_document_chunks_chunk_index"),
        sa.CheckConstraint("token_count >= 0", name="ck_document_chunks_token_count"),
        sa.CheckConstraint(
            "character_count >= 0",
            name="ck_document_chunks_character_count",
        ),
        sa.CheckConstraint("start_token >= 0", name="ck_document_chunks_start_token"),
        sa.CheckConstraint(
            "end_token >= start_token",
            name="ck_document_chunks_token_span",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.ForeignKeyConstraint(
            ["tenant_id", "namespace_id"],
            ["namespaces.tenant_id", "namespaces.namespace_id"],
            name="fk_document_chunks_tenant_namespace",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "doc_id"],
            ["documents.tenant_id", "documents.doc_id"],
            name="fk_document_chunks_tenant_document",
        ),
        sa.PrimaryKeyConstraint("chunk_row_id"),
        sa.UniqueConstraint(
            "tenant_id",
            "chunk_id",
            name="uq_document_chunks_tenant_chunk_id",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "doc_id",
            "chunk_index",
            name="uq_document_chunks_tenant_doc_chunk_index",
        ),
    )
    op.create_index(
        "ix_document_chunks_tenant_id",
        "document_chunks",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_namespace_id",
        "document_chunks",
        ["namespace_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_doc_id",
        "document_chunks",
        ["doc_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_chunks_search_vector",
        "document_chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_search_vector", table_name="document_chunks")
    op.drop_index("ix_document_chunks_doc_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_namespace_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_tenant_id", table_name="document_chunks")
    op.drop_table("document_chunks")
