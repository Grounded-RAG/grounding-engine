"""Message services for persisted conversation history."""

from __future__ import annotations

import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Conversation, Message, MessageRole


class MessageServiceError(RuntimeError):
    """Raised when a message operation cannot be completed."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _normalize_message_content(content: str) -> str:
    """Normalize message text while rejecting blank content."""

    normalized = content.strip()
    if not normalized:
        raise MessageServiceError(
            "Message content must not be empty.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return normalized


async def _get_conversation_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> Conversation:
    """Resolve one conversation only if it belongs to the authenticated tenant."""

    statement = select(Conversation).where(
        Conversation.tenant_id == tenant_id,
        Conversation.conversation_id == conversation_id,
    )
    result = await session.execute(statement)
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise MessageServiceError(
            "Conversation not found for tenant.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return conversation


async def list_conversation_messages(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> list[Message]:
    """List persisted messages for one tenant-scoped conversation."""

    await _get_conversation_for_tenant(
        session=session,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
    )

    statement = (
        select(Message)
        .where(
            Message.tenant_id == tenant_id,
            Message.conversation_id == conversation_id,
        )
        .order_by(Message.created_at.asc(), Message.message_id.asc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def create_message(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    role: MessageRole,
    content: str,
    created_by_api_key_id: uuid.UUID | None = None,
    run_id: uuid.UUID | None = None,
) -> Message:
    """Persist one message inside a tenant-scoped conversation.

    This helper is intentionally not exposed as a public route yet.
    It exists so later agent-chat execution can reuse the same persistence path.
    """

    conversation = await _get_conversation_for_tenant(
        session=session,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
    )

    message = Message(
        tenant_id=tenant_id,
        conversation_id=conversation.conversation_id,
        created_by_api_key_id=created_by_api_key_id,
        run_id=run_id,
        role=role,
        content=_normalize_message_content(content),
    )
    session.add(message)

    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise MessageServiceError(
            "Failed to persist message.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(message)
    return message
