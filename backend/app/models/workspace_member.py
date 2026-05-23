"""WorkspaceMember persistence model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import WorkspaceMemberRole, WorkspaceMemberStatus, sqlalchemy_enum

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class WorkspaceMember(Base):
    """A user invited to or active in a tenant workspace."""

    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "email", name="uq_workspace_members_workspace_email"),
        Index("ix_workspace_members_workspace_id", "workspace_id"),
        Index("ix_workspace_members_tenant_id", "tenant_id"),
    )

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.tenant_id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.workspace_id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[WorkspaceMemberRole] = mapped_column(
        sqlalchemy_enum(WorkspaceMemberRole, name="workspacememberrole"),
        nullable=False,
        default=WorkspaceMemberRole.MEMBER,
    )
    status: Mapped[WorkspaceMemberStatus] = mapped_column(
        sqlalchemy_enum(WorkspaceMemberStatus, name="workspacememberstatus"),
        nullable=False,
        default=WorkspaceMemberStatus.PENDING,
    )
    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    joined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    workspace: Mapped[Workspace] = relationship("Workspace", back_populates="members")
