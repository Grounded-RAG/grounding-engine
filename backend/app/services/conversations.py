"""Conversation services for product-shell chat threads."""

from __future__ import annotations

import uuid

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Agent, Conversation, UserFacingMode
from app.schemas.conversations import ConversationCreateRequest, ConversationUpdateRequest
from app.services.capabilities import get_current_supported_modes


class ConversationServiceError(RuntimeError):
    """Raised when a conversation operation cannot be completed."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _normalize_title(title: str | None) -> str:
    """Normalize one conversation title or fall back to the default shell label."""

    if title is None:
        return "New Chat"
    normalized = title.strip()
    if not normalized:
        raise ConversationServiceError(
            "Conversation title must not be empty.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    return normalized


def _resolve_mode(
    *,
    requested_mode: UserFacingMode | None,
    agent: Agent,
) -> UserFacingMode:
    """Resolve one conversation mode against current backend and agent constraints."""

    mode = requested_mode or agent.default_mode
    supported_modes = get_current_supported_modes()

    if mode not in supported_modes:
        raise ConversationServiceError(
            f"Conversation mode '{mode.value}' is not available yet.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if mode.value not in agent.allowed_modes:
        raise ConversationServiceError(
            "Conversation mode must be one of the agent's allowed modes.",
            status_code=status.HTTP_409_CONFLICT,
        )

    return mode


async def _get_agent_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> Agent:
    """Resolve one agent only if it belongs to the authenticated tenant."""

    statement = select(Agent).where(
        Agent.tenant_id == tenant_id,
        Agent.agent_id == agent_id,
    )
    result = await session.execute(statement)
    agent = result.scalar_one_or_none()
    if agent is None:
        raise ConversationServiceError(
            "Agent not found for tenant.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return agent


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
        raise ConversationServiceError(
            "Conversation not found for tenant.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return conversation


async def create_conversation(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    agent_id: uuid.UUID,
    created_by_api_key_id: uuid.UUID,
    conversation_request: ConversationCreateRequest,
) -> Conversation:
    """Create one tenant-scoped conversation under an existing agent."""

    agent = await _get_agent_for_tenant(
        session=session,
        tenant_id=tenant_id,
        agent_id=agent_id,
    )
    conversation = Conversation(
        tenant_id=tenant_id,
        workspace_id=agent.workspace_id,
        agent_id=agent.agent_id,
        created_by_api_key_id=created_by_api_key_id,
        title=_normalize_title(conversation_request.title),
        last_used_mode=_resolve_mode(
            requested_mode=conversation_request.mode,
            agent=agent,
        ),
    )
    session.add(conversation)

    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise ConversationServiceError(
            "Failed to create conversation.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(conversation)
    return conversation


async def list_agent_conversations(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    agent_id: uuid.UUID,
) -> list[Conversation]:
    """List conversations for one tenant-scoped agent."""

    await _get_agent_for_tenant(
        session=session,
        tenant_id=tenant_id,
        agent_id=agent_id,
    )

    statement = (
        select(Conversation)
        .where(
            Conversation.tenant_id == tenant_id,
            Conversation.agent_id == agent_id,
        )
        .order_by(Conversation.updated_at.desc(), Conversation.conversation_id.desc())
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_conversation_for_tenant(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> Conversation:
    """Return one tenant-scoped conversation."""

    return await _get_conversation_for_tenant(
        session=session,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
    )


async def update_conversation(
    *,
    session: AsyncSession,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    conversation_request: ConversationUpdateRequest,
) -> Conversation:
    """Patch one tenant-scoped conversation."""

    conversation = await _get_conversation_for_tenant(
        session=session,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
    )
    fields_set = conversation_request.model_fields_set

    if "title" in fields_set:
        conversation.title = _normalize_title(conversation_request.title)

    if "mode" in fields_set and conversation_request.mode is not None:
        agent = await _get_agent_for_tenant(
            session=session,
            tenant_id=tenant_id,
            agent_id=conversation.agent_id,
        )
        conversation.last_used_mode = _resolve_mode(
            requested_mode=conversation_request.mode,
            agent=agent,
        )

    try:
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise ConversationServiceError(
            "Failed to update conversation.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    await session.refresh(conversation)
    return conversation
