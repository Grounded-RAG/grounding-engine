"""Workspace routes for the product shell."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session
from app.schemas.workspaces import (
    WorkspaceCreateRequest,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)
from app.services.workspaces import (
    WorkspaceServiceError,
    create_workspace,
    get_workspace_for_tenant,
    list_workspaces_for_tenant,
    update_workspace,
)


router = APIRouter()


@router.post(
    "/workspaces",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace_route(
    workspace_request: WorkspaceCreateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceResponse:
    """Create one workspace for the authenticated tenant."""

    try:
        workspace = await create_workspace(
            session=session,
            tenant_id=tenant_context.tenant_id,
            workspace_request=workspace_request,
        )
    except WorkspaceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return WorkspaceResponse.model_validate(workspace)


@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def list_workspaces_route(
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[WorkspaceResponse]:
    """List all workspaces owned by the authenticated tenant."""

    workspaces = await list_workspaces_for_tenant(
        session=session,
        tenant_id=tenant_context.tenant_id,
    )
    return [WorkspaceResponse.model_validate(workspace) for workspace in workspaces]


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace_route(
    workspace_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceResponse:
    """Return one workspace only if it belongs to the authenticated tenant."""

    try:
        workspace = await get_workspace_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            workspace_id=workspace_id,
        )
    except WorkspaceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return WorkspaceResponse.model_validate(workspace)


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace_route(
    workspace_id: UUID,
    workspace_request: WorkspaceUpdateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceResponse:
    """Patch one workspace owned by the authenticated tenant."""

    try:
        workspace = await update_workspace(
            session=session,
            tenant_id=tenant_context.tenant_id,
            workspace_id=workspace_id,
            workspace_request=workspace_request,
        )
    except WorkspaceServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return WorkspaceResponse.model_validate(workspace)
