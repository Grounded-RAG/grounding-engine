"""Conversation message API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import MessageRole


class MessageResponse(BaseModel):
    """One persisted conversation message."""

    model_config = ConfigDict(from_attributes=True)

    message_id: UUID
    conversation_id: UUID
    created_by_api_key_id: UUID | None
    run_id: UUID | None
    role: MessageRole
    content: str
    created_at: datetime
