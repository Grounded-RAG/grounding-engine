"""Dashboard routes for the product shell."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session
from app.schemas.dashboard import DashboardRecentJobResponse, DashboardSummaryResponse
from app.schemas.runs import RunResponse
from app.services.dashboard import (
    get_dashboard_summary_for_tenant,
    list_recent_jobs_for_tenant,
    list_recent_runs_for_dashboard,
)


router = APIRouter()


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary_route(
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> DashboardSummaryResponse:
    """Return top-level dashboard counts for the authenticated tenant."""

    return await get_dashboard_summary_for_tenant(
        session=session,
        tenant_id=tenant_context.tenant_id,
    )


@router.get("/dashboard/recent-runs", response_model=list[RunResponse])
async def list_dashboard_recent_runs_route(
    limit: int = Query(default=10, ge=1, le=50),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[RunResponse]:
    """Return recent run activity for the authenticated tenant."""

    return await list_recent_runs_for_dashboard(
        session=session,
        tenant_id=tenant_context.tenant_id,
        limit=limit,
    )


@router.get("/dashboard/recent-jobs", response_model=list[DashboardRecentJobResponse])
async def list_dashboard_recent_jobs_route(
    limit: int = Query(default=10, ge=1, le=50),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[DashboardRecentJobResponse]:
    """Return recent ingestion job activity for the authenticated tenant."""

    return await list_recent_jobs_for_tenant(
        session=session,
        tenant_id=tenant_context.tenant_id,
        limit=limit,
    )
