"""Workspace persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.namespace import Namespace
    from app.models.tenant import Tenant


class Workspace(Base):
    """Tenant-scoped workspace used by the future product shell."""

    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("char_length(name) > 0", name="ck_workspaces_name_non_empty"),
        CheckConstraint("char_length(slug) > 0", name="ck_workspaces_slug_non_empty"),
        UniqueConstraint("tenant_id", "name", name="uq_workspaces_tenant_name"),
        UniqueConstraint("tenant_id", "slug", name="uq_workspaces_tenant_slug"),
        UniqueConstraint(
            "tenant_id",
            "workspace_id",
            name="uq_workspaces_tenant_workspace_id",
        ),
        Index("ix_workspaces_tenant_id", "tenant_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped["Tenant"] = relationship(
        back_populates="workspaces",
        foreign_keys=[tenant_id],
    )
    namespaces: Mapped[list["Namespace"]] = relationship(
        back_populates="workspace",
        primaryjoin=(
            "and_("
            "Workspace.tenant_id == Namespace.tenant_id, "
            "Workspace.workspace_id == Namespace.workspace_id"
            ")"
        ),
        foreign_keys="[Namespace.tenant_id, Namespace.workspace_id]",
        overlaps="tenant,namespaces",
    )
