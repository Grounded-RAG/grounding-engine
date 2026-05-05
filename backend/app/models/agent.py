"""Agent persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import get_settings
from app.core.database import Base
from app.models.enums import AgentStatus, UserFacingMode, sqlalchemy_enum

if TYPE_CHECKING:
    from app.models.agent_dataset import AgentDataset
    from app.models.conversation import Conversation
    from app.models.tenant import Tenant
    from app.models.workspace import Workspace


def _default_allowed_modes() -> list[str]:
    """Return the current default allowed modes for newly created agents."""

    allowed_modes = [UserFacingMode.AUTO.value, UserFacingMode.INSTANT.value]
    if get_settings().enterprise_enabled:
        allowed_modes.append(UserFacingMode.THINKING.value)
    return allowed_modes


class Agent(Base):
    """Reusable assistant configuration attached to one workspace."""

    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "workspace_id",
            "name",
            name="uq_agents_workspace_name",
        ),
        UniqueConstraint(
            "tenant_id",
            "agent_id",
            name="uq_agents_tenant_agent_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "workspace_id"],
            ["workspaces.tenant_id", "workspaces.workspace_id"],
            name="fk_agents_tenant_workspace",
        ),
        Index("ix_agents_tenant_id", "tenant_id"),
        Index("ix_agents_workspace_id", "workspace_id"),
        Index("ix_agents_status", "status"),
    )

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    system_instructions: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("''"),
    )
    default_mode: Mapped[UserFacingMode] = mapped_column(
        sqlalchemy_enum(UserFacingMode, name="user_facing_mode_enum"),
        nullable=False,
        server_default=text("'auto'"),
    )
    allowed_modes: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=_default_allowed_modes,
        server_default=text("'[\"auto\", \"instant\", \"thinking\"]'::jsonb"),
    )
    status: Mapped[AgentStatus] = mapped_column(
        sqlalchemy_enum(AgentStatus, name="agent_status_enum"),
        nullable=False,
        server_default=text("'active'"),
    )
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
        back_populates="agents",
        foreign_keys=[tenant_id],
    )
    workspace: Mapped["Workspace"] = relationship(
        back_populates="agents",
        primaryjoin=(
            "and_("
            "Agent.tenant_id == Workspace.tenant_id, "
            "Agent.workspace_id == Workspace.workspace_id"
            ")"
        ),
        foreign_keys="[Agent.tenant_id, Agent.workspace_id]",
        overlaps="tenant,workspaces",
    )
    dataset_links: Mapped[list["AgentDataset"]] = relationship(
        back_populates="agent",
        primaryjoin=(
            "and_("
            "Agent.tenant_id == AgentDataset.tenant_id, "
            "Agent.agent_id == AgentDataset.agent_id"
            ")"
        ),
        foreign_keys="[AgentDataset.tenant_id, AgentDataset.agent_id]",
        cascade="all, delete-orphan",
        overlaps="tenant,agents,dataset,agent_links",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="agent",
        primaryjoin=(
            "and_("
            "Agent.tenant_id == Conversation.tenant_id, "
            "Agent.agent_id == Conversation.agent_id"
            ")"
        ),
        foreign_keys="[Conversation.tenant_id, Conversation.agent_id]",
        overlaps="tenant,conversations,workspace",
        cascade="all, delete-orphan",
    )
