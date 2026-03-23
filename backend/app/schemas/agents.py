"""Agent API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import AgentStatus, UserFacingMode


class AgentCreateRequest(BaseModel):
    """Request used to create one agent for a workspace."""

    workspace_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    system_instructions: str | None = None
    default_mode: UserFacingMode = UserFacingMode.AUTO
    allowed_modes: list[UserFacingMode] | None = None


class AgentUpdateRequest(BaseModel):
    """Patch request for one tenant-scoped agent."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    system_instructions: str | None = None
    default_mode: UserFacingMode | None = None
    allowed_modes: list[UserFacingMode] | None = None
    status: AgentStatus | None = None


class AgentDatasetAttachRequest(BaseModel):
    """Attach one dataset to an agent."""

    dataset_id: UUID


class AgentResponse(BaseModel):
    """Product-facing agent resource."""

    agent_id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    system_instructions: str
    default_mode: UserFacingMode
    allowed_modes: list[UserFacingMode]
    status: AgentStatus
    dataset_ids: list[UUID]
    created_at: datetime
    updated_at: datetime
