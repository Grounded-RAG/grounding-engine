"""Audit log routes for governance and compliance."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session
from app.schemas.audit_logs import AuditLogListResponse, AuditLogResponse
from app.services.audit_logs import list_audit_logs


router = APIRouter()


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs_route(
    workspace_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> AuditLogListResponse:
    logs, total = await list_audit_logs(
        session=session,
        tenant_id=tenant_context.tenant_id,
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
    )
