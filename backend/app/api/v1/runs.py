"""Run-history routes for the product shell."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, get_tenant_context
from app.core.database import get_db_session
from app.schemas.runs import FeedbackSubmission, RunResponse
from app.services.runs import RunServiceError, get_run_for_tenant, list_runs_for_tenant, submit_run_feedback


router = APIRouter()


@router.get("/runs", response_model=list[RunResponse])
async def list_runs_route(
    dataset_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> list[RunResponse]:
    """List recent runs for the authenticated tenant."""

    return await list_runs_for_tenant(
        session=session,
        tenant_id=tenant_context.tenant_id,
        dataset_id=dataset_id,
        limit=limit,
    )


@router.get("/runs/{run_id}", response_model=RunResponse)
async def get_run_route(
    run_id: UUID,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> RunResponse:
    """Return one run only if it belongs to the authenticated tenant."""

    try:
        return await get_run_for_tenant(
            session=session,
            tenant_id=tenant_context.tenant_id,
            run_id=run_id,
        )
    except RunServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.patch("/runs/{run_id}/feedback", response_model=RunResponse)
async def submit_feedback_route(
    run_id: UUID,
    feedback: FeedbackSubmission,
    tenant_context: TenantContext = Depends(get_tenant_context),
    session: AsyncSession = Depends(get_db_session),
) -> RunResponse:
    """Submit or update user feedback for a completed run."""

    try:
        return await submit_run_feedback(
            session=session,
            tenant_id=tenant_context.tenant_id,
            run_id=run_id,
            feedback=feedback,
        )
    except RunServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
