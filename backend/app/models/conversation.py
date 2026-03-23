"""Conversation persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
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
from app.models.enums import UserFacingMode, sqlalchemy_enum

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.tenant import Tenant
    from app.models.workspace import Workspace


class Conversation(Base):
    """Tenant-scoped chat thread that belongs to one agent."""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "char_length(title) > 0",
            name="ck_conversations_title_non_empty",
        ),
        UniqueConstraint(
            "tenant_id",
            "conversation_id",
            name="uq_conversations_tenant_conversation_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "workspace_id"],
            ["workspaces.tenant_id", "workspaces.workspace_id"],
            name="fk_conversations_tenant_workspace",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.agent_id"],
            name="fk_conversations_tenant_agent",
        ),
        Index("ix_conversations_tenant_id", "tenant_id"),
        Index("ix_conversations_workspace_id", "workspace_id"),
        Index("ix_conversations_agent_id", "agent_id"),
        Index("ix_conversations_updated_at", "updated_at"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
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
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by_api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.key_id"),
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        server_default=text("'New Chat'"),
    )
    last_used_mode: Mapped[UserFacingMode] = mapped_column(
        sqlalchemy_enum(UserFacingMode, name="user_facing_mode_enum"),
        nullable=False,
        server_default=text("'auto'"),
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
        back_populates="conversations",
        foreign_keys=[tenant_id],
    )
    workspace: Mapped["Workspace"] = relationship(
        back_populates="conversations",
        primaryjoin=(
            "and_("
            "Conversation.tenant_id == Workspace.tenant_id, "
            "Conversation.workspace_id == Workspace.workspace_id"
            ")"
        ),
        foreign_keys="[Conversation.tenant_id, Conversation.workspace_id]",
        overlaps="tenant,workspaces",
    )
    agent: Mapped["Agent"] = relationship(
        back_populates="conversations",
        primaryjoin=(
            "and_("
            "Conversation.tenant_id == Agent.tenant_id, "
            "Conversation.agent_id == Agent.agent_id"
            ")"
        ),
        foreign_keys="[Conversation.tenant_id, Conversation.agent_id]",
        overlaps="tenant,agents,workspace",
    )
