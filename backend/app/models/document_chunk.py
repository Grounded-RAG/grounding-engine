"""Sparse-searchable document chunk persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentChunkRecord(Base):
    """Chunk rows materialized in PostgreSQL for sparse retrieval."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("tenant_id", "chunk_id", name="uq_document_chunks_tenant_chunk_id"),
        UniqueConstraint(
            "tenant_id",
            "doc_id",
            "chunk_index",
            name="uq_document_chunks_tenant_doc_chunk_index",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "namespace_id"],
            ["namespaces.tenant_id", "namespaces.namespace_id"],
            name="fk_document_chunks_tenant_namespace",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "doc_id"],
            ["documents.tenant_id", "documents.doc_id"],
            name="fk_document_chunks_tenant_document",
        ),
        CheckConstraint("chunk_index >= 0", name="ck_document_chunks_chunk_index"),
        CheckConstraint("token_count >= 0", name="ck_document_chunks_token_count"),
        CheckConstraint(
            "character_count >= 0",
            name="ck_document_chunks_character_count",
        ),
        CheckConstraint("start_token >= 0", name="ck_document_chunks_start_token"),
        CheckConstraint("end_token >= start_token", name="ck_document_chunks_token_span"),
        Index("ix_document_chunks_tenant_id", "tenant_id"),
        Index("ix_document_chunks_namespace_id", "namespace_id"),
        Index("ix_document_chunks_doc_id", "doc_id"),
        Index("ix_document_chunks_section_slug", "section_slug"),
        Index(
            "ix_document_chunks_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    chunk_row_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )
    namespace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    doc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    section_slug: Mapped[str | None] = mapped_column(String(256), nullable=True)
    chunk_role: Mapped[str] = mapped_column(String(32), nullable=False, default="body")
    starts_with_heading: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    is_list_block: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english'::regconfig, chunk_text)", persisted=True),
        nullable=False,
    )
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False)
    start_token: Mapped[int] = mapped_column(Integer, nullable=False)
    end_token: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
