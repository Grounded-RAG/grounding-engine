"""Conversation routes for product-shell chat history."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session
from app.schemas.conversations import (
    ConversationCreateRequest,
    ConversationResponse,
    ConversationUpdateRequest,
)
from app.services.conversations import (
    ConversationServiceError,
    create_conversation,
    get_conversation_for_tenant,
    list_agent_conversations,
    update_conversation,
)


router = APIRouter()


@router.post(
    "/agents/{agent_id}/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation_route(
    agent_id: UUID,
    conversation_request: ConversationCreateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """Create one conversation under the selected agent."""

    try:
        conversation = await create_conversation(
            session=session,
            tenant_id=tenant_context.tenant_id,
            agent_id=agent_id,
            created_by_api_key_id=tenant_context.api_key_id,
            conversation_request=conversation_request,
        )
    except ConversationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return ConversationResponse.model_validate(conversation)


@router.get(
    "/agents/{agent_id}/conversations",
    response_model=list[ConversationResponse],
)
async def list_agent_conversations_route(
    agent_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[ConversationResponse]:
    """List conversations for one tenant-scoped agent."""

    try:
        conversations = await list_agent_conversations(
            session=session,
            tenant_id=tenant_context.tenant_id,
            agent_id=agent_id,
        )
    except ConversationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return [
        ConversationResponse.model_validate(conversation)
        for conversation in conversations
    ]


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
async def get_conversation_route(
    conversation_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """Return one conversation only if it belongs to the authenticated tenant."""

    try:
        conversation = await get_conversation_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            conversation_id=conversation_id,
        )
    except ConversationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return ConversationResponse.model_validate(conversation)


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
async def update_conversation_route(
    conversation_id: UUID,
    conversation_request: ConversationUpdateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationResponse:
    """Patch one conversation owned by the authenticated tenant."""

    try:
        conversation = await update_conversation(
            session=session,
            tenant_id=tenant_context.tenant_id,
            conversation_id=conversation_id,
            conversation_request=conversation_request,
        )
    except ConversationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return ConversationResponse.model_validate(conversation)
