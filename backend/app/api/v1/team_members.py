"""Team member routes for workspace membership management."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session
from app.schemas.team_members import (
    TeamMemberInviteRequest,
    TeamMemberResponse,
    TeamMemberUpdateRequest,
)
from app.services.team_members import (
    TeamMemberServiceError,
    invite_workspace_member,
    list_workspace_members,
    remove_workspace_member,
    update_workspace_member,
)


router = APIRouter()


@router.get(
    "/workspaces/{workspace_id}/members",
    response_model=list[TeamMemberResponse],
)
async def list_members_route(
    workspace_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[TeamMemberResponse]:
    members = await list_workspace_members(
        session=session,
        tenant_id=tenant_context.tenant_id,
        workspace_id=workspace_id,
    )
    return [TeamMemberResponse.model_validate(m) for m in members]


@router.post(
    "/workspaces/{workspace_id}/members",
    response_model=TeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member_route(
    workspace_id: UUID,
    invite_request: TeamMemberInviteRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> TeamMemberResponse:
    try:
        member = await invite_workspace_member(
            session=session,
            tenant_id=tenant_context.tenant_id,
            workspace_id=workspace_id,
            invite_request=invite_request,
        )
    except TeamMemberServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return TeamMemberResponse.model_validate(member)


@router.patch(
    "/workspaces/{workspace_id}/members/{member_id}",
    response_model=TeamMemberResponse,
)
async def update_member_route(
    workspace_id: UUID,
    member_id: UUID,
    update_request: TeamMemberUpdateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> TeamMemberResponse:
    try:
        member = await update_workspace_member(
            session=session,
            tenant_id=tenant_context.tenant_id,
            workspace_id=workspace_id,
            member_id=member_id,
            update_request=update_request,
        )
    except TeamMemberServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return TeamMemberResponse.model_validate(member)


@router.delete(
    "/workspaces/{workspace_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def remove_member_route(
    workspace_id: UUID,
    member_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    try:
        await remove_workspace_member(
            session=session,
            tenant_id=tenant_context.tenant_id,
            workspace_id=workspace_id,
            member_id=member_id,
        )
    except TeamMemberServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
