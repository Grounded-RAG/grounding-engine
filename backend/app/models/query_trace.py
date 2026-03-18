"""Query trace persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PlanTier, sqlalchemy_enum

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class QueryTrace(Base):
    """Trace and provenance record for a grounded query."""

    __tablename__ = "query_traces"
    __table_args__ = (
        CheckConstraint(
            "overall_confidence >= 0 AND overall_confidence <= 1",
            name="ck_query_traces_overall_confidence",
        ),
        CheckConstraint(
            "total_latency_ms >= 0",
            name="ck_query_traces_total_latency_non_negative",
        ),
        Index("ix_query_traces_tenant_id", "tenant_id"),
        Index("ix_query_traces_created_at", "created_at"),
        Index("ix_query_traces_tenant_created_at", "tenant_id", "created_at"),
    )

    trace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )
    tier: Mapped[PlanTier] = mapped_column(
        sqlalchemy_enum(PlanTier, name="plan_tier_enum"),
        nullable=False,
    )
    query_redacted: Mapped[str] = mapped_column(Text, nullable=False)
    query_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    selected_evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    generator_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    verifier_result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    final_answer_redacted: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    overall_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    degraded_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    stage_latencies_ms: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    total_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant: Mapped["Tenant"] = relationship(
        back_populates="query_traces",
        foreign_keys=[tenant_id],
    )
