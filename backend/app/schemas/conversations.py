"""Conversation API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserFacingMode


class ConversationCreateRequest(BaseModel):
    """Request used to create one conversation under an agent."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    mode: UserFacingMode | None = None


class ConversationUpdateRequest(BaseModel):
    """Patch request for one tenant-scoped conversation."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    mode: UserFacingMode | None = None


class ConversationResponse(BaseModel):
    """Conversation resource returned by the product-shell API."""

    model_config = ConfigDict(from_attributes=True)

    conversation_id: UUID
    workspace_id: UUID
    agent_id: UUID
    created_by_api_key_id: UUID | None
    title: str
    last_used_mode: UserFacingMode
    created_at: datetime
    updated_at: datetime
