"""Agent routes for the product shell."""

from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session, get_session_factory
from app.models.enums import WorkspaceMemberRole, WorkspaceMemberStatus
from app.models.workspace_member import WorkspaceMember
from app.schemas.agents import (
    AgentChatRequest,
    AgentChatResponse,
    AgentCreateRequest,
    AgentDatasetAttachRequest,
    AgentResponse,
    AgentUpdateRequest,
)
from app.services.agent_chat import AgentChatServiceError, execute_agent_chat_turn, execute_agent_chat_turn_streaming
from app.services.audit_logs import write_audit_log
from app.services.agents import (
    AgentServiceError,
    attach_dataset_to_agent,
    create_agent,
    delete_agent_for_tenant,
    detach_dataset_from_agent,
    get_agent_for_tenant,
    list_agents_for_tenant,
    update_agent,
)


router = APIRouter()


def _build_agent_response(agent) -> AgentResponse:
    """Map one agent row into the product-facing response schema."""

    return AgentResponse(
        agent_id=agent.agent_id,
        workspace_id=agent.workspace_id,
        name=agent.name,
        description=agent.description,
        system_instructions=agent.system_instructions,
        default_mode=agent.default_mode,
        allowed_modes=agent.allowed_modes,
        status=agent.status,
        dataset_ids=[link.dataset_id for link in agent.dataset_links],
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_route(
    agent_request: AgentCreateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    """Create one agent for the authenticated tenant."""

    try:
        agent = await create_agent(
            session=session,
            tenant_id=tenant_context.tenant_id,
            agent_request=agent_request,
        )
    except AgentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    await write_audit_log(
        session=session,
        tenant_id=tenant_context.tenant_id,
        actor_key_id=tenant_context.api_key_id,
        workspace_id=agent.workspace_id,
        action="agent.created",
        resource_type="agent",
        resource_id=str(agent.agent_id),
        summary=f"Agent '{agent.name}' created",
    )

    return _build_agent_response(agent)


@router.get("/agents", response_model=list[AgentResponse])
async def list_agents_route(
    workspace_id: UUID | None = Query(default=None),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgentResponse]:
    """List agents owned by the authenticated tenant."""

    try:
        agents = await list_agents_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            workspace_id=workspace_id,
        )
    except AgentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return [_build_agent_response(agent) for agent in agents]


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent_route(
    agent_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    """Return one agent only if it belongs to the authenticated tenant."""

    try:
        agent = await get_agent_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            agent_id=agent_id,
        )
    except AgentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return _build_agent_response(agent)


@router.patch("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent_route(
    agent_id: UUID,
    agent_request: AgentUpdateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    """Patch one agent owned by the authenticated tenant."""

    try:
        agent = await update_agent(
            session=session,
            tenant_id=tenant_context.tenant_id,
            agent_id=agent_id,
            agent_request=agent_request,
        )
    except AgentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return _build_agent_response(agent)


@router.post("/agents/{agent_id}/datasets", response_model=AgentResponse)
async def attach_dataset_to_agent_route(
    agent_id: UUID,
    attach_request: AgentDatasetAttachRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AgentResponse:
    """Attach one dataset to one agent inside the same workspace."""

    try:
        agent = await attach_dataset_to_agent(
            session=session,
            tenant_id=tenant_context.tenant_id,
            agent_id=agent_id,
            dataset_id=attach_request.dataset_id,
        )
    except AgentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return _build_agent_response(agent)


@router.delete(
    "/agents/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_agent_route(
    agent_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Delete one tenant-scoped agent if the caller is a workspace admin."""

    try:
        agent = await get_agent_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            agent_id=agent_id,
        )
    except AgentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    member_result = await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.tenant_id == tenant_context.tenant_id,
            WorkspaceMember.workspace_id == agent.workspace_id,
            WorkspaceMember.status == WorkspaceMemberStatus.ACTIVE,
        )
    )
    member = member_result.scalar_one_or_none()
    if member is None or member.role != WorkspaceMemberRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace admins can delete agents.",
        )

    try:
        await delete_agent_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            agent_id=agent_id,
        )
    except AgentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/agents/{agent_id}/datasets/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def detach_dataset_from_agent_route(
    agent_id: UUID,
    dataset_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Detach one dataset from one tenant-scoped agent."""

    try:
        await detach_dataset_from_agent(
            session=session,
            tenant_id=tenant_context.tenant_id,
            agent_id=agent_id,
            dataset_id=dataset_id,
        )
    except AgentServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/agents/{agent_id}/chat", response_model=AgentChatResponse)
async def chat_with_agent_route(
    agent_id: UUID,
    chat_request: AgentChatRequest,
    response: Response,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AgentChatResponse:
    """Execute one grounded chat turn for an agent conversation."""

    try:
        chat_response = await execute_agent_chat_turn(
            session=session,
            tenant_context=tenant_context,
            agent_id=agent_id,
            chat_request=chat_request,
        )
    except AgentChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    response.headers["X-Run-Id"] = str(chat_response.run_id)
    response.headers["X-Trace-Id"] = str(chat_response.run_id)
    return chat_response


@router.post("/agents/{agent_id}/chat/stream")
async def stream_agent_chat_route(
    agent_id: UUID,
    chat_request: AgentChatRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> StreamingResponse:
    """Stream one grounded chat turn as SSE, emitting step-level progress events."""

    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def on_progress(event: dict) -> None:
        await queue.put(event)

    async def run_pipeline() -> None:
        session_factory = get_session_factory()
        async with session_factory() as session:
            try:
                chat_response = await execute_agent_chat_turn_streaming(
                    session=session,
                    tenant_context=tenant_context,
                    agent_id=agent_id,
                    chat_request=chat_request,
                    on_progress=on_progress,
                )
                await queue.put({
                    "type": "answer",
                    "data": chat_response.model_dump(mode="json"),
                })
            except AgentChatServiceError as exc:
                await queue.put({"type": "error", "detail": exc.detail, "status_code": exc.status_code})
            except Exception as exc:  # noqa: BLE001
                await queue.put({"type": "error", "detail": str(exc), "status_code": 500})
            finally:
                await queue.put(None)

    asyncio.create_task(run_pipeline())

    async def generate():
        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
        yield "data: {\"type\": \"done\"}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
