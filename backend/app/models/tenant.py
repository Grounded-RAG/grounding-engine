"""Tenant persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, Enum, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PlanTier

if TYPE_CHECKING:
    from app.models.api_key import APIKey
    from app.models.document import Document
    from app.models.ingestion_job import IngestionJob
    from app.models.namespace import Namespace
    from app.models.query_trace import QueryTrace


class Tenant(Base):
    """Top-level tenant boundary for every persisted resource."""

    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint("retention_days >= 1", name="ck_tenants_retention_days_positive"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    plan_tier: Mapped[PlanTier] = mapped_column(
        Enum(PlanTier, name="plan_tier_enum"),
        nullable=False,
    )
    default_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    retention_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("365"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    namespaces: Mapped[list["Namespace"]] = relationship(
        back_populates="tenant",
        foreign_keys="Namespace.tenant_id",
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        back_populates="tenant",
        foreign_keys="APIKey.tenant_id",
    )
    documents: Mapped[list["Document"]] = relationship(
        back_populates="tenant",
        foreign_keys="Document.tenant_id",
    )
    ingestion_jobs: Mapped[list["IngestionJob"]] = relationship(
        back_populates="tenant",
        foreign_keys="IngestionJob.tenant_id",
    )
    query_traces: Mapped[list["QueryTrace"]] = relationship(
        back_populates="tenant",
        foreign_keys="QueryTrace.tenant_id",
    )
