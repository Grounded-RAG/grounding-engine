"""Agent-to-dataset attachment model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Index, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.namespace import Namespace
    from app.models.tenant import Tenant


class AgentDataset(Base):
    """Attachment between one agent and one dataset."""

    __tablename__ = "agent_datasets"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "agent_id",
            "dataset_id",
            name="uq_agent_datasets_tenant_agent_dataset",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.agent_id"],
            name="fk_agent_datasets_tenant_agent",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "dataset_id"],
            ["namespaces.tenant_id", "namespaces.namespace_id"],
            name="fk_agent_datasets_tenant_dataset",
        ),
        Index("ix_agent_datasets_tenant_id", "tenant_id"),
        Index("ix_agent_datasets_agent_id", "agent_id"),
        Index("ix_agent_datasets_dataset_id", "dataset_id"),
    )

    attachment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant: Mapped["Tenant"] = relationship(foreign_keys=[tenant_id])
    agent: Mapped["Agent"] = relationship(
        back_populates="dataset_links",
        primaryjoin=(
            "and_("
            "AgentDataset.tenant_id == Agent.tenant_id, "
            "AgentDataset.agent_id == Agent.agent_id"
            ")"
        ),
        foreign_keys="[AgentDataset.tenant_id, AgentDataset.agent_id]",
        overlaps="tenant,agents,dataset,agent_links",
    )
    dataset: Mapped["Namespace"] = relationship(
        back_populates="agent_links",
        primaryjoin=(
            "and_("
            "AgentDataset.tenant_id == Namespace.tenant_id, "
            "AgentDataset.dataset_id == Namespace.namespace_id"
            ")"
        ),
        foreign_keys="[AgentDataset.tenant_id, AgentDataset.dataset_id]",
        overlaps="tenant,namespaces,agent,dataset_links",
    )
