"""Conversation message persistence model."""

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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import MessageRole, sqlalchemy_enum

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.tenant import Tenant


class Message(Base):
    """Immutable persisted message inside one tenant-scoped conversation."""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "char_length(content) > 0",
            name="ck_messages_content_non_empty",
        ),
        UniqueConstraint(
            "tenant_id",
            "message_id",
            name="uq_messages_tenant_message_id",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "conversation_id"],
            ["conversations.tenant_id", "conversations.conversation_id"],
            name="fk_messages_tenant_conversation",
        ),
        Index("ix_messages_tenant_id", "tenant_id"),
        Index("ix_messages_conversation_id", "conversation_id"),
        Index("ix_messages_created_at", "created_at"),
        Index("ix_messages_run_id", "run_id"),
    )

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id"),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by_api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.key_id"),
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    role: Mapped[MessageRole] = mapped_column(
        sqlalchemy_enum(MessageRole, name="message_role_enum"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant: Mapped["Tenant"] = relationship(
        back_populates="messages",
        foreign_keys=[tenant_id],
        overlaps="conversation",
    )
    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages",
        primaryjoin=(
            "and_("
            "Message.tenant_id == Conversation.tenant_id, "
            "Message.conversation_id == Conversation.conversation_id"
            ")"
        ),
        foreign_keys="[Message.tenant_id, Message.conversation_id]",
        overlaps="tenant,messages",
    )
