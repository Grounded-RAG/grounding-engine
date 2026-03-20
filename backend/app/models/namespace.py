"""Namespace persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import SensitivityLevel, sqlalchemy_enum

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.tenant import Tenant


class Namespace(Base):
    """Tenant-scoped logical partition for documents and retrieval."""

    __tablename__ = "namespaces"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_namespaces_tenant_name"),
        UniqueConstraint(
            "tenant_id",
            "namespace_id",
            name="uq_namespaces_tenant_namespace_id",
        ),
        Index("ix_namespaces_tenant_id", "tenant_id"),
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sensitivity_level: Mapped[SensitivityLevel] = mapped_column(
        sqlalchemy_enum(SensitivityLevel, name="sensitivity_level_enum"),
        nullable=False,
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
