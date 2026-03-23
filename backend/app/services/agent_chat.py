"""Agent-chat orchestration on top of the current Standard query engine."""

from __future__ import annotations

import uuid

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext
from app.models import MessageRole, UserFacingMode
from app.schemas.agents import AgentChatRequest, AgentChatResponse
from app.schemas.query import QueryRequest
from app.services.agents import AgentServiceError, get_agent_for_tenant
from app.services.conversations import (
    ConversationServiceError,
    get_conversation_for_tenant,
)
from app.services.messages import MessageServiceError, create_message
from app.services.query import QueryServiceError, execute_standard_query


class AgentChatServiceError(RuntimeError):
    """Raised when one agent chat turn cannot be completed."""

    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _resolve_chat_mode(
    *,
    requested_mode: UserFacingMode | None,
    conversation_mode: UserFacingMode,
    agent_allowed_modes: list[str],
) -> UserFacingMode:
    """Resolve one user-facing chat mode against the agent allowlist."""

    mode = requested_mode or conversation_mode
    if mode.value not in agent_allowed_modes:
        raise AgentChatServiceError(
            "Chat mode must be one of the agent's allowed modes.",
            status_code=status.HTTP_409_CONFLICT,
        )
    return mode


def _resolve_dataset_id(
    *,
    requested_dataset_id: uuid.UUID | None,
    attached_dataset_ids: list[uuid.UUID],
) -> uuid.UUID:
    """Resolve the dataset for one chat turn against the agent attachments."""

    if not attached_dataset_ids:
        raise AgentChatServiceError(
            "Agent must have at least one attached dataset before chat.",
            status_code=status.HTTP_409_CONFLICT,
        )

    if requested_dataset_id is not None:
        if requested_dataset_id not in attached_dataset_ids:
            raise AgentChatServiceError(
                "Selected dataset must already be attached to the agent.",
                status_code=status.HTTP_409_CONFLICT,
            )
        return requested_dataset_id

    if len(attached_dataset_ids) == 1:
        return attached_dataset_ids[0]

    raise AgentChatServiceError(
        "Agent has multiple attached datasets. Select one dataset for this chat request.",
        status_code=status.HTTP_409_CONFLICT,
    )


async def execute_agent_chat_turn(
    *,
    session: AsyncSession,
    tenant_context: TenantContext,
    agent_id: uuid.UUID,
    chat_request: AgentChatRequest,
) -> AgentChatResponse:
    """Execute one grounded chat turn for one agent conversation."""

    try:
        agent = await get_agent_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            agent_id=agent_id,
        )
        conversation = await get_conversation_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            conversation_id=chat_request.conversation_id,
        )
    except (AgentServiceError, ConversationServiceError) as exc:
        raise AgentChatServiceError(
            exc.detail,
            status_code=exc.status_code,
        ) from exc

    if conversation.agent_id != agent.agent_id:
        raise AgentChatServiceError(
            "Conversation not found for agent.",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    resolved_mode = _resolve_chat_mode(
        requested_mode=chat_request.mode,
        conversation_mode=conversation.last_used_mode,
        agent_allowed_modes=agent.allowed_modes,
    )
    resolved_dataset_id = _resolve_dataset_id(
        requested_dataset_id=chat_request.dataset_id,
        attached_dataset_ids=[link.dataset_id for link in agent.dataset_links],
    )

    try:
        user_message = await create_message(
            session=session,
            tenant_id=tenant_context.tenant_id,
            conversation_id=conversation.conversation_id,
            role=MessageRole.USER,
            content=chat_request.message,
            created_by_api_key_id=tenant_context.api_key_id,
        )
        query_result = await execute_standard_query(
            session=session,
            tenant_context=tenant_context,
            query_request=QueryRequest(
                namespace_id=resolved_dataset_id,
                query=chat_request.message,
            ),
            agent_id=agent.agent_id,
            conversation_id=conversation.conversation_id,
            selected_mode=resolved_mode,
        )
        assistant_message = await create_message(
            session=session,
            tenant_id=tenant_context.tenant_id,
            conversation_id=conversation.conversation_id,
            role=MessageRole.ASSISTANT,
            content=query_result.response.answer,
            run_id=query_result.trace_id,
        )

        conversation = await get_conversation_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            conversation_id=conversation.conversation_id,
        )
        conversation.last_used_mode = resolved_mode
        await session.commit()
        await session.refresh(conversation)
    except MessageServiceError as exc:
        raise AgentChatServiceError(
            exc.detail,
            status_code=exc.status_code,
        ) from exc
    except QueryServiceError as exc:
        raise AgentChatServiceError(
            exc.detail,
            status_code=exc.status_code,
        ) from exc
    except SQLAlchemyError as exc:
        await session.rollback()
        raise AgentChatServiceError(
            "Failed to update conversation after chat.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        ) from exc

    return AgentChatResponse(
        agent_id=agent.agent_id,
        conversation_id=conversation.conversation_id,
        dataset_id=resolved_dataset_id,
        mode=resolved_mode,
        run_id=query_result.trace_id,
        user_message_id=user_message.message_id,
        assistant_message_id=assistant_message.message_id,
        answer=query_result.response.answer,
        citations=query_result.response.citations,
        confidence_score=query_result.response.confidence_score,
        verification_status=query_result.response.verification_status,
        degraded_reasons=query_result.response.degraded_reasons,
    )
