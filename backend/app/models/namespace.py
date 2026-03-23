"""Namespace persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    ExecutionTier,
    FreshnessProfile,
    SensitivityLevel,
    sqlalchemy_enum,
)

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.query_trace import QueryTrace
    from app.models.tenant import Tenant
    from app.models.workspace import Workspace


class Namespace(Base):
    """Tenant-scoped logical partition for documents and retrieval."""

    __tablename__ = "namespaces"
    __table_args__ = (
        CheckConstraint("char_length(domain) > 0", name="ck_namespaces_domain_non_empty"),
        UniqueConstraint("tenant_id", "name", name="uq_namespaces_tenant_name"),
        UniqueConstraint(
            "tenant_id",
            "namespace_id",
            name="uq_namespaces_tenant_namespace_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "workspace_id"],
            ["workspaces.tenant_id", "workspaces.workspace_id"],
            name="fk_namespaces_tenant_workspace",
        ),
        Index("ix_namespaces_tenant_id", "tenant_id"),
        Index("ix_namespaces_workspace_id", "workspace_id"),
    )

    namespace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        server_default=text("'general'"),
    )
    sensitivity_level: Mapped[SensitivityLevel] = mapped_column(
        sqlalchemy_enum(SensitivityLevel, name="sensitivity_level_enum"),
        nullable=False,
    )
    freshness_profile: Mapped[FreshnessProfile] = mapped_column(
        sqlalchemy_enum(FreshnessProfile, name="freshness_profile_enum"),
        nullable=False,
        server_default=text("'balanced'"),
    )
    min_execution_tier: Mapped[ExecutionTier] = mapped_column(
        sqlalchemy_enum(ExecutionTier, name="execution_tier_enum"),
        nullable=False,
        server_default=text("'standard'"),
    )
    allow_web_fallback: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    allow_internal_model_retrieval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant: Mapped["Tenant"] = relationship(
        back_populates="namespaces",
        foreign_keys=[tenant_id],
    )
    workspace: Mapped["Workspace | None"] = relationship(
        back_populates="namespaces",
        primaryjoin=(
            "and_("
            "Namespace.tenant_id == Workspace.tenant_id, "
            "Namespace.workspace_id == Workspace.workspace_id"
            ")"
        ),
        foreign_keys="[Namespace.tenant_id, Namespace.workspace_id]",
        overlaps="tenant,namespaces",
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="namespace",
        primaryjoin=(
            "and_("
            "Namespace.tenant_id == Document.tenant_id, "
            "Namespace.namespace_id == Document.namespace_id"
            ")"
        ),
        foreign_keys="[Document.tenant_id, Document.namespace_id]",
        overlaps="tenant,documents",
    )
    query_traces: Mapped[list["QueryTrace"]] = relationship(
        back_populates="namespace",
        primaryjoin=(
            "and_("
            "Namespace.tenant_id == QueryTrace.tenant_id, "
            "Namespace.namespace_id == QueryTrace.namespace_id"
            ")"
        ),
        foreign_keys="[QueryTrace.tenant_id, QueryTrace.namespace_id]",
        overlaps="tenant,query_traces",
    )
